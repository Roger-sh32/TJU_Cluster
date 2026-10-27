"""Source-bound SYN array/tree checks, not a clustering experiment."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata as metadata
import json
import math
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "knowledge/sources/参考文献/HDBSCAN原理与实现_20261024"
RETRIEVAL = ROOT / "logs/hdbscan_source_retrieval_20261024.json"
RETRIEVAL_SHA = "a4dee09003a19499b4b119937ba8f10844e2b8ece701bef389a021404c6359c0"
OUTPUT = ROOT / "logs/hdbscan_synthetic_semantics_20261024.json"
WIKI = ROOT / "knowledge/wiki/HDBSCAN公式与软件输出边界_20261024.md"
STAGE = "synthetic_hdbscan_array_tree_semantics_only"


def record(path):
    path = Path(path).resolve()
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def verify(expected):
    actual = record(expected["path"])
    if actual["sha256"] != expected["sha256"] or (
            "bytes" in expected and actual["bytes"] != expected["bytes"]):
        raise ValueError(f"Digest/size mismatch: {expected['path']}")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf8"))


def hand_stability(edges):
    parents = {row[0] for row in edges}
    if not parents:
        raise ValueError("Empty synthetic tree")
    root = min(parents)
    births = {root: 0.0}
    for parent, child, value, size in edges:
        if child in parents:
            if child in births:
                raise ValueError("Duplicate cluster birth")
            births[child] = value
    if births.keys() != parents:
        raise ValueError("Disconnected synthetic cluster")
    result = {parent: 0.0 for parent in parents}
    for parent, child, value, size in edges:
        if not math.isfinite(value) or value < births[parent] or size < 1:
            raise ValueError("Invalid finite synthetic edge")
        result[parent] += (value - births[parent]) * size
    return result


def synthetic_cases():
    if metadata.version("hdbscan") != "0.8.39":
        raise ValueError("This probe is specific to hdbscan 0.8.39")
    import numpy as np
    from hdbscan._hdbscan_reachability import mutual_reachability
    from hdbscan._hdbscan_tree import compute_stability, get_clusters, outlier_scores

    distances = np.array([[0., 1., 4.], [1., 0., 3.], [4., 3., 0.]])
    core = np.array([1., 1., 3.])
    hand = np.maximum(np.maximum(distances, core[None, :]), core[:, None])
    native = mutual_reachability(distances.copy(), min_points=1, alpha=1.0)
    np.testing.assert_array_equal(native, hand)
    cases = {"SYN-DENSE": {"input": distances.tolist(), "min_points": 1, "alpha": 1.,
                           "hand_core": core.tolist(), "hand": hand.tolist(),
                           "native": native.tolist(),
                           "scope": "dense helper only; not automatic MST/Boruvka path"}}
    dtype = np.dtype([("parent", np.intp), ("child", np.intp),
                      ("lambda_val", np.float64), ("child_size", np.intp)])
    fixtures = {
        "SYN-NOISE": [(5, 4, .5, 1), (5, 6, 1., 2), (5, 7, 1., 2),
                      (6, 0, 2., 1), (6, 1, 4., 1), (7, 2, 2., 1), (7, 3, 2., 1)],
        "SYN-EOM-LEAF": [(7, 8, 1., 5), (7, 9, 1., 2), (8, 0, 5., 1),
                         (8, 10, 5., 2), (8, 11, 5., 2),
                         (9, 5, 2., 1), (9, 6, 2., 1),
                         (10, 1, 8., 1), (10, 2, 8., 1),
                         (11, 3, 8., 1), (11, 4, 8., 1)],
    }
    for name, edges in fixtures.items():
        tree = np.array(edges, dtype=dtype)
        stability = {int(k): float(v) for k, v in compute_stability(tree).items()}
        expected = hand_stability(edges)
        if stability != expected:
            raise AssertionError(f"{name}: stability differs")
        scores = outlier_scores(tree)
        if not np.isfinite(scores).all() or np.any(scores < 0) or np.any(scores > 1):
            raise AssertionError("Invalid synthetic outlier values")
        result = {"edges": edges, "hand_stability": expected,
                  "native_stability": stability, "outlier": scores.tolist()}
        methods = ("eom", "leaf") if name == "SYN-EOM-LEAF" else ("eom",)
        for method in methods:
            labels, probabilities, normalized_stabilities = get_clusters(
                tree, stability.copy(), cluster_selection_method=method,
                allow_single_cluster=False, match_reference_implementation=False,
                cluster_selection_epsilon=0.0, max_cluster_size=0)
            item = {"labels": labels.tolist(), "membership": probabilities.tolist(),
                    "selected_cluster_coherence": normalized_stabilities.tolist()}
            if method == "eom" and name == "SYN-NOISE":
                result.update(item)
            else:
                result[method] = item
        cases[name] = result
    noise = cases["SYN-NOISE"]
    if (noise["labels"] != [0, 0, 1, 1, -1]
            or noise["membership"] != [.5, 1., 1., 1., 0.]
            or math.isclose(noise["membership"][-1], 1 - noise["outlier"][-1])):
        raise AssertionError("Synthetic non-complement counterexample failed")
    nested = cases["SYN-EOM-LEAF"]
    if (nested["eom"]["labels"] != [0, 0, 0, 0, 0, 1, 1]
            or nested["leaf"]["labels"] != [-1, 1, 1, 2, 2, 0, 0]):
        raise AssertionError("Synthetic EOM/leaf comparison failed")
    return cases


def source_bindings():
    verify({"path": str(RETRIEVAL), "sha256": RETRIEVAL_SHA})
    retrieval = read_json(RETRIEVAL)
    rows = [record(RETRIEVAL)]
    for item in retrieval["requests"] + retrieval["extracted"]:
        if "path" in item:
            verify(item)
            rows.append({key: item[key] for key in ("path", "bytes", "sha256")})
    sdist = record(RAW / "hdbscan-0.8.39.tar.gz")
    if sdist["sha256"] != "2aa1351f42fa79efdc47d53695381aa9a2efef6d1855b96c42d030646fee74f7":
        raise ValueError("Wrong official 0.8.39 archive")
    dist = metadata.distribution("hdbscan")
    if dist.version != "0.8.39":
        raise ValueError("Wrong local distribution version")
    for name in ("hdbscan_.py", "prediction.py"):
        local = Path(dist.locate_file("hdbscan/" + name))
        if local.read_bytes() != (RAW / ("sdist_" + name)).read_bytes():
            raise ValueError(f"Local source differs from official sdist: {name}")
        rows.append(record(local))
    for path in dist.files:
        if str(path).startswith("hdbscan/") and str(path).endswith(".pyd"):
            rows.append(record(dist.locate_file(path)))
    protected = {
        "HDBSCAN/scripts/cluster_umap_hdbscan.py":
            "be1ffc107673436b2adc348fab4c2b6864635774361ec83ec3d74e38d6c26a7f",
        "HDBSCAN/scripts/corner_scoring.py":
            "18c9f88e48087017e5615f0639f13503b54d64335264d94df209fcbc7bbec620",
        "outputs/论文初稿/方法与开发验证事实稿_20261015.md":
            "e3cd1034ba06ce052db5ed0ef6f129e1090e6ecf412faff40c2cbe675fd6b536",
        "HDBSCAN/tables/human_evidence29_20261024_report.json":
            "9035ce0ea61084e5c4fa1c9f195a2c73a15b29680cb423e90e3a0e5dbdb02e18",
        "HDBSCAN/tables/human_candidate_causes35_20261024.json":
            "5a457c29d6ec7c7ddd69901dfb9f73de8143c2176b9f8fd75cf3371a10db46e2",
    }
    for relative, sha in protected.items():
        path = ROOT / relative
        verify({"path": str(path), "sha256": sha})
        rows.append(record(path))
    verify({"path": str(ROOT / "HDBSCAN/scripts/frozen_model.py"),
            "sha256": "981f38c264c883c0c4d423a9b9c8941ddad4541510f2e1858dc0dfc6c30bf552"})
    rows.append(record(ROOT / "HDBSCAN/scripts/frozen_model.py"))
    for path in (ROOT / "knowledge/sources/参考文献/外文/McInnes_2017_HDBSCAN_JOSS.pdf",
                 ROOT / "logs/hdbscan_semantics_pdf_20261024/joss_page1.png",
                 ROOT / "logs/hdbscan_semantics_pdf_20261024/joss_page2.png"):
        rows.append(record(path))
    for path in (Path(__file__), Path(__file__).with_name("test_hdbscan_semantics_20261024.py")):
        rows.append(record(path))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--worker", action="store_true")
    modes.add_argument("--check-only", action="store_true")
    parser.add_argument("--expected-sha")
    args = parser.parse_args()
    if args.worker:
        result = {"cases": synthetic_cases(), "checks_passed": True,
                  "runtime": {"python": sys.version, "executable": sys.executable,
                              "packages": {p: metadata.version(p) for p in
                                           ("hdbscan", "numpy", "scipy", "scikit-learn")}}}
        print(json.dumps(result, allow_nan=False))
        return
    if args.check_only:
        if not args.expected_sha:
            raise ValueError("Original SYN result digest is required")
        verify({"path": str(OUTPUT), "sha256": args.expected_sha})
        result = read_json(OUTPUT)
        for item in result["inputs"] + result["outputs"]:
            verify(item)
        if result["stage"] != STAGE or not result["child"]["checks_passed"]:
            raise ValueError("Invalid synthetic result state")
        print("Original SYN source/output check passed; no computations repeated")
        return
    if args.expected_sha:
        parser.error("--expected-sha requires --check-only")
    if OUTPUT.exists():
        raise FileExistsError("Do not overwrite/re-run a completed SYN evidence artifact")
    if not WIKI.exists():
        raise FileNotFoundError("Write the bounded wiki note before binding outputs")
    sources = source_bindings()
    wiki_before = record(WIKI)
    env = os.environ.copy()
    env.update({k: "1" for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                                "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "NUMBA_NUM_THREADS")})
    env["MKL_THREADING_LAYER"] = "SEQUENTIAL"
    command = [sys.executable, "-X", "utf8", str(Path(__file__).resolve()), "--worker"]
    child = subprocess.run(command, capture_output=True, text=True, encoding="utf8",
                           errors="strict", timeout=25, env=env, check=True)
    payload = json.loads(child.stdout)
    for item in sources + [wiki_before]:
        verify(item)
    output = {"stage": STAGE, "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "command": sys.argv, "child_command": command, "timeout_seconds": 25,
              "child_env_overrides": {k: env[k] for k in
                                     ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                                      "NUMEXPR_NUM_THREADS", "NUMBA_NUM_THREADS", "MKL_THREADING_LAYER")},
              "child_exit_code": child.returncode, "child_stderr": child.stderr,
              "child": payload, "inputs": sources, "outputs": [wiki_before],
              "estimator_fit": False, "model_load": False, "scene_data": False,
              "evaluation": False, "production_change": False,
              "paper_fulltext_verified": False, "formal_choice": False,
              "compiled_equivalence_to_official_build": "not_proven; local binaries recorded only"}
    with OUTPUT.open("x", encoding="utf8", newline="\n") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"status": "completed_SYN_only", "cases": list(payload["cases"]),
                      "original_sha256": record(OUTPUT)["sha256"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
