"""Offline safety tests for the dated camera recovery operation."""

import io
import json
from pathlib import Path
import shutil
import tarfile
import unittest
import uuid
from unittest.mock import patch

from PIL import Image

try:
    from logs import recover_camera_media_20261011 as recovery
except ImportError:
    recovery = None


class RecoverySafetyTest(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(recovery, 'Recovery recipe is not implemented')

    def test_range_start_total_length_and_etag_must_match(self):
        package = {'bytes': 100, 'etag': '"object"'}
        headers = {'Content-Length': '60', 'Content-Range': 'bytes 40-99/100', 'ETag': '"object"'}
        recovery.validate_response(206, headers, 40, package)
        for key, value in [('Content-Range', 'bytes 0-99/100'),
                           ('Content-Length', '59'), ('ETag', '"changed"')]:
            with self.assertRaises(ValueError):
                recovery.validate_response(206, dict(headers, **{key: value}), 40, package)
        with self.assertRaises(ValueError):
            recovery.validate_response(200, headers, 40, package)

    def test_fresh_download_requires_exact_object(self):
        recovery.validate_response(200, {'Content-Length': '100', 'ETag': '"object"'},
                                   0, {'bytes': 100, 'etag': '"object"'})
        with self.assertRaises(ValueError):
            recovery.validate_response(206, {'Content-Length': '100', 'ETag': '"object"'},
                                       0, {'bytes': 100, 'etag': '"object"'})

    def test_unsafe_or_non_camera_names_rejected(self):
        self.assertEqual(recovery.camera_name('./samples/CAM_FRONT/frame.jpg'),
                         'samples/CAM_FRONT/frame.jpg')
        for name in ('../samples/CAM_FRONT/a.jpg', '/samples/CAM_FRONT/a.jpg',
                     'samples/CAM_FRONT/../a.jpg', 'samples\\CAM_FRONT\\a.jpg',
                     'C:/samples/CAM_FRONT/a.jpg', 'samples/CAM_FRONT/a.jpg:stream',
                     'samples/LIDAR_TOP/a.jpg', 'samples/CAM_FRONT/a.bin'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                recovery.camera_name(name)

    def test_jpeg_dimensions_and_full_decoding_required(self):
        stream = io.BytesIO()
        Image.new('RGB', (12, 8)).save(stream, format='JPEG')
        recovery.validate_image(io.BytesIO(stream.getvalue()), {'width': 12, 'height': 8})
        with self.assertRaises(ValueError):
            recovery.validate_image(io.BytesIO(stream.getvalue()), {'width': 8, 'height': 12})
        with self.assertRaises(Exception):
            recovery.validate_image(io.BytesIO(b'invalid'), {'width': 12, 'height': 8})

    def test_space_reserve_is_enforced(self):
        recovery.require_space(300, 100, reserve=100)
        with self.assertRaises(OSError):
            recovery.require_space(199, 100, reserve=100)

    def test_no_overwrite_and_archive_links_rejected(self):
        folder = Path(__file__).resolve().parent / ('media_safety_test_' + uuid.uuid4().hex)
        folder.mkdir(mode=0o777)
        try:
            destination = folder / 'data'
            staging = folder / 'staging'
            destination.mkdir()
            staging.mkdir()
            row = {'filename': 'samples/CAM_FRONT/a.jpg', 'width': 12, 'height': 8}
            target = destination / row['filename']
            target.parent.mkdir(parents=True)
            target.write_bytes(b'preserve-existing')
            member = tarfile.TarInfo(row['filename'])
            member.size = 100
            self.assertEqual(recovery.restore_member(member, io.BytesIO(b'invalid'), row,
                                                     destination, staging), 'already_present')
            self.assertEqual(target.read_bytes(), b'preserve-existing')
            member.type = tarfile.SYMTYPE
            with self.assertRaises(ValueError):
                recovery.restore_member(member, io.BytesIO(), row, destination, staging)
        finally:
            folder.resolve().relative_to(Path(__file__).resolve().parent)
            shutil.rmtree(folder)

    def test_validated_image_is_published_only_when_absent(self):
        folder = Path(__file__).resolve().parent / ('media_safety_test_' + uuid.uuid4().hex)
        folder.mkdir(mode=0o777)
        try:
            destination, staging = folder / 'data', folder / 'staging'
            destination.mkdir()
            staging.mkdir()
            row = {'filename': 'samples/CAM_FRONT/a.jpg', 'width': 12, 'height': 8}
            data = io.BytesIO()
            Image.new('RGB', (12, 8)).save(data, format='JPEG')
            member = tarfile.TarInfo(row['filename'])
            member.size = len(data.getvalue())
            result = recovery.restore_member(member, io.BytesIO(data.getvalue()), row, destination, staging)
            self.assertEqual(result, 'restored')
            self.assertEqual((destination / row['filename']).read_bytes(), data.getvalue())
            self.assertEqual(list(staging.iterdir()), [])
        finally:
            folder.resolve().relative_to(Path(__file__).resolve().parent)
            shutil.rmtree(folder)

    def test_failed_decode_never_creates_dataset_file(self):
        folder = Path(__file__).resolve().parent / ('media_safety_test_' + uuid.uuid4().hex)
        folder.mkdir(mode=0o777)
        try:
            destination, staging = folder / 'data', folder / 'staging'
            destination.mkdir()
            staging.mkdir()
            row = {'filename': 'samples/CAM_FRONT/a.jpg', 'width': 12, 'height': 8}
            member = tarfile.TarInfo(row['filename'])
            member.size = 7
            with self.assertRaises(Exception):
                recovery.restore_member(member, io.BytesIO(b'invalid'), row, destination, staging)
            self.assertFalse((destination / row['filename']).exists())
        finally:
            folder.resolve().relative_to(Path(__file__).resolve().parent)
            shutil.rmtree(folder)

    def test_empty_partial_is_reusable(self):
        self.assertTrue(callable(getattr(recovery, 'partial_mode', None)), 'Missing empty-partial recovery')
        self.assertEqual(recovery.partial_mode(True), 'ab')
        self.assertEqual(recovery.partial_mode(False), 'xb')

    def test_malformed_tar_after_valid_member_fails_before_publication(self):
        self.assertTrue(callable(getattr(recovery, 'verify_archive', None)), 'Missing strict tar verification')
        import gzip
        folder = Path(__file__).resolve().parent / ('media_safety_test_' + uuid.uuid4().hex)
        folder.mkdir(mode=0o777)
        try:
            archive = folder / 'bad.tgz'
            member = tarfile.TarInfo('samples/CAM_FRONT/a.jpg')
            member.size = 7
            with gzip.open(archive, 'wb') as stream:
                stream.write(member.tobuf() + b'invalid' + b'\0' * 505 + b'X' * 512 + b'\0' * 1024)
            with self.assertRaises((ValueError, tarfile.TarError)):
                recovery.verify_archive(archive)
        finally:
            folder.resolve().relative_to(Path(__file__).resolve().parent)
            shutil.rmtree(folder)

    def test_archive_without_receipt_is_reconciled(self):
        self.assertTrue(callable(getattr(recovery, 'reconcile_archive', None)), 'Missing receipt reconciliation')
        folder = Path(__file__).resolve().parent / ('media_safety_test_' + uuid.uuid4().hex)
        folder.mkdir(mode=0o777)
        try:
            archive = folder / 'good.tgz'
            with tarfile.open(archive, 'w:gz') as stream:
                member = tarfile.TarInfo('samples/CAM_FRONT/a.jpg')
                member.size = 7
                stream.addfile(member, io.BytesIO(b'invalid'))
            receipt = folder / 'good.download.json'
            package = {'bytes': archive.stat().st_size, 'etag': '"object"'}
            result = recovery.reconcile_archive(archive, receipt, package)
            self.assertEqual(result['archive'], recovery.file_record(archive))
            self.assertTrue(json.loads(receipt.read_text())['receipt_reconciled'])
        finally:
            folder.resolve().relative_to(Path(__file__).resolve().parent)
            shutil.rmtree(folder)

    def test_publication_requires_prior_durable_intent(self):
        import inspect
        self.assertIn('before_publish', inspect.signature(recovery.restore_member).parameters)
        folder = Path(__file__).resolve().parent / ('media_safety_test_' + uuid.uuid4().hex)
        folder.mkdir(mode=0o777)
        try:
            destination, staging = folder / 'data', folder / 'staging'
            destination.mkdir()
            staging.mkdir()
            row = {'filename': 'samples/CAM_FRONT/a.jpg', 'width': 12, 'height': 8}
            data = io.BytesIO()
            Image.new('RGB', (12, 8)).save(data, format='JPEG')
            member = tarfile.TarInfo(row['filename'])
            member.size = len(data.getvalue())
            target = destination / row['filename']
            def interrupted_intent(record):
                self.assertFalse(target.exists())
                self.assertEqual(record['path'], str(target))
                raise OSError('simulated journal failure')
            with self.assertRaises(OSError):
                recovery.restore_member(member, io.BytesIO(data.getvalue()), row,
                                        destination, staging, before_publish=interrupted_intent)
            self.assertFalse(target.exists())
        finally:
            folder.resolve().relative_to(Path(__file__).resolve().parent)
            shutil.rmtree(folder)

    def test_interrupted_receipt_serialization_never_publishes_partial_json(self):
        self.assertTrue(callable(getattr(recovery, 'save_receipt', None)), 'Missing atomic receipt publication')
        folder = Path(__file__).resolve().parent / ('media_safety_test_' + uuid.uuid4().hex)
        folder.mkdir(mode=0o777)
        try:
            receipt = folder / 'download.json'
            def interrupted(value, stream, **kwargs):
                stream.write('{')
                raise OSError('interrupted receipt serialization')
            with patch.object(recovery.json, 'dump', side_effect=interrupted), self.assertRaises(OSError):
                recovery.save_receipt(receipt, {'valid': True})
            self.assertFalse(receipt.exists())
            recovery.save_receipt(receipt, {'valid': True})
            self.assertEqual(json.loads(receipt.read_text()), {'valid': True})
        finally:
            folder.resolve().relative_to(Path(__file__).resolve().parent)
            shutil.rmtree(folder)

    def test_bounded_range_request_requires_exact_end_and_length(self):
        import inspect
        self.assertIn('range_end', inspect.signature(recovery.validate_response).parameters)
        package = {'bytes': 100, 'etag': '"object"'}
        headers = {'Content-Length': '20', 'Content-Range': 'bytes 40-59/100', 'ETag': '"object"'}
        recovery.validate_response(206, headers, 40, package, range_end=59)
        with self.assertRaises(ValueError):
            recovery.validate_response(206, dict(headers, **{'Content-Range': 'bytes 40-60/100'}),
                                       40, package, range_end=59)

    def test_first_bounded_request_is_206_not_200(self):
        import inspect
        self.assertIn('range_end', inspect.signature(recovery.validate_response).parameters)
        package = {'bytes': 100, 'etag': '"object"'}
        headers = {'Content-Length': '20', 'Content-Range': 'bytes 0-19/100', 'ETag': '"object"'}
        recovery.validate_response(206, headers, 0, package, range_end=19)
        with self.assertRaises(ValueError):
            recovery.validate_response(200, headers, 0, package, range_end=19)

    def test_multiple_bounded_chunks_complete_with_empty_partial(self):
        self.assertTrue(hasattr(recovery, 'TRANSFER_CHUNK'), 'Missing bounded transfer loop')
        folder = Path(__file__).resolve().parent / ('media_safety_test_' + uuid.uuid4().hex)
        folder.mkdir(mode=0o777)
        try:
            payload = io.BytesIO()
            with tarfile.open(fileobj=payload, mode='w:gz') as stream:
                member = tarfile.TarInfo('samples/CAM_FRONT/a.jpg')
                member.size = 7
                stream.addfile(member, io.BytesIO(b'invalid'))
            data = payload.getvalue()
            package = {'part': 3, 'bytes': len(data), 'etag': '"object"', 'url': 'https://example.invalid/part.tgz'}
            cache = folder / 'packages'
            cache.mkdir()
            (cache / 'part.tgz.partial').write_bytes(b'')
            requests = []
            def response(request, **kwargs):
                begin, end = map(int, request.get_header('Range').removeprefix('bytes=').split('-'))
                requests.append((begin, end))
                value = io.BytesIO(data[begin:end + 1])
                value.status = 206
                value.headers = {'Content-Length': str(end - begin + 1),
                    'Content-Range': f'bytes {begin}-{end}/{len(data)}', 'ETag': package['etag']}
                return value
            with patch.object(recovery, 'BATCH', folder), patch.object(recovery, 'TRANSFER_CHUNK', 32), \
                    patch.object(recovery, 'head', return_value=package), patch.object(recovery, 'urlopen', side_effect=response):
                archive, receipt = recovery.download(package, lambda **changes: None)
            self.assertEqual(archive.read_bytes(), data)
            self.assertGreater(len(requests), 1)
            self.assertEqual(requests[0][0], 0)
            self.assertEqual(requests[-1][1], len(data) - 1)
            self.assertTrue(receipt['tar_integrity_verified'])
        finally:
            folder.resolve().relative_to(Path(__file__).resolve().parent)
            shutil.rmtree(folder)


if __name__ == '__main__':
    unittest.main()
