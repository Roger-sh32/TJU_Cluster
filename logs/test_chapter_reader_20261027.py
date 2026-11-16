import hashlib
import importlib
import json
from pathlib import Path
import shutil
import unittest
import uuid


def sha(data):
    return hashlib.sha256(data).hexdigest()


class ChapterReaderTests(unittest.TestCase):
    def setUp(self):
        recipe = Path(__file__).with_name('build_chapter_reader_20261027.py')
        self.assertTrue(recipe.is_file(), 'Reader recipe not implemented')
        self.api = importlib.import_module('logs.build_chapter_reader_20261027')
        # Inherit workspace permissions, avoiding Conda's restrictive temp ACL.
        self.root = Path(__file__).resolve().parent / ('SYN_chapter_reader_' + uuid.uuid4().hex)
        self.root.mkdir()
        self.addCleanup(self.clean_workspace)
        (self.root / 'logs').mkdir()
        for path in (recipe, Path(__file__)):
            shutil.copyfile(path, self.root / 'logs' / path.name)
        self.folder = self.root / self.api.OUTPUT_DIR
        self.folder.mkdir(parents=True)
        self.specs = []
        for chapter in (3, 4, 5, 6):
            raw = f'# SYN chapter {chapter}\r\n\r\nS01 is local to this chapter.\r\n'.encode()
            body = self.folder / f'SYN_{chapter}.md'
            body.write_bytes(raw)
            index = self.folder / f'SYN_{chapter}.json'
            index.write_text(json.dumps({'document': {'path': str(body),
                'bytes': len(raw), 'sha256': sha(raw)}}), encoding='utf8')
            self.specs.append(dict(chapter=chapter, body=body.relative_to(self.root).as_posix(),
                index=index.relative_to(self.root).as_posix(), body_sha=sha(raw),
                index_sha=sha(index.read_bytes())))

    def clean_workspace(self):
        target = self.root.resolve()
        if target.parent != Path(__file__).resolve().parent or not target.name.startswith('SYN_chapter_reader_'):
            raise RuntimeError('SYN cleanup escaped its workspace')
        shutil.rmtree(target)

    def test_original_bytes_and_chapter_order_are_preserved(self):
        chapters = self.api.load_chapters(self.root, self.specs)
        output = self.api.render_reader(chapters)
        positions = []
        for chapter in chapters:
            raw = chapter['raw']
            self.assertEqual(output.count(raw), 1)
            positions.append(output.index(raw))
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(output.count(b'S01 is local to this chapter.'), 4)

    def test_bad_index_digest_is_rejected_before_json_parse(self):
        spec = self.specs[0]
        (self.root / spec['index']).write_bytes(b'not json')
        with self.assertRaisesRegex(ValueError, 'index hash'):
            self.api.load_chapters(self.root, self.specs)

    def test_index_must_bind_the_actual_body(self):
        spec = self.specs[0]
        path = self.root / spec['index']
        value = json.loads(path.read_text(encoding='utf8'))
        value['document']['sha256'] = '0' * 64
        path.write_text(json.dumps(value), encoding='utf8')
        spec['index_sha'] = sha(path.read_bytes())
        with self.assertRaisesRegex(ValueError, 'document binding'):
            self.api.load_chapters(self.root, self.specs)

    def test_build_is_exclusive_and_does_not_overwrite(self):
        self.api.build(self.root, self.specs)
        path = self.folder / self.api.READER_NAME
        before = path.read_bytes()
        with self.assertRaises(FileExistsError):
            self.api.build(self.root, self.specs)
        self.assertEqual(path.read_bytes(), before)

    def test_check_requires_the_original_manifest_digest(self):
        self.api.build(self.root, self.specs)
        with self.assertRaisesRegex(ValueError, 'original manifest'):
            self.api.check(self.root, None, self.specs)
        with self.assertRaisesRegex(ValueError, 'original manifest'):
            self.api.check(self.root, '0' * 64, self.specs)

    def test_check_rejects_output_tampering(self):
        self.api.build(self.root, self.specs)
        manifest = self.folder / self.api.MANIFEST_NAME
        self.api.check(self.root, sha(manifest.read_bytes()), self.specs)
        output = self.folder / self.api.READER_NAME
        output.write_bytes(output.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, '[Rr]eader bytes'):
            self.api.check(self.root, sha(manifest.read_bytes()), self.specs)


if __name__ == '__main__':
    unittest.main()
