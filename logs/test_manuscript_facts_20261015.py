import importlib.util
import unittest


class ManuscriptFactsTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('logs.verify_manuscript_facts_20261015'))
        from logs import verify_manuscript_facts_20261015
        return verify_manuscript_facts_20261015

    def test_fact_table_exact_values(self):
        self.module().validate_fact_table('| F01 | 样本 | 700 / 150 | S01 |', {'F01': '700 / 150'})

    def test_changed_or_missing_fact_refused(self):
        m = self.module()
        for text in ('| F01 | 样本 | 850 / 150 | S01 |', ''):
            with self.assertRaises(ValueError):
                m.validate_fact_table(text, {'F01': '700 / 150'})

    def test_duplicate_or_extra_fact_refused(self):
        m = self.module()
        row = '| F01 | 样本 | 700 / 150 | S01 |'
        for text in (row+'\n'+row, row+'\n| F02 | 未登记 | 5 | S02 |'):
            with self.assertRaises(ValueError):
                m.validate_fact_table(text, {'F01': '700 / 150'})

    def test_correct_number_with_wrong_source_is_refused(self):
        with self.assertRaises(ValueError):
            self.module().validate_fact_table('| F01 | 样本 | 700 / 150 | S05 |', {'F01': '700 / 150'})

    def test_ast_parameter_reader_does_not_execute_module(self):
        m = self.module()
        text = "raise RuntimeError('must not execute')\ndef main():\n p = dict(n_neighbors=15, metric='cosine')"
        self.assertEqual(m.literal_parameters(text, 'p'), {'n_neighbors': 15, 'metric': 'cosine'})

    def test_nonliteral_or_ambiguous_parameters_refused(self):
        m = self.module()
        for text in ('p=dict(n_neighbors=unknown)', 'p=dict(x=1)\np=dict(x=2)'):
            with self.assertRaises(ValueError):
                m.literal_parameters(text, 'p')

    def test_unclosed_math_block_refused(self):
        with self.assertRaises(ValueError):
            self.module().validate_math('$$\nx=1\n')


if __name__ == '__main__':
    unittest.main()
