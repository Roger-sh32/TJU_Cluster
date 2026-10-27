# 旧网格入口绑定影响核对

日期：2026-10-16，Asia/Shanghai。前一目标轮形成第六章事实稿及来源索引，属于实际进展。本轮补查旧网格来源保护修复前的既有绑定，不实现修复，不改参数或启动拟合。

## 范围

已知问题仍为旧 `grid_search.py` 缺少提取来源门控；先前同表preflight差异已有记录，本轮不重复执行拟合入口。本轮仅扫描项目根目录顶层JSON及 `HDBSCAN/`、`Kmeans/`、`logs/`、`knowledge/`、`outputs/` 下可读取JSON中的文件名/源码摘要引用。不扫描 `nuScenes/`、`exports/`、Git目录或模型pickle，不解释评价场景内容、评分或标签。

目标是区分“当前文件的摘要绑定”“另一份快照文件的绑定”“命令/说明引用”和“只有摘要但无法定位文件”。这些不能混为一谈。未扫描范围或读取失败必须保留，不能据没有发现就宣布全仓库无绑定。

## 单次只读扫描配方

下面仅生成新的扫描证据文件，禁止覆盖。代码中的分类自检是合成路径/摘要，不运行真实脚本。对JSON先作文件名/摘要字节匹配，仅匹配文件才解析并检查相关叶节点；不会输出不相关的场景字段或标签。

```powershell
@'
import datetime, hashlib, json, os
from pathlib import Path

root=Path.cwd().resolve()
target=root/"HDBSCAN/scripts/grid_search.py"
output=root/"logs/grid_binding_inventory_20261016.json"
if output.exists(): raise FileExistsError("Do not overwrite binding inventory")
target_sha=hashlib.sha256(target.read_bytes()).hexdigest()
assert target_sha=="eb0f615a35f1287dfd0aab2f035a07fbc5abafa47cd4db1baea7a19488da4485"
scopes=["HDBSCAN","Kmeans","logs","knowledge","outputs"]
errors=[]; files=set(root.glob("*.json"))
def walk_error(error):
    errors.append({"kind":"walk_error","path":str(error.filename),"error":str(error)})
for scope in scopes:
    for directory,dirs,names in os.walk(root/scope,followlinks=False,onerror=walk_error):
        safe=[]
        for name in dirs:
            if name.lower()==".git": continue
            candidate=Path(directory)/name
            try:
                if candidate.resolve().is_relative_to(root): safe.append(name)
                else: errors.append({"kind":"outside_root_directory_skipped","path":str(candidate)})
            except OSError as error:
                errors.append({"kind":"resolve_error","path":str(candidate),"error":str(error)})
        dirs[:]=safe
        for name in names:
            if name.lower().endswith(".json"): files.add(Path(directory)/name)
def is_grid(value):
    return isinstance(value,str) and value.replace("\\","/").lower().endswith("/grid_search.py") or value=="grid_search.py"
def current_path(value):
    if not is_grid(value): return False
    p=Path(value)
    return (p if p.is_absolute() else root/p).resolve()==target
def walk(value,location=()):
    found=[]; handled=set()
    if isinstance(value,dict):
        if is_grid(value.get("path")) and isinstance(value.get("sha256"),str):
            found.append({"json_location":list(location),"kind":"current_file_record_binding" if current_path(value["path"]) else "other_file_record_binding", "path":value["path"],"sha256":value["sha256"],"matches_current_bytes":value["sha256"].lower()==target_sha})
            handled.update(("path","sha256"))
        for key,child in value.items():
            if key in handled: continue
            if is_grid(key) and isinstance(child,str) and len(child)==64 and all(c in "0123456789abcdefABCDEF" for c in child):
                found.append({"json_location":list(location+(key,)),"kind":"named_source_digest","name":key,"sha256":child,"matches_current_bytes":child.lower()==target_sha})
            else: found.extend(walk(child,location+(key,)))
    elif isinstance(value,list):
        for i,child in enumerate(value): found.extend(walk(child,location+(i,)))
    elif isinstance(value,str):
        if value.lower()==target_sha:
            found.append({"json_location":list(location),"kind":"unattributed_digest_reference","sha256":value})
        elif "grid_search.py" in value.lower():
            # Preserve only the target reference; do not copy unrelated scene prose.
            found.append({"json_location":list(location),"kind":"path_reference" if is_grid(value) else "text_or_command_reference","is_current_file_path":current_path(value) if is_grid(value) else None})
    return found

synthetic=[({"path":str(target),"sha256":target_sha},"current_file_record_binding"),
({"path":str(root/"logs/SYN_snapshot/grid_search.py"),"sha256":target_sha},"other_file_record_binding"),
({"grid_search.py":target_sha},"named_source_digest"),
(["HDBSCAN/scripts/grid_search.py"],"path_reference"),
({"note":"SYN run grid_search.py --preflight"},"text_or_command_reference"),
({"digest":target_sha},"unattributed_digest_reference")]
for value,kind in synthetic: assert [r["kind"] for r in walk(value)]==[kind]
assert walk({"path":str(root/"HDBSCAN/scripts/not_grid.py"),"sha256":"0"*64})==[]
assert walk({"grid_search.py":target_sha.upper()})[0]["matches_current_bytes"] is True
inventory=[]; matched=[]
for path in sorted(files,key=lambda p:str(p).lower()):
    if path==output: continue
    try:
        if not path.resolve().is_relative_to(root):
            errors.append({"kind":"outside_root_file_skipped","path":str(path)});continue
        data=path.read_bytes()
        rec={"path":str(path.relative_to(root)),"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()}
        inventory.append(rec)
        if b"grid_search.py" not in data.lower() and target_sha.encode() not in data.lower(): continue
        value=json.loads(data.decode("utf-8-sig"))
        references=walk(value)
        matched.append({"source":rec,"references":references})
    except (OSError,UnicodeError,ValueError) as error:
        errors.append({"kind":"read_or_parse_error","path":str(path),"error":str(error)})
counts={}
for item in matched:
    for reference in item["references"]:
        key=reference["kind"];counts[key]=counts.get(key,0)+1
result={"stage":"read_only_grid_binding_inventory_not_repair","created_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
"target":{"path":str(target),"sha256":target_sha,"bytes":target.stat().st_size},"scope_roots":scopes,"root_top_level_json_included":True,
"excluded":["nuScenes","exports",".git","non-JSON files","pickle contents"],"inventory":inventory,"matched":matched,"reference_kind_counts":counts,"errors_or_skips":errors,
"synthetic_classifier_cases":len(synthetic)+2,"code_modified":False,"fit_started":False,"absence_proven_globally":False}
with output.open("x",encoding="utf8") as stream: json.dump(result,stream,ensure_ascii=False,indent=2)
print(json.dumps({"inspected_json":len(inventory),"matched_files":len(matched),"reference_kind_counts":counts,"errors_or_skips":errors,"output_sha256":hashlib.sha256(output.read_bytes()).hexdigest()},ensure_ascii=False))
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -c "import sys; exec(compile(sys.stdin.buffer.read().decode('utf8'),'grid_binding_scan','exec'))"
```

