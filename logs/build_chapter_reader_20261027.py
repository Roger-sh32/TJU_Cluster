"""Package four immutable manuscript chapters without rewriting their bytes."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re


OUTPUT_DIR = Path('outputs/论文初稿')
READER_NAME = '第三至六章_方法与开发验证连续阅读版_20261027.md'
MANIFEST_NAME = '第三至六章_方法与开发验证连续阅读版_20261027_来源索引.json'
IMPLEMENTATION = ('logs/build_chapter_reader_20261027.py',
                  'logs/test_chapter_reader_20261027.py')
CHAPTERS = [
    dict(chapter=3, body='outputs/论文初稿/第三章_研究对象数据证据与总体框架事实稿_20261017.md',
         index='outputs/论文初稿/第三章_研究对象数据证据与总体框架事实稿_20261017_证据索引.json',
         body_sha='f537a66ce07ac2fd8fda50155c8b393288aaa8edece01fa7cf2a21e613deb209',
         index_sha='c3409b17854416de29bc045a6e9cf139cee04d36dac9a03fca3bb53d89d6e295'),
    dict(chapter=4, body='outputs/论文初稿/第四章_场景级特征构建与无监督聚类方法事实稿_20261024.md',
         index='outputs/论文初稿/第四章_场景级特征构建与无监督聚类方法事实稿_20261024_证据索引.json',
         body_sha='58d0fad6e121b88ebe1f946dc4f7172cbfc1611d58ed9657f4e14dc15851c6df',
         index_sha='1a940aec8ac73d7d84b2de2b0b5fcb9f23666ce3426617b903d953bf9b7d8e59'),
    dict(chapter=5, body='outputs/论文初稿/第五章_关键场景综合评分方法事实稿_20261024.md',
         index='outputs/论文初稿/第五章_关键场景综合评分方法事实稿_20261024_证据索引.json',
         body_sha='0d5896b21980de4c1842cc0d1599759e85e05b6899f223a48c7b594e4629fc06',
         index_sha='8c1ec7a2b33d3061b41301a5cc7f72bf037516e92e230646a308efe6cf3f90a2'),
    dict(chapter=6, body='outputs/论文初稿/第六章_开发验证与误差分析事实稿_20261016.md',
         index='outputs/论文初稿/第六章_开发验证与误差分析事实稿_20261016_证据索引.json',
         body_sha='ff4e7f589edda61ab9592de2e07b0804f2276143f3274454e6ed9a360bd776d4',
         index_sha='4e14e158b4b364fe8c26b444f8064995c8653ebeed90c8c8d99ff72c1f6fb3cd'),
]
INTRO = """# 自动驾驶场景聚类方法与开发验证连续阅读版

整理日期：2026-10-27。此文件按第三、四、五、六章顺序收录四份已保存的事实稿，便于连续阅读和定位原件。
各章文字、公式、表格、日期与证据编号均保留原样；不是学校格式稿、作者定稿或新增实验结果。

## 阅读说明

- 各章日期不同，段落中的“当前”“待审”“未完成”等状态只对应原稿所述时点。后续状态请查各章日志和[项目当前入口](../../README.md)，不要把原稿中的历史待办当作已授权运行命令。
- 内部编号仅在所属章节内解释。例如“第四章S03”与其他章的来源编号不能混用；文中的数字文献编号也没有合并成全书统一书目。
- 原稿出现的来源/正文链接仍指向原来的独立文件，便于对照；本阅读版没有覆盖它们，也未刷新原索引。
- 最新候选的正式全量提取、模型与排名、独立评价及作者/学校审定仍按[暂挂清单](../../logs/deferred_decisions_20261015.md)处理，不因合并阅读而获得批准。

## 章节导航

