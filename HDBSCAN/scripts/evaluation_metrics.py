"""In-memory offline metrics, not an authorized entry to the real holdout data.

No dataset loading, fitting, label generation or scene lookup occurs here.
Caller supplies frozen total orders; tie-breaking must be fixed before labels.
"""

from collections import Counter
from fractions import Fraction
import hashlib
import json
import math
import random


def _ids(values):
    result = list(values)
    if (not result or any(not isinstance(v, str) or not v or v != v.strip() for v in result)
            or len(set(result)) != len(result)):
        raise ValueError('Expected nonempty unique string identities')
    return result


def _priority(value):
    if value is not None and (type(value) is not int or value not in (0, 1, 2)):
        raise ValueError('Priority must be integer0/1/2 or None for unknown')


def _integer(value, minimum=1):
    if type(value) is not int or value < minimum:
        raise ValueError('Expected integer within allowed range')


def _ranking(ranking, labels):
    identities, order = _ids(labels), _ids(ranking)
    if set(order) != set(identities):
        raise ValueError('Ranking must contain exactly the same full cohort')
    for value in labels.values():
        _priority(value)
    return order


def aggregate_reviews(item_ids, reviews, reviewers):
    identities, reviewers = _ids(item_ids), _ids(reviewers)
    if len(reviewers) != 3:
        raise ValueError('Protocol requires exactly three independent reviewers')
    collected = {item: {} for item in identities}
    for row in reviews:
        item, reviewer, value = row['item_id'], row['reviewer'], row['priority']
        _priority(value)
        if item not in collected or reviewer not in reviewers or reviewer in collected[item]:
            raise ValueError('Unexpected or duplicate item/reviewer identity')
        collected[item][reviewer] = value
    raw = {item: [collected[item].get(r) for r in reviewers] for item in identities}
    labels = {item: sorted(values)[1] if None not in values else None for item, values in raw.items()}
    complete = [values for values in raw.values() if None not in values]
    return {'labels': labels, 'raw_independent_ratings': raw, 'reviewers': reviewers,
            'complete_review_count': len(complete), 'missing_review_count': len(raw)-len(complete),
            'complete_agreement_rate': sum(len(set(v)) == 1 for v in complete)/len(complete) if complete else None,
            'agreement_note': 'Complete-case exact agreement, not ordinal inter-rater reliability.'}