## 状态

单次扫描exit0：读取180份JSON，3份出现相关引用，找到2条当前文件记录绑定及2条路径引用。8个合成分类自检通过。证据 `logs/grid_binding_inventory_20261016.json` 为40090字节，ORIGINAL SHA256 `e59127adb03059d47593a99e27080aba3b871f476b93101213ceb925bd996a20`。不重复生成或刷新同名证据。

| 匹配文件 | 引用类别 | 影响解释 |
| --- | --- | --- |
| `logs/execution_chain_audit_sources_20261016.json` | 当前文件路径及SHA256绑定 | 当前脚本字节若改变，该源记录将不再与当前路径相符 |
| `logs/entry_guard_pair_verified_20261016.json` | 当前文件路径及SHA256绑定，另有命令路径 | 绑定的是当时成对preflight所用源码，不是正式模型批准 |
| `logs/grid_guard_preflight_20261016.json` | 仅命令中的路径引用 | 本条不是新增的源码摘要绑定，不据它增加“受封印文件”计数 |

两条直接记录的SHA256均为 `eb0f615a35f1287dfd0aab2f035a07fbc5abafa47cd4db1baea7a19488da4485`，与当前源文件相符。仅在内存中对原字节追加换行再求摘要，所得摘要与两记录均不同；文件未修改。这说明即使不改变算法语义，字节变化也会使摘要关系失配，但没有执行或验证任何修复实现。