"""


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def record(root, path):
    raw = (root / path).read_bytes()
    return dict(path=Path(path).as_posix(), bytes=len(raw), sha256=digest(raw))


def load_chapters(root, specs=CHAPTERS):
    root = Path(root)
    if [spec['chapter'] for spec in specs] != [3, 4, 5, 6]:
        raise ValueError('Expected chapters 3,4,5,6 once in order')
    chapters = []
    for spec in specs:
        index_raw = (root / spec['index']).read_bytes()
        if digest(index_raw) != spec['index_sha']:
            raise ValueError('Original index hash mismatch')
        raw = (root / spec['body']).read_bytes()
        if digest(raw) != spec['body_sha']:
            raise ValueError('Original body hash mismatch')
        document = json.loads(index_raw.decode('utf8'))['document']
        source_name = document['path'].replace('\\', '/').rsplit('/', 1)[-1]
        if (document['sha256'] != digest(raw) or document['bytes'] != len(raw)
                or source_name != Path(spec['body']).name):
            raise ValueError('Original document binding mismatch')
        raw.decode('utf8')
        chapters.append(dict(chapter=spec['chapter'], raw=raw,
            body_record=record(root, spec['body']), index_record=record(root, spec['index'])))
    return chapters


def render_reader(chapters):
    intro = INTRO
    for item in chapters:
        intro += f"- [第{item['chapter']}章](#chapter-{item['chapter']})，"
        intro += f"[原稿]({Path(item['body_record']['path']).name})，"
        intro += f"[原索引]({Path(item['index_record']['path']).name})。\n"
    parts = [(intro + '\n').encode('utf8')]
    for item in chapters:
        number = item['chapter']
        parts.append((f'<a id="chapter-{number}"></a>\n\n'
            f'本节开始收录第{number}章原文，内部来源编号仅适用于本章。\n\n'
            f'<!-- CHAPTER_{number}_BEGIN -->\n').encode('utf8'))
        parts.append(item['raw'])
        parts.append(f'\n<!-- CHAPTER_{number}_END -->\n\n'.encode('ascii'))
    return b''.join(parts)


def build(root, specs=CHAPTERS):
    root = Path(root)
    output = root / OUTPUT_DIR / READER_NAME
    manifest_path = root / OUTPUT_DIR / MANIFEST_NAME
    if output.exists() or manifest_path.exists():
        raise FileExistsError('Reader outputs already exist; use original-hash check-only')
    chapters = load_chapters(root, specs)
    raw = render_reader(chapters)
    implementation = [record(root, path) for path in IMPLEMENTATION]
    manifest = dict(stage='verbatim_chapter_reader_not_formal_manuscript',
        task_date='2026-10-27', created_at_utc=datetime.now(timezone.utc).isoformat(),
        output=dict(path=(OUTPUT_DIR / READER_NAME).as_posix(), bytes=len(raw), sha256=digest(raw)),
        inputs=[dict(chapter=c['chapter'], body=c['body_record'], index=c['index_record'])
                for c in chapters],
        implementation=implementation, original_chapter_bytes_preserved=True,
        global_reference_renumbering=False, real_extraction_fit_score_evaluation=False,
        author_or_school_accepted=False,
        limitation='Packaging and source integrity only; not prose/formula/semantic or visual DOCX acceptance')
    with output.open('xb') as stream:
        stream.write(raw)
    with manifest_path.open('x', encoding='utf8', newline='\n') as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    return manifest


def check(root, expected_manifest_sha, specs=CHAPTERS):
    root = Path(root)
    if not isinstance(expected_manifest_sha, str) or not re.fullmatch('[0-9a-f]{64}', expected_manifest_sha):
        raise ValueError('Caller must supply original manifest SHA256')
    path = root / OUTPUT_DIR / MANIFEST_NAME
    manifest_raw = path.read_bytes()
    if digest(manifest_raw) != expected_manifest_sha:
        raise ValueError('Wrong original manifest SHA256')
    manifest = json.loads(manifest_raw.decode('utf8'))
    chapters = load_chapters(root, specs)
    expected_inputs = [dict(chapter=c['chapter'], body=c['body_record'], index=c['index_record'])
                       for c in chapters]
    if manifest['inputs'] != expected_inputs:
        raise ValueError('Reader input bindings differ from original chapters')
    for item in manifest['implementation']:
        if record(root, item['path']) != item:
            raise ValueError('Reader implementation binding mismatch')
    actual = record(root, OUTPUT_DIR / READER_NAME)
    if actual != manifest['output'] or (root / actual['path']).read_bytes() != render_reader(chapters):
        raise ValueError('Reader bytes differ from verbatim assembly')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--build', action='store_true')
    action.add_argument('--check-only', action='store_true')
    parser.add_argument('--expected-manifest-sha')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = build(root) if args.build else check(root, args.expected_manifest_sha)
    print(json.dumps(dict(stage=result['stage'], chapter_count=len(result['inputs']),
        output=result['output'], check_only=args.check_only), ensure_ascii=False))


if __name__ == '__main__':
    main()
