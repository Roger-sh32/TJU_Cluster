"""Export the four preselected, media-available development supplements."""

import json
from pathlib import Path
import sys

import build_semantic_review_pack_20261001 as exporter


def main():
    root = Path(__file__).resolve().parents[1]
    selection_path = root / 'HDBSCAN/tables/semantic_review_supplements_20261001.json'
    selection = json.loads(selection_path.read_text(encoding='utf-8'))
    names = tuple(r['supplement'] for r in selection['supplements'] if r['supplement'])
    if len(names) != 4 or len(set(names)) != 4:
        raise ValueError('Four unique preselected supplements required')
    exporter.NAMES = names
    exporter.DEST = root / 'exports/semantic_review_supplements_20261001'
    exporter.REPORT = root / 'HDBSCAN/tables/semantic_review_supplement_media_20261001.json'
    protocol_path = root / 'HDBSCAN/tables/semantic_review_supplement_export_protocol_20261001.json'
    if protocol_path.exists() or exporter.DEST.exists() or exporter.REPORT.exists():
        raise FileExistsError('Dated supplement outputs already exist')
    protocol = {'stage': 'development_supplement_export_protocol', 'command': [sys.executable, *sys.argv],
                'selection': exporter.record(selection_path), 'script': exporter.record(__file__),
                'export_recipe': exporter.record(exporter.__file__), 'names': list(names),
                'output_report': str(exporter.REPORT), 'output_directory': str(exporter.DEST)}
    with protocol_path.open('x', encoding='utf-8') as stream:
        json.dump(protocol, stream, ensure_ascii=False, indent=2)
    exporter.main()


if __name__ == '__main__':
    main()
