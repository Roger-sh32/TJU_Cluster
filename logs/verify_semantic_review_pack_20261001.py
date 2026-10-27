"""Independent checks of retained cluster profiles and the five preview artifacts."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def verify_record(item):
    path = Path(item['path'])
    assert path.is_file(), path
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == item['sha256'], path
    if 'bytes' in item:
        assert path.stat().st_size == item['bytes'], path


def main():
    raw = pd.read_csv(ROOT / 'HDBSCAN/tables/scene_features_development_audit700_20260927.csv', float_precision='round_trip').set_index('scene_name')
    split = pd.read_csv(ROOT / 'HDBSCAN/tables/evaluation_split_20260924.csv').set_index('scene_name')
    semantic = json.loads((ROOT / 'HDBSCAN/tables/cluster_semantics_20260930.json').read_text(encoding='utf-8'))
    missing = []
    for item in semantic['inputs']:
        if Path(item['path']).exists():
            verify_record(item)
        else:
            missing.append(item['path'])
    assert len(missing) == 1 and Path(missing[0]).name == 'analyze_cluster_semantics_20260930.py'
    features = semantic['semantic_features']
    runs = {p.stem: pd.read_csv(p, float_precision='round_trip').set_index('scene_name')
            for p in (ROOT / 'HDBSCAN/tables/parameter_stability_20260930').glob('n*_seed*.csv')}
    assert len(runs) == 20 and len(semantic['profiles']) == 94
    for profile in semantic['profiles']:
        run = runs[profile['run']]
        names = run.index[run.cluster.eq(profile['cluster'])]
        values = raw.loc[names, features]
        assert len(names) == profile['n']
        for feature in features:
            stats = profile['features'][feature]
            expected = [values[feature].mean(), values[feature].median(),
                        (values[feature].mean()-raw[feature].mean())/raw[feature].std(ddof=0),
                        values[feature].gt(0).mean()]
            np.testing.assert_allclose([stats['mean'], stats['median'], stats['mean_z_global'], stats['positive_fraction']], expected, rtol=1e-12, atol=1e-12)
            assert stats['positive_count'] == int(values[feature].gt(0).sum())
        assert profile['locations'] == raw.loc[names, 'log_location'].value_counts().to_dict()
        if profile['cluster'] >= 0:
            distance = (((values-values.mean())/raw[features].std(ddof=0))**2).sum(axis=1)
            assert profile['prototype_scene'] == sorted(names, key=lambda name:(distance[name], name))[0]
    reports = [json.loads((ROOT / ('HDBSCAN/tables/' + name)).read_text(encoding='utf-8')) for name in
               ['semantic_review_media_20261001.json', 'semantic_review_supplement_media_20261001.json']]
    reviewed, outputs = [], []
    run = runs['n30_s1_seed42']
    for report in reports:
        for source in report['inputs']:
            verify_record(source)
        for scene in report['scenes']:
            name = scene['scene_name']
            assert split.loc[name, 'split'] == 'development'
            assert scene['scene_token'] == split.loc[name, 'scene_token'] == raw.loc[name, 'scene_token']
            assert scene['cluster'] == int(run.loc[name, 'cluster'])
            assert scene['priority_rank'] == int(run.loc[name, 'priority_rank'])
            np.testing.assert_allclose(scene['risk'], run.loc[name, 'risk'], atol=1e-12)
            if scene['status'] != 'exported_verified':
                assert scene['missing_keyframes'] == scene['keyframes'] and not scene['outputs']
                continue
            reviewed.append(name)
            assert scene['missing_media_count'] == 0 and scene['frame_count'] >= 110
            frames = scene['selected_frames']
            assert len(frames) == scene['frame_count']
            assert all(a['timestamp'] < b['timestamp'] for a,b in zip(frames,frames[1:]))
            for frame in frames:
                verify_record(frame['source'])
            for output in scene['outputs']:
                verify_record(output)
                outputs.append(output)
                with Image.open(output['path']) as image:
                    if output['path'].endswith('.gif'):
                        assert image.n_frames == scene['frame_count']
                        durations = []
                        for i in range(image.n_frames):
                            image.seek(i)
                            image.load()
                            assert image.size == (960,576)
                            durations.append(image.info['duration'])
                        assert durations == scene['frame_durations_ms']
                        assert sum(durations)/1000 == scene['playback_seconds']
                        assert abs(sum(durations[:-1])/1000-scene['sampled_data_span_seconds']) <= .01
                    else:
                        image.load()
    assert set(reviewed) == {'scene-0158','scene-0107','scene-0151','scene-0032','scene-0014'}
    assert split.loc[reviewed, 'log_token'].nunique() == 5
    supplements = json.loads((ROOT / 'HDBSCAN/tables/semantic_review_supplements_20261001.json').read_text(encoding='utf-8'))
    for source in supplements['inputs']:
        verify_record(source)
    for item in supplements['supplements']:
        assert run.loc[item['missing_target'],'cluster'] == run.loc[item['supplement'],'cluster'] == item['cluster']
        distance = np.sqrt((((raw.loc[item['missing_target'],features]-raw.loc[item['supplement'],features])/raw[features].std(ddof=0))**2).mean())
        np.testing.assert_allclose(distance,item['standardized_feature_rms_distance'],atol=1e-12)
    protocol = json.loads((ROOT / 'HDBSCAN/tables/semantic_review_supplement_export_protocol_20261001.json').read_text(encoding='utf-8'))
    for key in ['selection','script','export_recipe']:
        verify_record(protocol[key])
    print('PASS: 94 x 52 profile statistics; all input/output/source hashes; 5 complete GIFs and timing; 4 same-cluster supplements; 5 development logs')
    print('Known gap: historical semantic analysis recipe absent; its numeric profiles independently recomputed, historical recipe provenance not restored.')
    print('Total preview assets: %.1f MiB' % (sum(o['bytes'] for o in outputs)/1024**2))


if __name__ == '__main__':
    main()
