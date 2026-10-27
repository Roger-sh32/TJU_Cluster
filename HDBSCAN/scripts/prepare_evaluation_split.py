"""Freeze a log-disjoint, development-evidence-aware evaluation partition."""

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import re
import sys


def fingerprint(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def mentions(text):
    return {'scene-' + value for value in re.findall(r'scene[-_](\d{4})(?!\d)', text)}


def collect_evidence(tables, note_dirs, previews, known, ignored_notes):
    used, unknown = set(), set()
    sources, full_corpus, skipped, preview_paths = [], [], [], []
    for path in sorted(Path(tables).glob('scene_features*.csv')):
        with path.open(encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.DictReader(stream))
        names = {row.get('scene_name') for row in rows} - {None, ''}
        unknown.update(names - known)
        if names == known:
            full_corpus.append(fingerprint(path))
        elif names & known:
            used.update(names & known)
            sources.append(dict(fingerprint(path), kind='development_table',
                                scenes=sorted(names & known)))
        else:
            skipped.append(dict(fingerprint(path), reason='no_known_scene_names'))
    note_paths = {p.resolve() for directory in note_dirs for p in Path(directory).glob('*.md')}
    for path in sorted(note_paths - {Path(p).resolve() for p in ignored_notes}):
        names = mentions(path.read_text(encoding='utf-8-sig'))
        unknown.update(names - known)
        if names & known:
            used.update(names & known)
            sources.append(dict(fingerprint(path), kind='scene_reference_note',
                                scenes=sorted(names & known)))
    for path in sorted(Path(previews).rglob('*')):
        if path.is_file():
            names = mentions(path.name) & known
            if names:
                used.update(names)
                preview_paths.append(str(path.resolve()))
    return used, {
        'sources': sources, 'historical_full_corpus_tables': full_corpus,
        'skipped_tables': skipped, 'unmatched_mentions': sorted(unknown),
        'preview_paths': preview_paths,
        'preview_path_list_sha256': hashlib.sha256('\n'.join(preview_paths).encode()).hexdigest(),
        'policy': 'Conservative union of small development tables, explicit note references '
                  'and preview filenames; all matching log groups stay in development. '
                  'Full-corpus historical tables are disclosed, not treated as 850 human reviews.',
    }


def build_split(scenes, logs, excluded, target, seed):
    if not scenes or not 0 < target < len(scenes):
        raise ValueError('Evaluation count must be positive and smaller than the corpus')
    for key in ['name', 'token']:
        values = [scene[key] for scene in scenes]
        if any(not value for value in values) or len(set(values)) != len(values):
            raise ValueError(f'Missing or duplicate scene {key}')
    log_map = {log['token']: log for log in logs}
    if len(log_map) != len(logs) or any(not log.get('location') for log in logs):
        raise ValueError('Duplicate logs or missing location')
    if any(scene['log_token'] not in log_map for scene in scenes):
        raise ValueError('Scene refers to a missing log')
    if excluded - {scene['name'] for scene in scenes}:
        raise ValueError('Unknown excluded scene')
    groups = defaultdict(list)
    for scene in scenes:
        groups[scene['log_token']].append(scene)
    blocked = {scene['log_token'] for scene in scenes if scene['name'] in excluded}
    population = Counter(log_map[scene['log_token']]['location'] for scene in scenes)
    eligible = defaultdict(list)
    for token, group in sorted(groups.items()):
        if token not in blocked:
            eligible[log_map[token]['location']].append((token, len(group)))
    if set(population) != set(eligible):
        raise ValueError('At least one location has no eligible log group')

    # Subset sums preserve whole logs. The seed selects among feasible subsets;
    # quotas minimize squared deviation from full-corpus location proportions.
    rng = random.Random(seed)
    location_options = {}
    for location in sorted(eligible):
        choices = eligible[location][:]
        rng.shuffle(choices)
        sums = {0: ()}
        for token, size in choices:
            for count, tokens in list(sums.items()):
                if count + size <= target and count + size not in sums:
                    sums[count + size] = tokens + (token,)
        location_options[location] = {count: tokens for count, tokens in sums.items() if count}
    combined = {0: (0, ())}
    for location, options in location_options.items():
        next_combined = {}
        for count, (cost, tokens) in combined.items():
            for local_count, local_tokens in options.items():
                total = count + local_count
                if total > target:
                    continue
                new_cost = cost + (local_count * len(scenes) - target * population[location]) ** 2
                if total not in next_combined or new_cost < next_combined[total][0]:
                    next_combined[total] = (new_cost, tokens + local_tokens)
        combined = next_combined
    if target not in combined:
        raise ValueError('No exact evaluation size preserving logs and every location')
    selected_logs = set(combined[target][1])
    eval_names = sorted(scene['name'] for scene in scenes if scene['log_token'] in selected_logs)
    random.Random(seed + 1).shuffle(eval_names)
    review_ids = {name: f'E{index:04}' for index, name in enumerate(eval_names, 1)}
    output = []
    for scene in sorted(scenes, key=lambda item: item['name']):
        token = scene['log_token']
        output.append({
            'scene_name': scene['name'], 'scene_token': scene['token'],
            'log_token': token, 'log_location': log_map[token]['location'],
            'split': 'evaluation' if token in selected_logs else 'development',
            'review_id': review_ids.get(scene['name'], ''),
            'development_evidence': ('direct_reference' if scene['name'] in excluded else
                                     'same_log_as_reference' if token in blocked else ''),
        })
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadata-dir', type=Path, default=Path('nuScenes/v1.0-trainval'))
    parser.add_argument('--tables-dir', type=Path, default=Path('HDBSCAN/tables'))
    parser.add_argument('--notes-dir', type=Path, action='append', default=[])
    parser.add_argument('--ignore-note', type=Path, action='append', default=[])
    parser.add_argument('--previews-dir', type=Path, default=Path('exports'))
    parser.add_argument('--exclude-scene', action='append', default=[])
    parser.add_argument('--evaluation-count', type=int, default=150)
    parser.add_argument('--seed', type=int, default=20260924)
    parser.add_argument('--output-prefix', type=Path, required=True)
    args = parser.parse_args()
    csv_path = Path(str(args.output_prefix) + '.csv')
    manifest_path = Path(str(args.output_prefix) + '_manifest.json')
    if csv_path.exists() or manifest_path.exists():
        raise FileExistsError('Frozen split outputs already exist; use a new version prefix')
    scene_path, log_path = [args.metadata_dir / name for name in ['scene.json', 'log.json']]
    scenes, logs = [json.loads(path.read_text(encoding='utf-8')) for path in [scene_path, log_path]]
    notes = args.notes_dir or [Path('logs'), Path('knowledge/wiki')]
    for directory in [args.tables_dir, args.previews_dir, *notes]:
        if not directory.is_dir():
            raise FileNotFoundError(f'Evidence directory missing: {directory}')
    used, evidence = collect_evidence(args.tables_dir, notes, args.previews_dir,
                                      {scene['name'] for scene in scenes}, set(args.ignore_note))
    used.update(args.exclude_scene)
    rows = build_split(scenes, logs, used, args.evaluation_count, args.seed)
    counts = Counter(row['split'] for row in rows)
    locations = {split: dict(Counter(row['log_location'] for row in rows if row['split'] == split))
                 for split in ['development', 'evaluation']}
    log_counts = {split: len({row['log_token'] for row in rows if row['split'] == split})
                  for split in ['development', 'evaluation']}
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    manifest = {
        'created_at_utc': datetime.now(timezone.utc).isoformat(), 'python': sys.executable,
        'python_version': sys.version, 'command': [sys.executable, *sys.argv],
        'script': fingerprint(__file__), 'metadata': [fingerprint(scene_path), fingerprint(log_path)],
        'seed': args.seed, 'target_evaluation_count': args.evaluation_count,
        'counts': dict(counts), 'location_counts': locations, 'log_counts': log_counts,
        'development_reference_count': len(used), 'development_reference_scenes': sorted(used),
        'forced_development_count': sum(bool(row['development_evidence']) for row in rows),
        'evidence': evidence, 'output': fingerprint(csv_path),
        'status': 'membership_frozen; media_readiness_and_expert_labels_pending',
        'limitations': [
            'This is a custom split, not the official nuScenes train/val split.',
            'All 850 scenes were previously included in historical unsupervised exploration.',
            'Unrecorded human reviews cannot be excluded automatically.',
            'Log separation does not guarantee geographic separation.',
            'Seeded subset-sum sampling is constrained, not a uniform random scene sample.',
            'Existing extraction and clustering scripts do not yet enforce this partition.',
        ],
    }
    with manifest_path.open('x', encoding='utf-8') as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
    print(json.dumps({'counts': counts, 'locations': locations, 'log_counts': log_counts,
                      'development_references': len(used),
                      'forced_development': manifest['forced_development_count'],
                      'manifest': str(manifest_path)}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
