"""Observe extraction fallbacks without changing feature values or decisions."""

from collections import Counter
from datetime import datetime, timezone
import math
from numbers import Real

import pandas as pd


class ExtractionAudit:
    def __init__(self, example_limit=3):
        if example_limit < 0:
            raise ValueError('Negative example limit')
        self.example_limit = example_limit
        self.errors = {}

    def record_error(self, scene, stage, error, frame_index=None):
        key = (scene['name'], scene['token'], stage, type(error).__name__)
        record = self.errors.setdefault(key, {
            'scene_name': scene['name'], 'scene_token': scene['token'],
            'stage': stage, 'error_type': type(error).__name__, 'count': 0, 'examples': []})
        record['count'] += 1
        if len(record['examples']) < self.example_limit:
            record['examples'].append({'frame_index': frame_index, 'message': str(error)[:1000]})

    def report(self, frame):
        if not {'scene_name', 'scene_token'}.issubset(frame.columns):
            raise ValueError('Audit requires scene identities')
        counts, cells = {}, []
        for row in frame.to_dict('records'):
            for column, value in row.items():
                if pd.isna(value):
                    kind = 'nan'
                elif isinstance(value, Real) and math.isinf(value):
                    kind = 'positive_inf' if value > 0 else 'negative_inf'
                else:
                    continue
                counter = counts.setdefault(column, {'nan': 0, 'positive_inf': 0, 'negative_inf': 0})
                counter[kind] += 1
                cells.append({'scene_name': row['scene_name'], 'scene_token': row['scene_token'],
                              'column': column, 'kind': kind})
        errors = list(self.errors.values())
        total_errors = sum(r['count'] for r in errors)
        stages = Counter()
        for record in errors:
            stages[record['stage']] += record['count']
        return {
            'created_at_utc': datetime.now(timezone.utc).isoformat(),
            'scope': 'pre-fill scene aggregates and caught query exceptions only',
            'scene_count': len(frame), 'column_count': len(frame.columns),
            'scene_names': frame.scene_name.tolist(),
            'nonfinite_cell_count': len(cells), 'nonfinite_by_column': counts,
            'nonfinite_cells': cells, 'query_exception_count': total_errors,
            'query_exception_counts_by_stage': dict(stages), 'query_errors': errors,
            'observed_checks_clean': not cells and total_errors == 0,
            'semantic_validity_verified': False,
            'legacy_fill_policy': {'nan': 0.0, 'positive_inf': 30.0, 'negative_inf': 30.0},
            'limitations': [
                'No guarantee about intermediate values discarded before scene aggregation.',
                'Empty observations and explicit finite defaults are not calculation errors here.',
                'Counts are exceptions, not affected frames or rates; one frame may raise repeatedly.',
                'No semantic, risk or expert acceptance; zeros still require contextual interpretation.',
            ],
        }
