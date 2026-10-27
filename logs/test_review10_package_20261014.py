import unittest
from HDBSCAN.tests.test_evaluation_split import workspace_tempdir


class ReviewPackageContracts(unittest.TestCase):
    def fixtures(self):
        from logs.build_review10_package_20261014 import NAMES
        rows = {n: {'scene_name': n, 'scene_token': n+'token'} for n in NAMES}
        split = {n: {**r, 'split': 'development', 'log_token': n+'log'} for n,r in rows.items()}
        return rows, split

    def test_exact_fixed_ten_current_development_only(self):
        from logs.build_review10_package_20261014 import NAMES, validate_scope
        rows, split = self.fixtures()
        validate_scope(NAMES, rows, rows, split)
        split[NAMES[0]]['split'] = 'evaluation'
        with self.assertRaises(ValueError):
            validate_scope(NAMES, rows, rows, split)

    def test_identity_mismatch_and_duplicate_or_extra_selection_refused(self):
        from logs.build_review10_package_20261014 import NAMES, validate_scope
        rows, split = self.fixtures()
        for names in (NAMES[:-1], NAMES+(NAMES[0],)):
            with self.assertRaises(ValueError):
                validate_scope(names, rows, rows, split)
        baseline = {n:r.copy() for n,r in rows.items()}
        baseline[NAMES[0]]['scene_token'] = 'other'
        with self.assertRaises(ValueError):
            validate_scope(NAMES, rows, baseline, split)

    def test_missing_front_keyframes_cannot_silently_fallback_or_replace(self):
        from logs.build_review10_package_20261014 import camera_pool
        with workspace_tempdir() as directory:
            row = {'token':'k', 'sample_token':'s', 'filename':'missing.jpg',
                   'timestamp':100, 'is_key_frame':True}
            with self.assertRaisesRegex(ValueError, 'keyframe'):
                camera_pool([row], ['s'], directory)

    def test_missing_sweeps_fallback_is_explicit_and_uses_only_real_keyframes(self):
        from logs.build_review10_package_20261014 import camera_pool
        with workspace_tempdir() as directory:
            (directory/'a.jpg').write_bytes(b'present')
            (directory/'b.jpg').write_bytes(b'present')
            rows = [dict(token='a', sample_token='s1',filename='a.jpg', timestamp=0,is_key_frame=True),
                    dict(token='sweep',sample_token='s1',filename='absent.jpg',timestamp=100,is_key_frame=False),
                    dict(token='b',sample_token='s2',filename='b.jpg',timestamp=500,is_key_frame=True)]
            pool, mode = camera_pool(rows, ['s1','s2'], directory)
            self.assertEqual(mode, 'native_keyframes_2hz_no_interpolation')
            self.assertEqual([r['token'] for r in pool], ['a','b'])

    def test_camera_path_cannot_escape_source_dataset(self):
        from logs.build_review10_package_20261014 import camera_pool
        with workspace_tempdir() as directory:
            row = dict(token='a',sample_token='s',filename='../escape.jpg',timestamp=0,is_key_frame=True)
            with self.assertRaises(ValueError):
                camera_pool([row], ['s'], directory)

    def test_runtime_mismatch_is_refused(self):
        from logs.build_review10_package_20261014 import runtime_record, validate_runtime
        runtime = runtime_record()
        validate_runtime(runtime)
        runtime['pillow'] = 'different'
        with self.assertRaises(ValueError):
            validate_runtime(runtime)

    def test_export_failure_preserves_original_seal_and_does_not_rewrite_completion(self):
        import json
        from unittest.mock import patch
        from logs import build_review10_package_20261014 as recipe
        with workspace_tempdir() as directory:
            path = directory/'status.json'
            seal = {'path':'original','sha256':'sealed','bytes':123}
            path.write_text(json.dumps({'phase':'exporting_two_development_gifs','protocol':seal}))
            with patch.object(recipe,'STATUS',path):
                recipe.fail_status(RuntimeError('problem'))
            status = json.loads(path.read_text())
            self.assertEqual(status['protocol'],seal)
            self.assertEqual(status['phase'],'failed_requires_inspection')
            path.write_text(json.dumps({'phase':'completed_requires_human','protocol':seal}))
            before = path.read_bytes()
            with patch.object(recipe,'STATUS',path):
                recipe.fail_status(RuntimeError('do not rewrite'))
            self.assertEqual(path.read_bytes(),before)

    def test_ten_cards_embed_media_without_claiming_blind_evaluation(self):
        from logs.build_review10_package_20261014 import NAMES, CARDS, document
        media = {n:{'outputs':[{'path':'F:/Scene_cluster/exports/'+n+'.gif'}],'frame_count':2} for n in NAMES}
        rows = {n:{field:'0' for field in CARDS[n][-1]} for n in NAMES}
        audits = {n:{'crossing_v5_audit':[]} for n in NAMES}
        text = document(media,rows,rows,audits)
        for n in NAMES:
            self.assertIn('!['+n+']',text)
        self.assertIn('不是10条全新抽样或独立盲评',text)
        self.assertIn('未知不是安全',text)

    def test_verifier_rejects_redirected_protocol_even_with_same_seal(self):
        import json
        from unittest.mock import patch
        from logs import build_review10_package_20261014 as recipe
        with workspace_tempdir() as directory:
            protocol, copy = directory/'original.json',directory/'copy.json'
            copy.write_text('{}')
            seal = recipe.record(copy)
            status = directory/'status.json'
            status.write_text(json.dumps({'phase':'completed_requires_human','protocol':seal}))
            with patch.object(recipe,'STATUS',status),patch.object(recipe,'PROTOCOL',protocol):
                with self.assertRaisesRegex(ValueError,'path'):
                    recipe.verify(seal['sha256'])

    def test_reuse_strips_historical_feature_rank_and_pending_annotations(self):
        from logs.build_review10_package_20261014 import media_only
        raw = {'scene_name':'scene-0453','scene_token':'t','log_token':'l','frame_count':2,
               'selected_frames':[], 'outputs':[], 'frame_durations_ms':[170,160],
               'features':{'crossing_vehicle_conflict_ratio':0},'risk':.2,'cluster':3,
               'priority_rank':2,'review_status':'pending_human','status':'old'}
        media = media_only(raw)
        self.assertEqual(media['scene_name'],raw['scene_name'])
        self.assertEqual(media['frame_count'],2)
        self.assertFalse(set(media) & {'features','risk','cluster','priority_rank','review_status','status'})
        self.assertIn('features',raw)


if __name__ == '__main__':
    unittest.main()
