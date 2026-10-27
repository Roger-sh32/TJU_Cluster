"""Limited writing checks and provenance; not full prose/formula acceptance."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "outputs/论文初稿/第五章_关键场景综合评分方法事实稿_20261024.md"
INDEX = DOCUMENT.with_name(DOCUMENT.stem + "_证据索引.json")
STAGE = "writing_only_scoring_chapter"
REVIEW_STATE = {"status": "not_completed_usage_limit", "result_received": False,
                "agent_id": "01a16c04-26ab-7132-9623-b4c2b25614cf",
                "scope": "requested independent fact/formula/version review; no review returned"}
SOURCE_DEFS = [
    ("C01", "HDBSCAN/scripts/corner_scoring.py", "18c9f88e48087017e5615f0639f13503b54d64335264d94df209fcbc7bbec620"),
    ("C02", "HDBSCAN/scripts/frozen_model.py", "981f38c264c883c0c4d423a9b9c8941ddad4541510f2e1858dc0dfc6c30bf552"),
    ("C03", "HDBSCAN/scripts/feature_selection.py", "36cef6e7d7fed0226377555688e749e853faa777622112605d643b1c229103ee"),
    ("C04", "HDBSCAN/scripts/cluster_umap_hdbscan.py", "be1ffc107673436b2adc348fab4c2b6864635774361ec83ec3d74e38d6c26a7f"),
    ("C05", "HDBSCAN/scripts/corner_case_detection.py", "9ab370b76eee04648807590f9e4b6a98c25f48da3a46fbbe918bca73c2ac7398"),
    ("C06", "HDBSCAN/scripts/experiment_partition.py", "b33756c4c4d95eb4170ab052f7a1fc5f3625eba3783f201e3115087b24ade4db"),
    ("C07", "outputs/论文初稿/方法与开发验证事实稿_20261015.md", "e3cd1034ba06ce052db5ed0ef6f129e1090e6ecf412faff40c2cbe675fd6b536"),
    ("C08", "outputs/论文初稿/基于聚类的自动驾驶路测关键场景识别研究_导师审查骨架稿.md", "69e801dbc82bfc81fabeee0866aae86ec4daffd6a0c244b63c5e2196a1eb7561"),
    ("C09", "knowledge/wiki/HDBSCAN公式与软件输出边界_20261024.md", "59db429fe1c74e5403c1c6c4ce002d69133e7d16c16cc7d530e2ea6f231f1706"),
    ("C10", "logs/hdbscan_synthetic_semantics_20261024.json", "4b1e6f12cc3505fd368813670d90e02f4fa7ed68daedb3c52a16f080bb8505d3"),
    ("C11", "HDBSCAN/tables/human_candidate_causes35_20261024.json", "5a457c29d6ec7c7ddd69901dfb9f73de8143c2176b9f8fd75cf3371a10db46e2"),
    ("C12", "knowledge/sources/参考文献/外文/McInnes_2017_HDBSCAN_JOSS.pdf", "9338398c56bb6a231606af02729c41bee259aafdbddab2d6e5b68ee4340a960d"),
    ("C13", "outputs/论文初稿/方法原始引用_20261016.ris", "e73c12bf2d39a567ce061c4f0096c3fb9b1fb8364dbff876a17fe2cb6b8524eb"),
    ("C14", "HDBSCAN/tables/longitudinal_v7_replay29_comparison_20261015.json", "b7df6d51107f04cf3b7fdf9142fcddf24cec1a997e99277555ce3eab4872bdf3"),
    ("C15", "HDBSCAN/scripts/scene_feature_hdbscan_v5_2.py", "a34af552a0bdc396cec210aed1ebf63c5e20d75c0e084f987e51c1d3302e2974"),
]
FACTS = [
    ("P01", "语义52列与评分33列为可交叉接口", ["C01", "C02", "C03", "C04", "C06"]),
    ("P02", "成员强度与离群量分开且不是危险概率", ["C04", "C09", "C10", "C12", "C13"]),
    ("P03", "稀有性与噪声单样本规模约定", ["C01"]),
    ("P04", "纵向分项与固定工程尺度", ["C01", "C15"]),
    ("P05", "合流/横向/侵入组合及让行衰减", ["C01"]),
    ("P06", "VRU按列存在选分支，不按零值回退", ["C01", "C02", "C11", "C15"]),
    ("P07", "自车响应与四类观测风险组合", ["C01"]),
    ("P08", "决策需求与停止牌修正的条件", ["C01", "C02", "C15"]),
    ("P09", "工程risk与综合权重", ["C01"]),
    ("P10", "开发批次/开发参考/冻结查询三种路径", ["C01", "C02", "C05"]),
    ("P11", "冻结归一化及纯手算SYN说明", ["C01", "C02"]),
    ("P12", "版本、来源、正式结果与待办边界", ["C02", "C06", "C07", "C08", "C14"]),
]


def file_record(path):
    path = Path(path).resolve()
    return {"path": str(path), "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def verify(record):
    actual = file_record(record["path"])
    if actual["sha256"] != record["sha256"] or (
            "bytes" in record and actual["bytes"] != record["bytes"]):
        raise ValueError(f"Binding changed: {record['path']}")


def ensure_new(path):
    if Path(path).exists():
        raise FileExistsError(path)


def validate_text(text, facts, sources):
    ids = [item["id"] for item in facts]
    if len(ids) != len(set(ids)) or set(re.findall(r"【(P\d+)】", text)) != set(ids):
        raise ValueError("Missing, duplicate or unknown registered fact")
    if len(re.findall(r"(?m)^\$\$\s*$", text)) % 2:
        raise ValueError("Unclosed display math block")
    for fact in facts:
        if not fact["sources"] or not set(fact["sources"]).issubset(sources):
            raise ValueError("Fact lacks registered source")
    return True


def assignment_weights(source, function_name, output_name):
    tree = ast.parse(source)
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                    and node.name == function_name)

    def key(node):
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
            return node.slice.value
        if isinstance(node, ast.Attribute):
            return node.attr
        raise ValueError("Unsupported source term")

    expression = None
    for node in ast.walk(function):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Subscript) and not isinstance(target.slice, ast.Constant):
                    continue
                if isinstance(target, (ast.Attribute, ast.Subscript)) and key(target) == output_name:
                    expression = node.value
    if expression is None:
        raise ValueError("Registered assignment missing")
    if isinstance(expression, ast.Call) and isinstance(expression.func, ast.Attribute) and expression.func.attr == "clip":
        expression = expression.args[0]
    result = {}

    def visit(node):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            visit(node.left)
            visit(node.right)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult) and isinstance(node.left, ast.Constant):
            result[key(node.right)] = float(node.left.value)
        elif isinstance(node, (ast.Subscript, ast.Attribute)):
            result[key(node)] = 1.
        else:
            raise ValueError("Unsupported registered weighting expression")
    visit(expression)
    return result


def literal_assignment(path, name):
    for node in ast.parse(Path(path).read_text(encoding="utf8")).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError(f"Missing constant {name}")


def registered_values():
    score_path = ROOT / "HDBSCAN/scripts/corner_scoring.py"
    source = score_path.read_text(encoding="utf8")
    cluster = literal_assignment(ROOT / "HDBSCAN/scripts/feature_selection.py", "CLUSTERING_FEATURES")
    risk = literal_assignment(score_path, "FROZEN_RISK_INPUTS")
    if len(cluster) != len(set(cluster)) or len(risk) != len(set(risk)):
        raise ValueError("Duplicate schema field")
    c = .20 * (1 - 10 / 100) + .25 * .3 + .55 * .4
    return {
        "clustering_columns": len(cluster), "frozen_risk_columns": len(risk),
        "observed_weights": assignment_weights(source, "calculate_grouped_risk", "observed_risk"),
        "combined_weights": assignment_weights(source, "calculate_frozen_corner_scores", "corner_score"),
        "risk_addition": assignment_weights(source, "calculate_grouped_risk", "risk"),
        "strict_sustained_fields": {"vru_sustained_relevance_ratio", "vru_sustained_max_duration"}.issubset(risk),
        "strict_route_field": "crossing_route_conflict_ratio" in risk,
        "SYN_score": c, "SYN_normalized": (c - .2) / (.7 - .2),
    }


def source_records():
    records = {}
    for identity, relative, sha in SOURCE_DEFS:
        path = ROOT / relative
        verify({"path": str(path), "sha256": sha})
        records[identity] = file_record(path)
    return records


def check_document(sources, facts):
    text = DOCUMENT.read_text(encoding="utf8")
    validate_text(text, facts, sources)
    sections = re.findall(r"(?m)^## (5\.[1-5]) ", text)
    if sections != ["5.1", "5.2", "5.3", "5.4", "5.5"]:
        raise ValueError("Changed fifth-chapter structure")
    for token in ("52", "33", "SYN", "0.475", "0.55", "待", "不是"):
        if token not in text:
            raise ValueError(f"Missing registered writing marker: {token}")
    values = registered_values()
    if (values["clustering_columns"], values["frozen_risk_columns"]) != (52, 33):
        raise ValueError("Schema count drift")
    if values["observed_weights"] != {"longitudinal_risk": .35, "interaction_risk": .30,
                                      "vru_risk": .25, "ego_response_risk": .10}:
        raise ValueError("Observed weights drift")
    if values["combined_weights"] != {"rarity": .20, "atypical_norm": .25, "risk": .55}:
        raise ValueError("Composite weights drift")
    return values


def verify_index(expected_sha):
    if not expected_sha:
        raise ValueError("Original writing index digest is required")
    verify({"path": str(INDEX), "sha256": expected_sha})
    index = json.loads(INDEX.read_text(encoding="utf8"))
    if (index["stage"] != STAGE or index["new_realdata_extraction_fit_or_scoring"]
            or index["independent_review"] != REVIEW_STATE):
        raise ValueError("Wrong writing stage")
    verify(index["document"])
    for record in list(index["sources"].values()) + index["integrity"]:
        verify(record)
    values = check_document(index["sources"], index["facts"])
    if values != index["registered_values"]:
        raise ValueError("Registered value mismatch")
    print("Original chapter/body/source checks passed; limited writing checks only")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--register", action="store_true")
    modes.add_argument("--check-only", action="store_true")
    parser.add_argument("--expected-index-sha")
    args = parser.parse_args()
    if args.check_only:
        verify_index(args.expected_index_sha)
        return
    if args.expected_index_sha:
        parser.error("--expected-index-sha requires --check-only")
    ensure_new(INDEX)
    sources = source_records()
    facts = [{"id": identity, "claim": claim, "sources": ids} for identity, claim, ids in FACTS]
    values = check_document(sources, facts)
    old_index = ROOT / "outputs/论文初稿/方法与开发验证事实稿_20261015_证据索引.json"
    verify({"path": str(old_index), "sha256": "d7b82321ea70e63293a20668ea88d99763597b8a9692465095a9ccdaf0d18ac9"})
    index = {"stage": STAGE, "created_at_utc": datetime.now(timezone.utc).isoformat(),
             "task_date": "2026-10-24 Asia/Shanghai", "command": sys.argv,
             "python": sys.executable, "python_version": sys.version,
             "document": file_record(DOCUMENT), "sources": sources, "facts": facts,
             "integrity": [file_record(__file__), file_record(Path(__file__).with_name("test_verify_scoring_chapter_20261024.py")),
                           file_record(old_index)],
             "registered_values": values, "new_realdata_extraction_fit_or_scoring": False,
             "hand_SYN_arithmetic_only": True, "production_scoring_called": False,
             "independent_review": REVIEW_STATE,
             "evaluation_semantics": False, "author_accepted": False,
             "check_scope": "fact/source IDs, five headings, display-math pairing, registered AST values "
                            "and hand SYN arithmetic; NOT all prose/formulas/semantics, school format or formal approval"}
    for record in list(sources.values()) + index["integrity"] + [index["document"]]:
        verify(record)
    with INDEX.open("x", encoding="utf8", newline="\n") as handle:
        json.dump(index, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"status": STAGE, "facts": len(facts), "direct_sources": len(sources),
                      "index_sha256": file_record(INDEX)["sha256"],
                      "body_sha256": index["document"]["sha256"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