扫描时 `logs/tmpb3irnoc7/` 和 `logs/tmpt7jfoeol/` 拒绝访问，已记录WinError5，没有修改ACL或删除目录。其他明确未扫描范围，以及非JSON内的源码/文档关系，不在本结论内。字节预筛依赖通常的ASCII/UTF8文件名或摘要字面量；完全Unicode转义引用、非UTF8形式和不同字段命名也不能据此排除。路径按项目根解析，缺少工作目录的相对命令不构成明确的当前文件摘要绑定。

这是一份扫描时点快照，不新增180份JSON的全局冻结要求，也不是拟合入口使用的正式协议。以后合法变更仍按对应文件自身协议处理；历史清单不能重写成当前结果，若需再调查应另建版本。

结论是“已定位到具体直接绑定”，不是“全仓库无其他绑定”或“所有旧实验只依赖这两份记录”。修复前仍须确定兼容既有封印的版本迁移方式；不能通过改写旧SHA256使历史证据看起来有效。本轮不选择/实施新入口，不宣称来源保护缺口已修复，原候选实验禁用警示继续有效。

## 后续只读复核

下面核对既有扫描证据、180份当时已读文件、两条具体绑定及内存摘要对照，不重新枚举全仓库，不重新访问拒读目录，也不证明未扫描区没有绑定。

```powershell
@'
import hashlib,json
from pathlib import Path
root=Path.cwd().resolve()
p=root/"logs/grid_binding_inventory_20261016.json"
assert hashlib.sha256(p.read_bytes()).hexdigest()=="e59127adb03059d47593a99e27080aba3b871f476b93101213ceb925bd996a20"
d=json.loads(p.read_text(encoding="utf8"))
assert len(d["inventory"])==180 and len(d["matched"])==3
assert d["synthetic_classifier_cases"]==8 and d["absence_proven_globally"] is False
target=Path(d["target"]["path"])
assert target.resolve()==root/"HDBSCAN/scripts/grid_search.py"
actual=hashlib.sha256(target.read_bytes()).hexdigest()
assert actual==d["target"]["sha256"]
perturbed=hashlib.sha256(target.read_bytes()+b"\n").hexdigest()
assert perturbed!=actual
indexed={r["path"]:r for r in d["inventory"]}
for relative,r in indexed.items():
    path=root/relative
    assert path.resolve().is_relative_to(root)
    assert path.stat().st_size==r["bytes"]
    assert hashlib.sha256(path.read_bytes()).hexdigest()==r["sha256"],relative
counts={}; bindings=[]
for matched in d["matched"]:
    r=matched["source"];assert indexed[r["path"]]==r
    source=json.loads((root/r["path"]).read_text(encoding="utf-8-sig"))
    for reference in matched["references"]:
        kind=reference["kind"];counts[kind]=counts.get(kind,0)+1
        value=source
        for key in reference["json_location"]: value=value[key]
        if kind=="current_file_record_binding":
            assert Path(value["path"]).resolve()==target.resolve()
            assert value["sha256"]==reference["sha256"]==actual
            assert reference["matches_current_bytes"] is True
            assert value["sha256"]!=perturbed
            bindings.append(r["path"].replace("\\","/"))
        elif kind=="path_reference":
            assert isinstance(value,str) and value.replace("\\","/").endswith("grid_search.py")
        else: raise AssertionError("Unexpected recorded class")
assert counts==d["reference_kind_counts"]=={"current_file_record_binding":2,"path_reference":2}
assert set(bindings)=={"logs/execution_chain_audit_sources_20261016.json","logs/entry_guard_pair_verified_20261016.json"}
assert len(d["errors_or_skips"])==2
print("PASS: original180 JSON hashes, 2 current-file bindings and 2 path references; no source edit or full-scope absence claim")
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -c "import sys; exec(compile(sys.stdin.buffer.read().decode('utf8'),'grid_binding_check','exec'))"
```

上述只读复核已执行exit0，180份当时已读JSON摘要、两条当前文件绑定、两条路径引用与原清单一致。内存换行摘要对照不修改文件，不等于执行修复回归。

独立窄审未发现有根据的P1/P2；审查者核对了原清单摘要、三份匹配JSON当前摘要和必要源码，并确认未将路径引用/合成snapshot计入实际直接绑定。审查者未重扫或逐份复核全部180文件，未覆盖拒读/排除区域，不为全局完整性或正式实验安全背书。没有生产代码/参数/特征/模型改动、拟合、评价或Git提交。来源保护修复仍暂挂。
