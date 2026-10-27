"""Dated, identity-only camera recovery. No labels, fitting, or existing-file overwrite."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import ssl
import sys
import tarfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import uuid

import certifi
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from logs.evaluation_media_audit_20260926 import file_record, records
from HDBSCAN.scripts.experiment_partition import load_partition

DATA = ROOT / 'nuScenes'
BATCH = ROOT / 'exports/media_recovery_20261011'
PROTOCOL = BATCH / 'protocol.json'
LAUNCH_PROTOCOL = BATCH / 'launch_protocol.json'
TRANSFER_PROTOCOL = BATCH / 'transfer_protocol_v2.json'
TRANSFER_CHUNK = 64 * 2**20
FILES = BATCH / 'camera_files.jsonl'
STATUS = ROOT / 'logs/media_recovery_20261011_status.json'
REPORT = ROOT / 'HDBSCAN/tables/media_recovery_audit_20261011.json'
DEVELOPMENT = ['scene-0002', 'scene-0093', 'scene-0102', 'scene-0453',
               'scene-0552', 'scene-0669', 'scene-0815', 'scene-0816']
CHANNELS = {'CAM_FRONT', 'CAM_FRONT_LEFT', 'CAM_FRONT_RIGHT',
            'CAM_BACK', 'CAM_BACK_LEFT', 'CAM_BACK_RIGHT'}
RESERVE = 30 * 2**30
CONTEXT = ssl.create_default_context(cafile=certifi.where())


def now():
    return datetime.now(timezone.utc).isoformat()


def save_json(path, value, exclusive=True):
    if exclusive:
        with path.open('x', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
    else:
        temporary = path.with_name(path.name + '.tmp')
        with temporary.open('w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        os.replace(temporary, path)


def save_receipt(path, value):
    temporary = path.with_name(path.name + '.writing-' + uuid.uuid4().hex)
    try:
        with temporary.open('x', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        if temporary.exists():
            temporary.resolve().relative_to(path.parent.resolve())
            temporary.unlink()


def camera_name(name):
    while name.startswith('./'):
        name = name[2:]
    parts = name.split('/')
    if ('\\' in name or ':' in name or '\x00' in name or len(parts) != 3
            or any(p in ('', '.', '..') for p in parts)
            or parts[0] not in {'samples', 'sweeps'} or parts[1] not in CHANNELS
            or not re.fullmatch(r'[A-Za-z0-9_+.\-]+\.jpg', parts[2])
            or parts[2].split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL'}):
        raise ValueError('Unsafe/non-camera filename: ' + name)
    return '/'.join(parts)


def target_path(root, name):
    relative = camera_name(name)
    target = root / relative
    target.resolve().relative_to(root.resolve())
    if target.is_symlink():
        raise ValueError('Refusing symlink target: ' + relative)
    return target


def require_space(free, required, reserve=RESERVE):
    if required < 0 or free < required + reserve:
        raise OSError('Insufficient disk space including safety reserve')


def validate_response(status, headers, offset, package, range_end=None):
    end = package['bytes'] - 1 if range_end is None else range_end
    if not 0 <= offset <= end < package['bytes']:
        raise ValueError('Invalid requested byte interval')
    remaining = end - offset + 1
    if (headers.get('ETag') != package['etag']
            or int(headers.get('Content-Length', '-1')) != remaining
            or headers.get('Content-Encoding') not in (None, 'identity')):
        raise ValueError('Download object identity/length/encoding mismatch')
    if offset or range_end is not None:
        expected = f"bytes {offset}-{end}/{package['bytes']}"
        if status != 206 or headers.get('Content-Range') != expected:
            raise ValueError('Unsafe resume response; never append a full HTTP200 body')
    elif status != 200:
        raise ValueError('Unexpected fresh-download HTTP response')


def validate_image(source, row):
    with Image.open(source) as picture:
        if picture.format != 'JPEG' or picture.size != (row['width'], row['height']):
            raise ValueError('Unexpected image format/dimensions')
        picture.load()


def restore_member(member, source, row, root, staging, before_publish=None):
    if not member.isfile() or member.issym() or member.islnk():
        raise ValueError('Refusing archive link/device/nonregular file')
    if camera_name(member.name) != row['filename'] or not 0 < member.size <= 16 * 2**20:
        raise ValueError('Unexpected archive member identity/size')
    target = target_path(root, row['filename'])
    if target.exists():
        if not target.is_file():
            raise ValueError('Existing non-file target')
        return 'already_present' if target.stat().st_size else 'existing_empty_blocked'
    require_space(shutil.disk_usage(root).free, member.size)
    temporary = staging / (uuid.uuid4().hex + '.jpg')
    try:
        with temporary.open('xb') as stream:
            shutil.copyfileobj(source, stream, length=1024 * 1024)
        if temporary.stat().st_size != member.size:
            raise ValueError('Truncated archive image')
        validate_image(temporary, row)
        target.parent.mkdir(parents=True, exist_ok=True)
        target = target_path(root, row['filename'])
        if before_publish is not None:
            record = file_record(temporary)
            record['path'] = str(target)
            before_publish(record)
        try:
            # NTFS hard-link publication is atomic and fails if the destination exists.
            os.link(temporary, target)
        except FileExistsError:
            return 'already_present'
        return 'restored'
    finally:
        if temporary.exists():
            temporary.resolve().relative_to(staging.resolve())
            temporary.unlink()


def head(package):
    with urlopen(Request(package['url'], method='HEAD'), context=CONTEXT, timeout=40) as response:
        result = dict(package, bytes=int(response.headers['Content-Length']),
                      etag=response.headers.get('ETag'), accept_ranges=response.headers.get('Accept-Ranges'))
    if not result['etag'] or result['accept_ranges'] != 'bytes':
        raise ValueError('Official object lacks resume identity/range support')
    return result


def verify_records(bound):
    for record in bound:
        if file_record(Path(record['path']))['sha256'] != record['sha256']:
            raise ValueError('Frozen recovery input changed: ' + record['path'])


def partial_mode(exists):
    return 'ab' if exists else 'xb'


def verify_archive(archive):
    record = file_record(archive)
    headers = 0
    # tarfile can treat a corrupt subsequent header as EOF. Check every physical
    # header and the two-block terminator before its semantic member traversal.
    with gzip.open(archive, 'rb') as stream:
        while True:
            block = stream.read(512)
            if len(block) != 512:
                raise ValueError('Tar missing complete terminator/header')
            if block == b'\0' * 512:
                trailing = 0
                for tail in iter(lambda: stream.read(4 * 2**20), b''):
                    if any(tail):
                        raise ValueError('Nonzero data after tar terminator')
                    trailing += len(tail)
                if trailing < 512 or trailing % 512:
                    raise ValueError('Incomplete tar terminator/padding')
                break
            member = tarfile.TarInfo.frombuf(block, 'utf-8', 'surrogateescape')
            if member.size < 0:
                raise ValueError('Negative tar payload size')
            remaining = (member.size + 511) // 512 * 512
            while remaining:
                payload = stream.read(min(remaining, 4 * 2**20))
                if not payload:
                    raise ValueError('Truncated tar payload')
                remaining -= len(payload)
            headers += 1
    if not headers:
        raise ValueError('Empty camera archive')
    with tarfile.open(archive, mode='r|gz') as stream:
        for member in stream:
            parts = PurePosixPath(member.name).parts
            if (member.name.startswith('/') or '\\' in member.name or ':' in member.name
                    or '..' in parts or member.issym() or member.islnk()
                    or not (member.isfile() or member.isdir())):
                raise ValueError('Unsafe tar member before publication: ' + member.name)
    return {'archive': record, 'gzip_crc_complete': True, 'tar_integrity_verified': True}


def reconcile_archive(archive, receipt, package):
    if archive.stat().st_size != package['bytes']:
        raise ValueError('Cached archive length mismatch')
    verified = verify_archive(archive)
    result = dict(verified, verified_at_utc=now(), package=package, receipt_reconciled=True)
    save_receipt(receipt, result)
    return result


def prepare():
    if BATCH.exists() or REPORT.exists() or STATUS.exists():
        raise FileExistsError('Keep previous recovery batches; do not overwrite')
    partition = load_partition()
    evaluation = [r for r in partition['rows'] if r['split'] == 'evaluation']
    development = [partition['by_name'][name] for name in DEVELOPMENT]
    if len(evaluation) != 150 or any(r['split'] != 'development' for r in development):
        raise ValueError('Frozen recovery scope mismatch')
    meta = DATA / 'v1.0-trainval'
    metadata_names = ['scene.json', 'sensor.json', 'calibrated_sensor.json', 'sample.json', 'sample_data.json']
    bound = [file_record(meta / name) for name in metadata_names]
    old = json.loads((ROOT / 'exports/media_recovery_20260926/recovery_inventory.json').read_text())
    verify_records([old['partition'], *old['metadata'], old['missing_file_list']])
    packages = []
    for part in range(3, 11):
        package = head({'part': part, 'url': 'https://motional-nuscenes.s3.amazonaws.com/public/v1.0/'
                        + f'v1.0-trainval{part:02}_blobs_camera.tgz'})
        packages.append(package)
        print(f"HEAD {part:02}: {package['bytes']} bytes", flush=True)
    selected = {r['scene_token']: dict(r, role='evaluation') for r in evaluation}
    selected.update({r['scene_token']: dict(r, role='development') for r in development})
    sensors = {r['token']: r for r in json.loads((meta / 'sensor.json').read_text())}
    calibrations = {r['token']: sensors[r['sensor_token']]
                    for r in json.loads((meta / 'calibrated_sensor.json').read_text())}
    samples = {r['token']: r for r in json.loads((meta / 'sample.json').read_text())
               if r['scene_token'] in selected}
    scene_counts = {r['token']: r['nbr_samples'] for r in json.loads((meta / 'scene.json').read_text())}
    BATCH.mkdir(parents=True)
    counts, key_counts, seen = Counter(), Counter(), set()
    with FILES.open('x', encoding='utf-8') as stream:
        for index, row in enumerate(records(meta / 'sample_data.json'), 1):
            sample = samples.get(row['sample_token'])
            if sample is None:
                continue
            sensor = calibrations[row['calibrated_sensor_token']]
            identity = selected[sample['scene_token']]
            if sensor['modality'] != 'camera' or (identity['role'] == 'development' and sensor['channel'] != 'CAM_FRONT'):
                continue
            name = camera_name(row['filename'])
            if name in seen:
                raise ValueError('Duplicate selected filename')
            seen.add(name)
            path = target_path(DATA, name)
            if path.exists() and not path.is_file():
                raise ValueError('Non-file source path')
            present = path.is_file() and path.stat().st_size > 0
            kind = 'keyframe' if row['is_key_frame'] else 'associated_nonkeyframe'
            counts[f"{identity['role']}_{kind}_{'present' if present else 'missing_or_empty'}"] += 1
            if row['is_key_frame']:
                key_counts[sample['scene_token'], sensor['channel']] += 1
            stream.write(json.dumps({'filename': name, 'scene_token': sample['scene_token'],
                'scene_name': identity['scene_name'], 'role': identity['role'], 'channel': sensor['channel'],
                'sample_data_token': row['token'], 'sample_token': row['sample_token'],
                'is_key_frame': row['is_key_frame'], 'timestamp': row['timestamp'],
                'width': row['width'], 'height': row['height'], 'present_before': present}) + '\n')
    for token, identity in selected.items():
        for channel in CHANNELS if identity['role'] == 'evaluation' else {'CAM_FRONT'}:
            if key_counts[token, channel] != scene_counts[token]:
                raise ValueError('Camera keyframe metadata count mismatch')
    bound.extend([partition['file'], file_record(Path(__file__).resolve()),
                  file_record(ROOT / 'logs/test_recover_camera_media_20261011.py'),
                  file_record(ROOT / 'logs/evaluation_media_audit_20260926.py'), file_record(FILES)])
    protocol = {'created_at_utc': now(), 'authorization': 'User approved resuming official camera recovery on 2026-10-11.',
        'scope': 'Media identity/integrity only; no evaluation semantics or labels',
        'python': sys.executable, 'command': [sys.executable, *sys.argv], 'bound_records': bound,
        'candidate_packages': packages, 'package_total_bytes_upper_bound': sum(p['bytes'] for p in packages),
        'selected_scenes': list(selected.values()), 'counts_before': dict(counts),
        'selected_file_count': len(seen), 'free_disk_bytes_before': shutil.disk_usage(ROOT).free,
        'reserve_bytes': RESERVE, 'cache_policy': 'Keep downloaded packages; no automatic deletion',
        'overwrite_existing': False, 'restore_only_frozen_list': True, 'packages_are_proven_minimal': False,
        'limits': ['No model/feature/split changes.', 'ETag is object identity, not assumed MD5.',
                   'Associated nonkeyframes follow metadata sample association, not exact playback interval.']}
    save_json(PROTOCOL, protocol)
    print(json.dumps({'protocol': file_record(PROTOCOL), 'counts': dict(counts),
                      'selected_file_count': len(seen)}, ensure_ascii=False), flush=True)


def freeze_launch():
    if LAUNCH_PROTOCOL.exists() or STATUS.exists() or (BATCH / 'packages').exists():
        raise FileExistsError('Launch freeze must precede downloads; never rewrite it')
    protocol = json.loads(PROTOCOL.read_text(encoding='utf-8'))
    changed_paths = {str(Path(__file__).resolve()), str(ROOT / 'logs/test_recover_camera_media_20261011.py')}
    bound, snapshots = [], []
    for record in protocol['bound_records']:
        path = Path(record['path'])
        if record['path'] in changed_paths:
            snapshot = file_record(BATCH / 'prepared_sources' / path.name)
            if snapshot['sha256'] != record['sha256']:
                raise ValueError('Original preparation source snapshot mismatch')
            snapshots.append(snapshot)
            bound.append(file_record(path))
        else:
            verify_records([record])
            bound.append(record)
    protocol['bound_records'] = bound + snapshots + [file_record(PROTOCOL)]
    protocol['preparation_protocol'] = file_record(PROTOCOL)
    protocol['launch_frozen_at_utc'] = now()
    protocol['launch_amendment'] = 'Independent re-review required atomic receipt publication; original preparation/selection unchanged and source snapshots preserved before patch.'
    protocol['launch_command'] = [sys.executable, str(Path(__file__).resolve()), 'run']
    save_json(LAUNCH_PROTOCOL, protocol)
    print(json.dumps({'launch_protocol': file_record(LAUNCH_PROTOCOL), 'counts_before': protocol['counts_before']}), flush=True)


def active_protocol():
    return TRANSFER_PROTOCOL if TRANSFER_PROTOCOL.exists() else LAUNCH_PROTOCOL


def freeze_transfer():
    if TRANSFER_PROTOCOL.exists() or (BATCH / 'restored_files.jsonl').exists():
        raise FileExistsError('Transfer amendment must precede image publication and is not overwritten')
    protocol = json.loads(LAUNCH_PROTOCOL.read_text(encoding='utf-8'))
    changed = {str(Path(__file__).resolve()), str(ROOT / 'logs/test_recover_camera_media_20261011.py')}
    bound, snapshots = [], []
    for record in protocol['bound_records']:
        path = Path(record['path'])
        if record['path'] in changed:
            snapshot = file_record(BATCH / 'launch_sources_v1' / path.name)
            if snapshot['sha256'] != record['sha256']:
                raise ValueError('Original launch source mismatch')
            snapshots.append(snapshot)
            bound.append(file_record(path))
        else:
            verify_records([record])
            bound.append(record)
    protocol['bound_records'] = bound + snapshots + [file_record(LAUNCH_PROTOCOL)]
    protocol['previous_launch_protocol'] = file_record(LAUNCH_PROTOCOL)
    protocol['transfer_amended_at_utc'] = now()
    protocol['transfer_amendment'] = 'Observed premature EOF of long HTTP response; use exact64MiB Range requests with five retries per chunk, keeping downloaded prefix. No source-data files published yet.'
    protocol['transfer_chunk_bytes'] = TRANSFER_CHUNK
    save_json(TRANSFER_PROTOCOL, protocol)
    print(json.dumps({'transfer_protocol': file_record(TRANSFER_PROTOCOL)}), flush=True)


def download(package, progress):
    current = head(package)
    if current != package:
        raise ValueError('Official object changed since recovery preparation')
    cache = BATCH / 'packages'
    cache.mkdir(exist_ok=True)
    archive = cache / package['url'].rsplit('/', 1)[1]
    partial = archive.with_name(archive.name + '.partial')
    receipt = archive.with_name(archive.name + '.download.json')
    if archive.exists():
        if not receipt.exists():
            return archive, reconcile_archive(archive, receipt, package)
        record = json.loads(receipt.read_text())
        if (record['package'] != package or record['archive'] != file_record(archive)
                or not record.get('tar_integrity_verified')):
            raise ValueError('Existing cached archive differs from verified receipt')
        return archive, record
    while True:
        offset = partial.stat().st_size if partial.exists() else 0
        if offset > package['bytes']:
            raise ValueError('Oversized partial cache')
        if offset == package['bytes']:
            break
        for attempt in range(1, 6):
            offset = partial.stat().st_size if partial.exists() else 0
            end = min(offset + TRANSFER_CHUNK, package['bytes']) - 1
            require_space(shutil.disk_usage(ROOT).free, package['bytes'] - offset)
            headers = {'If-Match': package['etag'], 'Accept-Encoding': 'identity',
                       'Range': f'bytes={offset}-{end}'}
            progress(phase='downloading', part=package['part'], downloaded_bytes=offset,
                     package_bytes=package['bytes'], attempt=attempt, range_end=end)
            try:
                with urlopen(Request(package['url'], headers=headers), context=CONTEXT, timeout=60) as response:
                    validate_response(response.status, response.headers, offset, package, range_end=end)
                    with partial.open(partial_mode(partial.exists())) as stream:
                        last = time.monotonic()
                        while True:
                            block = response.read(2 * 2**20)
                            if not block:
                                break
                            if offset + len(block) > end + 1:
                                raise ValueError('Oversized download response')
                            stream.write(block)
                            offset += len(block)
                            if time.monotonic() - last >= 10:
                                stream.flush()
                                progress(downloaded_bytes=offset)
                                last = time.monotonic()
                    if offset != end + 1:
                        raise ConnectionError('Incomplete range; keep partial for safe resume')
                progress(downloaded_bytes=offset, last_network_error=None)
                break
            except HTTPError as error:
                if error.code not in {408, 429, 500, 502, 503, 504} or attempt == 5:
                    raise
                progress(last_network_error=repr(error))
                time.sleep(5 * attempt)
            except (URLError, TimeoutError, ConnectionError, OSError) as error:
                if attempt == 5:
                    raise
                progress(last_network_error=repr(error))
                time.sleep(5 * attempt)
    if not partial.is_file() or partial.stat().st_size != package['bytes']:
        raise ValueError('Incomplete archive; no extraction')
    progress(phase='checking_archive', downloaded_bytes=package['bytes'])
    verified = verify_archive(partial)
    os.rename(partial, archive)
    verified['archive']['path'] = str(archive)
    result = dict(verified, verified_at_utc=now(), package=package, receipt_reconciled=False)
    save_receipt(receipt, result)
    return archive, result


def missing_rows(rows):
    return {row['filename']: row for row in rows
            if not (target_path(DATA, row['filename']).is_file()
                    and target_path(DATA, row['filename']).stat().st_size > 0)}


def extract(archive, wanted, progress, verified_receipt=None):
    verified = verified_receipt or verify_archive(archive)
    if not verified.get('tar_integrity_verified'):
        raise ValueError('Unverified archive')
    staging = BATCH / 'staging'
    staging.mkdir(exist_ok=True)
    restored = skipped = 0
    journal_path = BATCH / 'restored_files.jsonl'
    if journal_path.is_file() and journal_path.stat().st_size:
        with journal_path.open('rb') as previous:
            previous.seek(-1, 2)
            torn_line = previous.read(1) != b'\n'
        if torn_line:
            with journal_path.open('ab') as previous:
                previous.write(b'\n')
                previous.flush()
                os.fsync(previous.fileno())
    with journal_path.open('a', encoding='utf-8') as journal:
        with tarfile.open(archive, mode='r|gz') as stream:
            for index, member in enumerate(stream, 1):
                name = member.name
                parts = PurePosixPath(name).parts
                if (name.startswith('/') or '\\' in name or ':' in name or '..' in parts
                        or member.issym() or member.islnk() or not (member.isfile() or member.isdir())):
                    raise ValueError('Unsafe tar member: ' + name)
                if member.isdir():
                    continue
                clean = name[2:] if name.startswith('./') else name
                row = wanted.get(clean)
                if row is None:
                    continue
                source = stream.extractfile(member)
                if source is None:
                    raise ValueError('Missing archive member stream')
                def durable_intent(record):
                    journal.write(json.dumps({'event': 'validated_before_publish', 'filename': clean,
                        'scene_token': row['scene_token'], 'part_archive': archive.name,
                        'archive_sha256': verified['archive']['sha256'], 'image': record}) + '\n')
                    journal.flush()
                    os.fsync(journal.fileno())

                with source:
                    result = restore_member(member, source, row, DATA, staging, before_publish=durable_intent)
                if result == 'restored':
                    restored += 1
                else:
                    skipped += 1
                if (restored + skipped) % 500 == 0:
                    journal.flush()
                    progress(restored_in_part=restored, skipped_in_part=skipped)
        journal.flush()
    progress(restored_in_part=restored, skipped_in_part=skipped)
    return restored


def audit(protocol, rows, progress):
    totals, per_scene, failures = Counter(), {}, []
    journal_path = BATCH / 'restored_files.jsonl'
    intents, torn_lines = {}, 0
    if journal_path.exists():
        for line in journal_path.read_text(encoding='utf-8').splitlines():
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                torn_lines += 1
                continue
            name = camera_name(entry['filename'])
            if name in intents and intents[name]['image']['sha256'] != entry['image']['sha256']:
                raise ValueError('Conflicting restoration intents')
            intents[name] = entry
    provenance_failures = 0
    for index, row in enumerate(rows, 1):
        path = target_path(DATA, row['filename'])
        status = 'exists_not_decoded'
        try:
            if not path.is_file():
                status = 'missing'
            elif not path.stat().st_size:
                status = 'empty'
            elif row['is_key_frame'] or row['channel'] == 'CAM_FRONT':
                validate_image(path, row)
                status = 'decoded'
        except Exception as error:
            status = 'decode_failed'
            if len(failures) < 100:
                failures.append({'filename': row['filename'], 'error': repr(error)})
        if not row['present_before'] and status in {'decoded', 'exists_not_decoded'}:
            intent = intents.get(row['filename'])
            if intent is None or file_record(path) != intent['image']:
                provenance_failures += 1
                status = 'restoration_provenance_failed'
        kind = 'keyframe' if row['is_key_frame'] else 'associated_nonkeyframe'
        key = row['role'] + '/' + row['channel'] + '/' + kind + '/' + status
        totals[key] += 1
        stats = per_scene.setdefault(row['scene_name'], Counter())
        stats['files'] += 1
        if status not in {'decoded', 'exists_not_decoded'}:
            stats['failures'] += 1
            if len(failures) < 100 and status in {'missing', 'empty'}:
                failures.append({'filename': row['filename'], 'error': status})
        if index % 5000 == 0:
            progress(audited_file_count=index)
    verify_records(protocol['bound_records'])
    result = {'created_at_utc': now(), 'scope': protocol['scope'], 'protocol': file_record(active_protocol()),
              'preparation_protocol': file_record(PROTOCOL),
              'counts_before': protocol['counts_before'], 'counts_after': dict(totals),
              'selected_file_count': len(rows), 'per_scene': {k: dict(v) for k, v in per_scene.items()},
              'failure_examples_at_most_100': failures,
              'restoration_journal': file_record(journal_path) if journal_path.exists() else None,
              'restoration_provenance_failure_count': provenance_failures,
              'ignored_torn_journal_line_count': torn_lines,
              'all_selected_media_present_and_required_decode_checks_passed': all(s['failures'] == 0 for s in per_scene.values()),
              'evaluation_scene_count': 150, 'development_scene_count': 8,
              'evaluation_semantics_inspected': False, 'split_or_features_changed': False,
              'limits': ['All six keyframe channels decoded; all CAM_FRONT associated nonkeyframes decoded.',
                         'Other associated nonkeyframes checked for presence/nonempty, not decoded.',
                         'Not expert semantic acceptance or permission to tune using evaluation.']}
    save_json(REPORT, result)
    return result


def run():
    import msvcrt
    protocol = json.loads(active_protocol().read_text(encoding='utf-8'))
    verify_records(protocol['bound_records'])
    if REPORT.exists():
        raise FileExistsError('Audit already exists; do not rerun recovery over a completed batch')
    lock = (BATCH / 'operation.lock').open('a+b')
    if lock.tell() == 0:
        lock.write(b'0')
        lock.flush()
    lock.seek(0)
    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    state = {'started_at_utc': now(), 'pid': os.getpid(), 'phase': 'initializing',
             'protocol': file_record(active_protocol()), 'completed_parts': []}

    def progress(**changes):
        state.update(changes, updated_at_utc=now())
        save_json(STATUS, state, exclusive=False)
        if changes.get('phase'):
            print(json.dumps(state, ensure_ascii=False), flush=True)

    try:
        rows = [json.loads(line) for line in FILES.read_text(encoding='utf-8').splitlines()]
        progress(remaining_files=len(missing_rows(rows)))
        for package in protocol['candidate_packages']:
            wanted = missing_rows(rows)
            if not wanted:
                break
            archive, receipt = download(package, progress)
            progress(phase='extracting', part=package['part'], restored_in_part=0, skipped_in_part=0)
            restored = extract(archive, wanted, progress, verified_receipt=receipt)
            state['completed_parts'].append({'part': package['part'], 'archive': receipt['archive'],
                                             'restored_files': restored})
            progress(remaining_files=len(missing_rows(rows)))
        progress(phase='auditing', audited_file_count=0)
        result = audit(protocol, rows, progress)
        progress(phase='completed' if result['all_selected_media_present_and_required_decode_checks_passed']
                 else 'completed_with_missing_or_invalid_media', report=file_record(REPORT))
    except BaseException as error:
        progress(phase='failed', error=repr(error))
        raise
    finally:
        lock.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['prepare', 'freeze-launch', 'freeze-transfer', 'run'])
    args = parser.parse_args()
    {'prepare': prepare, 'freeze-launch': freeze_launch, 'freeze-transfer': freeze_transfer, 'run': run}[args.stage]()
