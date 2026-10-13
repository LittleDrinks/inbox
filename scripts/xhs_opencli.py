"""Upstream OpenCLI calls and validation; no browser adapter or HTTP media fallback."""
import json
from pathlib import Path
import re
import subprocess
import time


class CallUser(Exception):
    """Stop the batch: the browser, login or site security needs user attention."""


def start_chrome():
    """Open normal Windows Chrome only when absent; require a live bridge probe."""
    try:
        tasks = subprocess.run(
            ['/mnt/c/Windows/System32/tasklist.exe', '/FI', 'IMAGENAME eq chrome.exe',
             '/FO', 'CSV', '/NH'], capture_output=True, text=True, errors='replace', timeout=5)
        if tasks.returncode or re.search(r'"chrome\.exe"', tasks.stdout, re.I):
            raise CallUser('Chrome already running or process check unavailable; check Chrome Bridge')
        chrome = Path('/mnt/c/Program Files/Google/Chrome/Application/chrome.exe')
        if not chrome.is_file():
            raise CallUser('Windows Chrome unavailable; open Chrome and check Chrome Bridge')
        subprocess.Popen([str(chrome)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
        deadline = time.monotonic() + 20
        while (remaining := deadline - time.monotonic()) > 0:
            try:
                probe = subprocess.run(['opencli', 'doctor'], capture_output=True, text=True,
                                       timeout=min(5, remaining))
                if re.search(r'^\[OK\] Connectivity: connected in ', probe.stdout, re.M):
                    return
            except subprocess.TimeoutExpired:
                pass
            time.sleep(min(1, max(0, deadline - time.monotonic())))
    except (OSError, subprocess.TimeoutExpired):
        raise CallUser('Chrome startup unavailable; open Chrome and check Chrome Bridge') from None
    raise CallUser('Chrome opened but Chrome Bridge did not connect; check extension and retry')


def opencli(command, url, *args):
    for attempt in range(2):
        try:
            result = subprocess.run(
                ['opencli', 'xiaohongshu', command, url, *args, '-f', 'json',
                 '--window', 'background'], capture_output=True, text=True, timeout=180)
        except FileNotFoundError:
            raise CallUser('OpenCLI unavailable; install/configure OpenCLI before retrying') from None
        except subprocess.TimeoutExpired:
            raise ValueError('OpenCLI command timed out') from None
        try:
            data = json.loads(result.stdout)
        except ValueError:
            data = None
        # Valid success rows are data, not diagnostics (body text may mention login/errors).
        if result.returncode == 0 and isinstance(data, list):
            return data
        output = result.stdout + '\n' + result.stderr
        # Never persist raw diagnostics: they can contain signed URLs and cookies.
        auth = result.returncode == 77 or re.search(
            r'AUTH[_ ]?REQUIRED|SECURITY[_ ]?BLOCK|login.?wall|'
            r'requires? login|not logged in|authentication|'
            r'请登录|登录后查看|安全限制|访问链接异常', output, re.I)
        bridge = result.returncode == 69 or re.search(
            r'BROWSER_CONNECT|bridge.*(?:not connected|disconnect)|'
            r'extension.*(?:not connected|disconnect)|daemon.*not running', output, re.I)
        if bridge and not auth and attempt == 0:
            start_chrome()
            continue
        if bridge or auth:
            raise CallUser('OpenCLI browser/login/security blocked; check Chrome Bridge and login, then retry')
        if result.returncode:
            raise ValueError('OpenCLI ' + command + ' failed (raw diagnostics omitted)')
        raise ValueError('OpenCLI returned invalid JSON or an unexpected result')


def check_id(data, requested):
    for key in ('noteId', 'note_id', 'nid'):
        if key in data and data[key] != requested:
            raise ValueError('returned noteId does not match input signed URL')


def read_note(url, requested):
    rows = opencli('note', url)
    fields = {}
    for row in rows:
        if (not isinstance(row, dict) or not isinstance(row.get('field'), str)
                or 'value' not in row or row['field'] in fields):
            raise ValueError('expected unique note field/value rows')
        fields[row['field']] = row['value']
    check_id(fields, requested)
    if any(not isinstance(fields.get(k), str) for k in ('title', 'author', 'content')):
        raise ValueError('note title/author/content must be strings')
    if not any(fields[k].strip() for k in ('title', 'author', 'content')):
        raise ValueError('empty note body')
    return fields


def validate_media(path, kind):
    if path.is_symlink() or not path.is_file():
        raise ValueError('missing or unsafe downloaded media')
    with path.open('rb') as stream:
        prefix = stream.read(16)
    image = (prefix.startswith((b'\xff\xd8\xff', b'\x89PNG\r\n\x1a\n', b'GIF87a', b'GIF89a'))
             or (prefix.startswith(b'RIFF') and prefix[8:12] == b'WEBP')
             or (prefix[4:8] == b'ftyp' and prefix[8:12] in {b'avif', b'avis', b'heic', b'heix'}))
    if not (image if kind == 'image' else prefix[4:8] == b'ftyp'):
        raise ValueError('invalid media signature (empty/HTML/error payload)')
    try:
        result = subprocess.run(
            ['ffmpeg', '-nostdin', '-v', 'error', '-xerror', '-err_detect', 'explode',
             '-i', str(path), '-map', '0:v:0', '-f', 'null', '-'],
            capture_output=True, text=True, timeout=180)
    except FileNotFoundError:
        raise ValueError('ffmpeg required for full media decode') from None
    except subprocess.TimeoutExpired:
        raise ValueError('media decode timed out') from None
    if result.returncode or result.stderr.strip():
        raise ValueError('media decode failed')


def download(url, requested, output):
    rows = opencli('download', url, '--output', str(output))
    if output.is_symlink() or not output.is_dir():
        raise ValueError('unsafe or missing download output directory')
    if not rows:
        raise ValueError('download returned an empty inventory')
    expected = {}
    for row in rows:
        if (not isinstance(row, dict) or type(row.get('index')) is not int
                or row['index'] < 1 or row.get('type') not in {'image', 'video'}
                or row['index'] in expected):
            raise ValueError('invalid or duplicate download inventory index')
        check_id(row, requested)
        if row.get('status') != 'success':
            raise ValueError('download inventory contains failed media')
        ext = 'jpg' if row['type'] == 'image' else 'mp4'
        expected[row['index']] = (Path(requested) / f"{requested}_{row['index']}.{ext}", row['type'])
    if sorted(expected) != list(range(1, len(rows) + 1)):
        raise ValueError('download inventory indexes must be contiguous from 1')
    actual = set()
    for path in output.rglob('*'):
        if path.is_symlink():
            raise ValueError('unsafe symlink in downloaded files')
        if path.is_file():
            actual.add(path.relative_to(output))
    if actual != {p for p, _ in expected.values()}:
        raise ValueError('download files do not match expected inventory')
    files = []
    for index, (relative, kind) in sorted(expected.items()):
        path = output / relative
        validate_media(path, kind)
        files.append({'index': index, 'type': kind, 'local': path})
    return files
