import unittest
from contextlib import contextmanager
from pathlib import Path
import shutil
import uuid

from HDBSCAN.scripts.prepare_evaluation_split import build_split, collect_evidence


@contextmanager
def workspace_tempdir():
    parent = Path(__file__).resolve().parent
    path = parent / ('split_test_' + uuid.uuid4().hex)
    # Inherit workspace permissions instead of Conda's Windows 0700 temp ACL.
    path.mkdir()
    try:
        yield path
    finally:
        if path.resolve().parent != parent:
            raise RuntimeError('Temporary directory escaped the test workspace')
        shutil.rmtree(path)


def sample_metadata():
    logs = []
    scenes = []
    for location in ['A', 'B']:
        for number in range(4):
            token = f'{location}{number}'
            logs.append({'token': token, 'location': location})
            for _ in range(2):
                index = len(scenes)
                scenes.append({'name': f'scene-{index:04}', 'token': f's{index}',
                               'log_token': token})
    return scenes, logs


class EvaluationSplitTest(unittest.TestCase):
    def test_exact_count_and_log_isolation(self):
        scenes, logs = sample_metadata()
        rows = build_split(scenes, logs, {'scene-0000'}, 6, 42)
        evaluation = [r for r in rows if r['split'] == 'evaluation']
        development = [r for r in rows if r['split'] == 'development']
        self.assertEqual(len(evaluation), 6)
        self.assertFalse({r['log_token'] for r in evaluation}
                         & {r['log_token'] for r in development})
        self.assertEqual({r['log_location'] for r in evaluation}, {'A', 'B'})
        self.assertTrue(all(r['split'] == 'development' for r in rows
                            if r['log_token'] == 'A0'))
        self.assertEqual(len({r['review_id'] for r in evaluation}), 6)
        self.assertTrue(all(not r['review_id'] for r in development))

    def test_input_order_does_not_change_split(self):
        scenes, logs = sample_metadata()
        a = build_split(scenes, logs, set(), 8, 123)
        b = build_split(list(reversed(scenes)), list(reversed(logs)), set(), 8, 123)
        self.assertEqual(a, b)

    def test_impossible_count_does_not_split_logs(self):
        scenes, logs = sample_metadata()
        with self.assertRaisesRegex(ValueError, 'exact'):
            build_split(scenes, logs, set(), 5, 42)

    def test_duplicate_scene_or_token_rejected(self):
        scenes, logs = sample_metadata()
        with self.assertRaises(ValueError):
            build_split(scenes + [scenes[0]], logs, set(), 6, 42)
        changed = [dict(r) for r in scenes]
        changed[1]['token'] = changed[0]['token']
        with self.assertRaises(ValueError):
            build_split(changed, logs, set(), 6, 42)

    def test_missing_log_or_unknown_exclusion_rejected(self):
        scenes, logs = sample_metadata()
        with self.assertRaises(ValueError):
            build_split(scenes, logs[1:], set(), 6, 42)
        with self.assertRaises(ValueError):
            build_split(scenes, logs, {'scene-9999'}, 6, 42)

    def test_unavailable_location_rejected_instead_of_silent_bias(self):
        scenes, logs = sample_metadata()
        excluded = {s['name'] for s in scenes if s['log_token'].startswith('A')}
        with self.assertRaisesRegex(ValueError, 'location'):
            build_split(scenes, logs, excluded, 6, 42)

    def test_evidence_ignores_full_corpus_table_but_keeps_notes_and_previews(self):
        import csv
        from pathlib import Path
        scenes, _ = sample_metadata()
        known = {s['name'] for s in scenes}
        with workspace_tempdir() as temp:
            root = Path(temp)
            self.assertTrue(root.resolve().is_relative_to(Path(__file__).resolve().parent))
            tables, notes, previews = [root / name for name in ['tables', 'notes', 'exports']]
            for directory in [tables, notes, previews]:
                directory.mkdir()
            for path, names in [(tables / 'scene_features.csv', sorted(known)),
                                (tables / 'scene_features_debug.csv', ['scene-0001'])]:
                with path.open('w', newline='', encoding='utf-8') as stream:
                    writer = csv.DictWriter(stream, fieldnames=['scene_name'])
                    writer.writeheader()
                    writer.writerows({'scene_name': name} for name in names)
            (notes / 'review.md').write_text('scene-0002; scene-9999', encoding='utf-8')
            (previews / 'scene-0003.gif').touch()
            used, evidence = collect_evidence(tables, [notes], previews, known, set())
            self.assertEqual(used, {'scene-0001', 'scene-0002', 'scene-0003'})
            self.assertTrue(evidence['historical_full_corpus_tables'])
            self.assertEqual(evidence['unmatched_mentions'], ['scene-9999'])
            used, _ = collect_evidence(tables, [notes], previews, known, {notes / 'review.md'})
            self.assertEqual(used, {'scene-0001', 'scene-0003'})

    def test_output_cannot_overwrite_frozen_partition(self):
        from pathlib import Path
        from unittest.mock import patch
        from HDBSCAN.scripts.prepare_evaluation_split import main
        with workspace_tempdir() as temp:
            root = Path(temp)
            self.assertTrue(root.resolve().is_relative_to(Path(__file__).resolve().parent))
            prefix = root / 'frozen'
            output = root / 'frozen.csv'
            output.write_text('do not overwrite', encoding='utf-8')
            with patch('sys.argv', ['prepare_evaluation_split.py', '--output-prefix', str(prefix)]):
                with self.assertRaises(FileExistsError):
                    main()
            self.assertEqual(output.read_text(encoding='utf-8'), 'do not overwrite')


if __name__ == '__main__':
    unittest.main()
