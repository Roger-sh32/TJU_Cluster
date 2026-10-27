# nuScenes 数据能力核验记录

日期：2026-10-16，Asia/Shanghai。环境：`D:/Python/Conda/envs/autodrive-cluster/python.exe`；SDK 1.2.0。状态：只读结构核验及知识文档窄范围复核完成。不是实验执行或特征语义验收。

## 执行与产出

先从已保存官方目录提取 C-ICAP 2024 A.1/A.2 的两个实际链接，用验证 CA/主机名的 HTTPS、25 秒超时、12 MiB 上限请求；均 HTTP403。没有 PDF 落盘，没有 ZIP、登录绕过或反复重试。原目录响应为 gzip 字节，解析时仅在内存解压，原文件没有改动。两次失败已写入 `knowledge/sources/标准项目/CICAP2024行车条款_20261016/retrieval_manifest.json`。

随后只读本地通用 ontology、四份静态地图字段和 SDK/项目源代码，生成 `logs/nuscenes_capability_inventory_20261016.json` 与 `logs/nuscenes_capability_nested_20261016.json`。第一份登记源文件路径/字节数/SHA256、图层数量和字段；第二份递归检查灯及道路分隔记录的字段，避免只看顶层而漏掉 `color`。这不是逐场景数据统计。

官方 schema 使用 HTTPS 验证、25 秒超时和 1 MiB 上限，HTTP200、10333 字节，原字节保存到 `knowledge/sources/数据说明/nuScenes能力核验_20261016/schema_nuscenes_master.md`；响应元数据见同目录 manifest。检索时间 `2026-10-16T01:43:39.299218+00:00`，SHA256 `07b34570d0df3e8d75dd2c9f1b8251275a16fd4b83ac7d0ec2db9334d2325385`。该快照来自 upstream master，不宣称与安装版完全一致。

可复用结论放在[数据能力与特征边界](F:/Scene_cluster/knowledge/wiki/nuScenes数据能力与特征边界_20261016.md)。没有打开 scene/sample/sample_annotation/ego_pose、图像或真实评价标签；没有场景提取、拟合、打分、排名、下载数据集、导出媒体或修改源数据。生产代码、52字段、公式、阈值和旧封印保持不变。

## 可复核命令

以下在项目根目录执行，仅读取固定结构清单和其列出的字典/地图/源代码；不重新下载或改写清单。重建字段集合只检查结构，不读取场景轨迹。命令通过只能说明列出的结构与摘要一致，不能验证本文全部语义判断或原算法效果。

```powershell
@'
import hashlib, json
from pathlib import Path

root = Path.cwd()
def load(path):
    return json.loads(Path(path).read_text(encoding="utf8"))
def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def check_source(record):
    path = Path(record["path"])
    assert path.stat().st_size == record["bytes"], str(path)
    assert digest(path) == record["sha256"], str(path)
def recursive_keys(value):
    keys = set()
    if isinstance(value, dict):
        keys.update(value)
        for child in value.values():
            keys.update(recursive_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(recursive_keys(child))
    return keys

inventory = load("logs/nuscenes_capability_inventory_20261016.json")
nested = load("logs/nuscenes_capability_nested_20261016.json")
assert digest("logs/nuscenes_capability_inventory_20261016.json") == "60bdcd2180bd68e854c7234f080271652b8814ed7ef5755776dd1e3b2fcbbdb0"
assert digest("logs/nuscenes_capability_nested_20261016.json") == "1e0acc8b039587bf5428ae2c5344f2629e0e986f10c7adcd9dfce77595f21009"
assert inventory["sdk_version"] == "1.2.0"
assert len(inventory["maps"]) == len(nested["maps"]) == 4
check_source(inventory["sdk_source"])
check_source(inventory["category_source"])
check_source(inventory["visibility_source"])
categories = load(inventory["category_source"]["path"])
assert len(categories) == inventory["category_count"] == 23
by_name = {r["name"]: r["description"] for r in categories}
for name, description in inventory["selected_category_definitions"].items():
    assert by_name[name] == description
assert load(inventory["visibility_source"]["path"]) == inventory["visibility_levels"]
assert len(inventory["visibility_levels"]) == 4
for record, deep in zip(inventory["maps"], nested["maps"]):
    check_source(record["source"])
    assert (root / deep["file"]).resolve() == Path(record["source"]["path"]).resolve()
    assert deep["source_sha256"] == record["source"]["sha256"]
    data = load(record["source"]["path"])
    assert data["version"] == record["version"] == "1.3"
    assert sorted(data) == record["top_level_keys"]
    for layer, expected in record["selected_layer_schemas"].items():
        assert len(data[layer]) == expected["count"]
        assert sorted(set().union(*(set(r) for r in data[layer]))) == expected["field_names"]
    for layer in ("traffic_light", "road_divider", "lane_divider"):
        assert sorted(recursive_keys(data[layer])) == deep[layer + "_nested_keys"]
    light_keys = deep["traffic_light_nested_keys"]
    matches = sorted(k for k in light_keys if any(t in k.lower() for t in ("timestamp", "sample_token", "phase", "state")))
    assert matches == deep["temporal_name_matches"] == []
    assert "color" in light_keys
source_dir = Path("knowledge/sources/数据说明/nuScenes能力核验_20261016")
for record in load(source_dir / "retrieval_manifest.json")["records"]:
    assert digest(source_dir / record["file"]) == record["sha256"]
failure_dir = Path("knowledge/sources/标准项目/CICAP2024行车条款_20261016")
failed = load(failure_dir / "retrieval_manifest.json")
assert len(failed["records"]) == 2
parent = failed["source_page_record"]
assert digest(parent["path"]) == parent["sha256"]
for record in failed["records"]:
    assert record["saved"] is False and "403" in record["error"]
    assert not (failure_dir / record["file"]).exists()
print("PASS: 4 map schemas, 23 categories, 4 visibility levels, nested keys, source hashes and 2 absent failed PDFs")
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -c "import sys; exec(compile(sys.stdin.buffer.read().decode('utf8'),'capability_check','exec'))"
```

## 最终检查

文档中的结构复核命令已执行，exit0：四地图、23类别、四档可见性、递归字段与源文件摘要一致；两个失败附录的PDF均不存在。另只读确认 `traffic_light[].items[].color` 的实际嵌套路径，没有读取逐场景观测。

对照既有原始摘要，10个生产模块和4份原稿/索引/引文补注件全部相同。链路审计索引 ORIGINAL SHA256 `0900518237ffa258c4e051a2fd47190e1582ccfb62098560039e1c4f210d3dea` 及其19项源/证据摘要另查通过。没有更新任何旧摘要或封印。`git diff --check` 对本轮修改的既有入口文档通过。

窄范围独立文档复核未发现有根据的P1/P2，四类边界和通用类别分支描述均与所给证据相符。复核者仅读文档、清单、schema和必要源码，未独立运行哈希/结构检查；上述一致性检查由主线程执行。加上固定清单摘要断言后重跑文档内命令，仍exit0；新文档本地链接和空白检查通过。

本轮不宣称已运行 HDBSCAN 全套测试、全部历史封印重放或人工语义验收；没有修改其实现。设计决定与正式实验仍按原队列暂挂。