def ranking_metrics(ranking, labels, ks=(10, 20, 30), target_recalls=(.5, .8, 1.), max_budget=None):
    order = _ranking(ranking, labels)
    ks, targets = list(ks), list(target_recalls)
    if not ks or len(set(ks)) != len(ks) or not targets or len(set(targets)) != len(targets):
        raise ValueError('Nonempty unique K values and recall targets required')
    for k in ks:
        _integer(k)
        if k > len(order):
            raise ValueError('K exceeds fixed cohort; no silent truncation')
    for target in targets:
        if type(target) not in (int, float) or not math.isfinite(target) or not 0 < target <= 1:
            raise ValueError('Recall target must be finite and in (0,1]')
    maximum = len(order) if max_budget is None else max_budget
    _integer(maximum)
    if maximum > len(order):
        raise ValueError('Review budget exceeds cohort')
    missing, positives = sum(v is None for v in labels.values()), sum(v == 2 for v in labels.values())
    fingerprint = hashlib.sha256(json.dumps(labels, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    top = {}
    for k in ks:
        values = [labels[item] for item in order[:k]]
        hit, unknown = values.count(2), values.count(None)
        top[k] = {'k': k, 'positive_count': hit, 'unknown_count': unknown,
                  'precision': hit/k if not unknown else None,
                  'precision_lower': hit/k, 'precision_upper': (hit+unknown)/k,
                  'recall': hit/positives if not missing and positives else None}
    budgets = {}
    for target in targets:
        reason = 'incomplete_labels' if missing else 'no_positive_labels' if not positives else None
        needed = math.ceil(Fraction(str(target))*positives)
        hits, count = 0, None
        if reason is None:
            for i, item in enumerate(order[:maximum], 1):
                hits += labels[item] == 2
                if hits >= needed:
                    count = i
                    break
        achieved = None if reason else count is not None
        budgets[target] = {'target_recall': target, 'review_count': count, 'achieved': achieved,
                           'reason': reason or (None if achieved else 'not_reached_within_budget'),
                           'max_budget': maximum, 'label_fingerprint': fingerprint}
    return {'cohort_size': len(order), 'known_positive_count': positives, 'missing_count': missing,
            'label_fingerprint': fingerprint, 'top_k': top, 'budgets': budgets,
            'note': 'Fixed TopK, no NA backfill; recall/budget require complete labels and positives.'}


def budget_savings(reference, candidate):
    if (reference['target_recall'] != candidate['target_recall']
            or not reference.get('label_fingerprint')
            or reference['label_fingerprint'] != candidate.get('label_fingerprint')):
        raise ValueError('Budget comparison requires same recall target, cohort and labels')
    available = reference['achieved'] is True and candidate['achieved'] is True
    if available:
        _integer(reference['review_count'])
        _integer(candidate['review_count'])
    return {'fraction': 1-candidate['review_count']/reference['review_count'] if available else None,
            'unit': 'reviewed_scene_count_not_time_or_road_mileage'}


def random_baseline(labels, ks, target_recalls, seeds):
    ks, target_recalls = list(ks), list(target_recalls)
    seeds = list(seeds)
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError('Random seeds must be nonempty and unique')
    for seed in seeds:
        _integer(seed, 0)
    runs = []
    for seed in seeds:
        order = sorted(labels)
        random.Random(seed).shuffle(order)
        runs.append({'seed': seed, 'ranking': order,
                     'metrics': ranking_metrics(order, labels, ks, target_recalls)})
    summaries = {}
    for k in ks:
        samples = [r['metrics']['top_k'][k] for r in runs]
        summaries[k] = {key: {'mean': sum(v)/len(v), 'min': min(v), 'max': max(v)}
                        for key in ('precision_lower', 'precision_upper')
                        for v in [[r[key] for r in samples]]}
    return {'runs': runs, 'top_k_summary': summaries,
            'exact_expected_precision': sum(v == 2 for v in labels.values())/len(labels)
                                        if all(v is not None for v in labels.values()) else None,
            'uncertainty_kind': 'random_permutation_variation_not_method_difference_ci'}


def _quantile(values, probability):
    ordered = sorted(values)
    index = (len(ordered)-1)*probability
    low, high = math.floor(index), math.ceil(index)
    return ordered[low] + (ordered[high]-ordered[low])*(index-low)


def paired_log_bootstrap(candidate, reference, labels, groups, k, iterations=2000, seed=42):
    candidate, reference = _ranking(candidate, labels), _ranking(reference, labels)
    _integer(k)
    _integer(iterations, 2)
    _integer(seed, 0)
    if k > len(labels) or set(groups) != set(labels) or any(v is None for v in labels.values()):
        raise ValueError('Bootstrap requires full known labels, same cohort and valid K')
    if any(not isinstance(g, str) or not g.strip() or g != g.strip() for g in groups.values()):
        raise ValueError('Invalid acquisition-log identity')
    logs = sorted(set(groups.values()))
    if len(logs) < 2:
        raise ValueError('At least two acquisition logs required')
    rng, differences, invalid = random.Random(seed), [], 0
    for _ in range(iterations):
        weights = Counter(rng.choice(logs) for _ in logs)
        # Shared whole-log resample; duplicate scenes retain their frozen ranking position.
        sample_candidate = [item for item in candidate for _ in range(weights[groups[item]])]
        sample_reference = [item for item in reference for _ in range(weights[groups[item]])]
        if len(sample_candidate) < k:
            invalid += 1
            continue
        differences.append((sum(labels[i] == 2 for i in sample_candidate[:k])
                            - sum(labels[i] == 2 for i in sample_reference[:k]))/k)
    return {'status': 'incomplete_resamples' if invalid else 'computed',
            'interval': None if invalid else [_quantile(differences, .025), _quantile(differences, .975)],
            'point_difference': (sum(labels[i] == 2 for i in candidate[:k])
                                 - sum(labels[i] == 2 for i in reference[:k]))/k,
            'group_count': len(logs), 'iterations': iterations, 'seed': seed, 'invalid_draws': invalid,
            'interval_kind': 'paired_whole_log_percentile_95',
            'note': 'Conditional on frozen total orders; no refit. Few logs limit inference; no CI if any draw is too small.'}
