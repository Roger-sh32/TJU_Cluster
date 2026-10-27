import copy
import unittest


class EvaluationMetricsTests(unittest.TestCase):
    def api(self):
        from HDBSCAN.scripts import evaluation_metrics
        return evaluation_metrics

    def test_three_independent_reviews_median_and_missing_not_zero(self):
        reviews = [{'item_id': 'a', 'reviewer': r, 'priority': p}
                   for r, p in zip(('R1', 'R2', 'R3'), (2, 1, 2))]
        reviews += [{'item_id': 'b', 'reviewer': 'R1', 'priority': 0}]
        original = copy.deepcopy(reviews)
        result = self.api().aggregate_reviews(['a', 'b'], reviews, ['R1', 'R2', 'R3'])
        self.assertEqual(result['labels'], {'a': 2, 'b': None})
        self.assertEqual(result['complete_review_count'], 1)
        self.assertEqual(result['complete_agreement_rate'], 0.)
        self.assertEqual(reviews, original)

    def test_duplicate_review_or_unexpected_identity_is_refused(self):
        row = {'item_id': 'a', 'reviewer': 'R1', 'priority': 2}
        for rows in ([row, row], [{**row, 'reviewer': 'R4'}], [{**row, 'item_id': 'b'}]):
            with self.assertRaises(ValueError):
                self.api().aggregate_reviews(['a'], rows, ['R1', 'R2', 'R3'])

    def test_precision_recall_budget_and_unattainable_budget(self):
        labels = {'a': 2, 'b': 0, 'c': 2, 'd': 1}
        result = self.api().ranking_metrics(list(labels), labels, [2], [.5, 1.], max_budget=2)
        self.assertEqual(result['top_k'][2]['precision'], .5)
        self.assertEqual(result['top_k'][2]['recall'], .5)
        self.assertEqual(result['budgets'][.5]['review_count'], 1)
        self.assertFalse(result['budgets'][1.]['achieved'])
        self.assertIsNone(result['budgets'][1.]['review_count'])

    def test_unknown_top_k_bounds_no_backfill_no_full_recall(self):
        labels = {'a': 2, 'b': None, 'c': 2, 'd': 0}
        result = self.api().ranking_metrics(list(labels), labels, [2], [.5])
        top = result['top_k'][2]
        self.assertIsNone(top['precision'])
        self.assertEqual((top['precision_lower'], top['precision_upper']), (.5, 1.))
        self.assertEqual(top['unknown_count'], 1)
        self.assertIsNone(top['recall'])
        self.assertIsNone(result['budgets'][.5]['achieved'])

    def test_missing_outside_top_k_also_disables_full_recall(self):
        result = self.api().ranking_metrics(['a','b'], {'a': 2,'b': None}, [1], [.5])
        self.assertEqual(result['top_k'][1]['precision'], 1.)
        self.assertIsNone(result['top_k'][1]['recall'])

    def test_no_positive_does_not_report_zero_recall_or_budget(self):
        result = self.api().ranking_metrics(['a','b'], {'a': 0,'b': 1}, [1], [.5])
        self.assertIsNone(result['top_k'][1]['recall'])
        self.assertEqual(result['budgets'][.5]['reason'], 'no_positive_labels')

    def test_invalid_ranking_labels_k_and_recall_targets_refused(self):
        for ranking, labels, ks, targets in [
            (['a','a'], {'a': 2}, [1], [.5]), (['a'], {'a': 2,'b': 0}, [1], [.5]),
            (['a'], {'a': True}, [1], [.5]), (['a'], {'a': float('nan')}, [1], [.5]),
            (['a'], {'a': 2}, [2], [.5]), (['a'], {'a': 2}, [True], [.5]),
            (['a'], {'a': 2}, [1], [0]), (['a'], {'a': 2}, [1], [1.1])]:
            with self.assertRaises(ValueError):
                self.api().ranking_metrics(ranking, labels, ks, targets)

    def test_budget_savings_keep_negative_result_and_require_same_target(self):
        api = self.api()
        labels = {'a':0, 'b':0, 'c':2, 'd':2}
        ref = api.ranking_metrics(['a','c','b','d'], labels, [2], [.5])['budgets'][.5]
        new = api.ranking_metrics(['a','b','c','d'], labels, [2], [.5])['budgets'][.5]
        self.assertEqual(api.budget_savings(ref, new)['fraction'], -.5)
        self.assertIsNone(api.budget_savings(ref, {**new, 'achieved': False})['fraction'])
        with self.assertRaises(ValueError):
            api.budget_savings(ref, {**new, 'target_recall': .8})
        with self.assertRaises(ValueError):
            api.budget_savings(ref, {**new, 'label_fingerprint': 'different'})

    def test_seeded_random_baseline_reproducible_without_mutation(self):
        labels = {str(i): 2 if i < 3 else 0 for i in range(8)}
        original = labels.copy()
        first = self.api().random_baseline(labels, [2], [.5], [3,7,11])
        self.assertEqual(first, self.api().random_baseline(labels, [2], [.5], [3,7,11]))
        self.assertEqual(first['exact_expected_precision'], 3/8)
        self.assertEqual(first['uncertainty_kind'], 'random_permutation_variation_not_method_difference_ci')
        self.assertEqual(labels, original)
        with self.assertRaises(ValueError):
            self.api().random_baseline(labels, [2], [.5], [3,3])

    def test_random_baseline_materializes_metric_iterators_once(self):
        api = self.api()
        labels = {'a':2,'b':0}
        expected = api.random_baseline(labels, [1], [.5], [7,8])
        self.assertEqual(api.random_baseline(labels, iter([1]), iter([.5]), [7,8]), expected)

    def test_padded_log_identity_cannot_invent_independent_groups(self):
        with self.assertRaises(ValueError):
            self.api().paired_log_bootstrap(['a','b'], ['b','a'], {'a':2,'b':0},
                                           {'a':'L1','b':'L1 '}, 1, 100, 7)

    def test_log_bootstrap_identical_methods_have_zero_difference(self):
        labels = {str(i): 2 if i < 3 else 0 for i in range(8)}
        groups = {str(i): 'L'+str(i//2) for i in range(8)}
        result = self.api().paired_log_bootstrap(list(labels), list(labels), labels, groups, 2, 50, 7)
        self.assertEqual(result['interval'], [0., 0.])
        self.assertEqual(result['group_count'], 4)

    def test_log_bootstrap_uses_same_resample_and_retains_sign(self):
        labels = {str(i): 2 if i % 2 else 0 for i in range(8)}
        groups = {str(i): 'L'+str(i//2) for i in range(8)}
        good = [str(i) for i in (1,3,5,7,0,2,4,6)]
        bad = list(reversed(good))
        api = self.api()
        forward = api.paired_log_bootstrap(good, bad, labels, groups, 2, 50, 7)
        backward = api.paired_log_bootstrap(bad, good, labels, groups, 2, 50, 7)
        self.assertEqual(forward['interval'], [1.,1.])
        self.assertEqual(backward['interval'], [-1.,-1.])

    def test_bootstrap_does_not_silently_drop_too_small_cohorts(self):
        labels = {str(i): 2 for i in range(5)}
        groups = {'0': 'small', **{str(i): 'big' for i in range(1,5)}}
        result = self.api().paired_log_bootstrap(list(labels), list(labels), labels, groups, 4, 100, 1)
        self.assertGreater(result['invalid_draws'], 0)
        self.assertIsNone(result['interval'])
        self.assertEqual(result['status'], 'incomplete_resamples')

    def test_bootstrap_refuses_missing_labels_or_group_membership(self):
        api = self.api()
        with self.assertRaises(ValueError):
            api.paired_log_bootstrap(['a','b'], ['a','b'], {'a': 2,'b': None}, {'a':'l1','b':'l2'}, 1, 10, 2)
        with self.assertRaises(ValueError):
            api.paired_log_bootstrap(['a','b'], ['a','b'], {'a': 2,'b': 0}, {'a':'l1'}, 1, 10, 2)


if __name__ == '__main__':
    unittest.main()
