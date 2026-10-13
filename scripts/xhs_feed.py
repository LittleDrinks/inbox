#!/usr/bin/env python3
"""Batch archive signed Xiaohongshu links through upstream OpenCLI (POSIX/WSL)."""
import argparse
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import urllib.error
import urllib.request
from urllib.parse import parse_qs, urljoin, urlsplit

from xhs_opencli import CallUser, download, read_note

SHORT_HOSTS = {'xhslink.cn', 'xhslink.com'}
NOTE_HOSTS = {'xiaohongshu.com', 'www.xiaohongshu.com'}
NOTE_ID = r'[0-9a-fA-F]{24}'
URL_RE = re.compile(r'https?://[^\s<>\"\'\u3000-\u303f\uff00-\uffef]+', re.I)


def validate_url(url):
    p = urlsplit(url)
    try:
        port = p.port
    except ValueError:
        raise ValueError('unsupported URL port') from None
    if p.scheme not in {'http', 'https'} or p.username or p.password or port not in {None, 80, 443}:
        raise ValueError('unsupported URL scheme, credentials, or port')
    if p.hostname in SHORT_HOSTS:
        if not re.fullmatch(r'/(?:o/)?[A-Za-z0-9_-]+/?', p.path):
            raise ValueError('invalid short-link path')
        return {'kind': 'short', 'url': url, 'note_id': None}
    if p.hostname not in NOTE_HOSTS:
        raise ValueError('host is not an allowed Xiaohongshu domain')
    match = re.fullmatch(r'/(?:explore|note|search_result|discovery/item)/(' + NOTE_ID + r')/?', p.path)
    if not match:
        match = re.fullmatch(r'/user/profile/[^/]+/(' + NOTE_ID + r')/?', p.path)
    if not match:
        raise ValueError('missing or invalid 24-hex noteId')
    tokens = parse_qs(p.query, keep_blank_values=True).get('xsec_token', [])
    if len(tokens) != 1 or not tokens[0].strip():
        raise ValueError('a full signed URL with one nonempty xsec_token is required')
    return {'kind': 'note', 'url': url, 'note_id': match.group(1)}


def parse_input(text):
    entries, seen = [], set()
    for line in text.splitlines():
        urls = [m.group().rstrip('.,;!?)）]}>') for m in URL_RE.finditer(line)]
        if not urls and line.strip() and ('xhslink' in line or 'xiaohongshu' in line or re.fullmatch(NOTE_ID, line.strip())):
            urls = [line.strip()]
        for url in urls:
            entry = {'input': url, 'status': 'pending'}
            try:
                entry.update(validate_url(url))
                if url in seen:
                    entry['status'] = 'duplicate'
                seen.add(url)
            except ValueError:
                entry.update(status='invalid', error='invalid or unsigned Xiaohongshu URL')
            entries.append(entry)
    return entries or [{'status': 'invalid', 'error': 'no supported URL found'}]


def resolve_short(url):
    """HTTP only for allowlisted redirects: note requires a full signed URL.

    No HTML scraping, cookies, authentication or media HTTP fallback.
    """
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    opener = urllib.request.build_opener(NoRedirect)
    for _ in range(6):
        parsed = validate_url(url)
        if parsed['kind'] == 'note':
            return parsed
        try:
            with opener.open(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=20):
                raise ValueError('short link did not redirect; supply a full signed URL')
        except urllib.error.HTTPError as exc:
            try:
                if exc.code in {401, 403, 429}:
                    raise CallUser('short-link access blocked; supply a signed URL or retry later') from None
                if exc.code not in {301, 302, 303, 307, 308} or not exc.headers.get('Location'):
                    raise ValueError('short-link resolution failed') from None
                url = urljoin(url, exc.headers['Location'])
                validate_url(url)  # Validate BEFORE requesting the next hop.
            finally:
                exc.close()
        except (urllib.error.URLError, TimeoutError):
            raise ValueError('short-link network failure') from None
    raise ValueError('too many short-link redirects')


def safe_path(root, relative):
    relative = Path(relative)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('unsafe artifact path')
    path = root / relative
    for part in [path, *path.parents]:
        if part.is_symlink():
            raise ValueError('symlink traversal is not allowed')
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('artifact escapes run directory')
    return path


def run_path(raw):
    inbox = Path(os.environ.get('INBOX_DIR', '/mnt/e/OBSIDIAN/inbox')).expanduser().absolute()
    root = Path(raw).expanduser().absolute()
    webclip = inbox / 'webclip'
    if '..' in root.parts or root == webclip or not root.is_relative_to(webclip):
        raise ValueError('--run-dir must be strictly under INBOX_DIR/webclip')
    safe_path(webclip, root.relative_to(webclip))
    for ancestor in root.parents:
        if ancestor == webclip:
            break
        if (ancestor / 'state.json').exists() or (ancestor / '.lock').exists():
            raise ValueError('run must not be nested inside an existing batch')
    return root


def atomic_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def atomic_json(path, data):
    atomic_text(path, json.dumps(data, ensure_ascii=False, indent=2) + '\n')


@contextlib.contextmanager
def locked(root):
    lockpath = safe_path(root, '.lock')
    with lockpath.open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('run is locked by another process') from None
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def record(root, path):
    return {'path': str(path.relative_to(root)), 'sha256': digest(path)}


def intact(root, file):
    try:
        return bool(file) and digest(safe_path(root, file['path'])) == file['sha256']
    except (OSError, ValueError, KeyError):
        return False


def complete(root, item, media):
    return (item['status'] == 'captured' and not item.get('pending_clip_hash') and intact(root, item.get('body'))
            and intact(root, item.get('clip')) and (media == 'skip' or
            (bool(item.get('files')) and all(intact(root, f) for f in item['files']))))


def clip_target(root, item):
    target = safe_path(root, 'clips/' + item['note_id'] + '.md')
    if target.exists() and digest(target) not in {item.get('clip', {}).get('sha256'), item.get('pending_clip_hash')}:
        raise ValueError('user-edited or unowned markdown; preserved without overwrite')
    return target


def write_clip(root, state, item, fields, save):
    target = clip_target(root, item)
    metadata = {'date': state['date'], 'source': '小红书', 'status': '#status/todo',
                'capture_status': item['status'], 'identity_source': 'input_signed_url',
                'note_id': item['note_id'], 'url': item['url'],
                'title': fields['title'] or '无标题-' + item['note_id'],
                'author': fields['author'], 'media_status': item['media_status']}
    text = '---\n' + ''.join(k + ': ' + json.dumps(v, ensure_ascii=False) + '\n' for k, v in metadata.items()) + '---\n\n' + fields['content'] + '\n'
    for file in item.get('files', []):
        text += f"\n[{file['type']} {file['index']}](../{file['path']})\n"
    item['pending_clip_hash'] = hashlib.sha256(text.encode()).hexdigest()
    save()  # Crash recovery accepts only our last or intended bytes.
    clip_target(root, item)  # Recheck after journaling; never knowingly replace new user edits.
    atomic_text(target, text)
    item['clip'] = record(root, target)
    item.pop('pending_clip_hash', None)


def process(root, state):
    def save():
        atomic_json(safe_path(root, 'state.json'), state)
    for entry in state['entries']:
        if entry['status'] in {'invalid', 'duplicate', 'linked'}:
            continue
        try:
            if entry['kind'] == 'short':
                entry.update(resolve_short(entry['url']))
            nid = entry['note_id']
            if nid in state['items']:
                entry['status'] = 'duplicate'
            else:
                state['items'][nid] = {'note_id': nid, 'url': entry['url'], 'status': 'pending'}
                entry['status'] = 'linked'
        except ValueError:
            entry.update(status='failed', error='short-link resolution failed; supply full signed URL')
        save()
    for item in state['items'].values():
        if complete(root, item, state['media']):
            continue
        fields, stopped = None, None
        try:
            clip_target(root, item)  # Do not make browser calls for edited clips.
            if validate_url(item['url'])['note_id'] != item['note_id']:
                raise ValueError('stored noteId does not match URL')
            item.update(status='running', error=None)
            save()
            # Every retry is a whole note. Old attempts stay untouched; no media history/reuse.
            attempt = Path(tempfile.mkdtemp(prefix='attempt-', dir=root))
            fields = read_note(item['url'], item['note_id'])
            atomic_json(attempt / 'body.json', fields)
            item.update(body=record(root, attempt / 'body.json'), files=[], media_status='skipped' if state['media'] == 'skip' else 'pending')
            save()
            if state['media'] == 'all':
                output = attempt / 'output'
                output.mkdir()
                files = download(item['url'], item['note_id'], output)
                item['files'] = [{**record(root, f['local']), 'index': f['index'], 'type': f['type']} for f in files]
                item['media_status'] = 'complete'
            item['status'] = 'captured'
        except (CallUser, ValueError, OSError) as exc:
            item.update(status='partial' if fields else 'failed', error=str(exc) if isinstance(exc, (CallUser, ValueError)) else 'local filesystem error')
            if fields:
                item['media_status'] = 'failed'
            print(item['note_id'] + ': ' + item['error'], file=sys.stderr)
            if isinstance(exc, CallUser):
                stopped = exc
        if fields:
            try:
                write_clip(root, state, item, fields, save)
            except (ValueError, OSError):
                item.update(status='failed', error='markdown conflict or write failure; existing file preserved')
        save()
        if stopped:
            raise stopped


def summarize(root, state):
    captured = sum(complete(root, i, state['media']) for i in state['items'].values())
    changed = [f['path'] for i in state['items'].values() for f in [i.get('body'), i.get('clip'), *i.get('files', [])] if f and not intact(root, f)]
    return {'run_dir': str(root), 'state_path': str(root / 'state.json'),
            'input_urls': len(state['entries']), 'items': len(state['items']),
            'duplicate_inputs': sum(e['status'] == 'duplicate' for e in state['entries']),
            'invalid_inputs': sum(e['status'] == 'invalid' for e in state['entries']),
            'captured': captured, 'partial': sum(i['status'] == 'partial' for i in state['items'].values()),
            'failed': sum(i['status'] == 'failed' for i in state['items'].values()) + sum(e['status'] == 'failed' for e in state['entries']),
            'pending': sum(i['status'] not in {'partial', 'failed'} and not complete(root, i, state['media']) for i in state['items'].values()) + sum(e['status'] == 'pending' for e in state['entries']),
            'missing_or_changed': changed,
            'clips': [str(safe_path(root, i['clip']['path'])) for i in state['items'].values() if i.get('clip')]}


def load_state(root):
    state = json.loads(safe_path(root, 'state.json').read_text(encoding='utf-8'))
    if (not isinstance(state, dict) or state.get('schema') != 2):
        raise ValueError('unsupported run schema; preserve this run and create a new --run-dir under INBOX_DIR/webclip')
    if (not isinstance(state.get('items'), dict) or not isinstance(state.get('entries'), list)
            or state.get('media') not in {'all', 'skip'} or not isinstance(state.get('date'), str)):
        raise ValueError('malformed state.json')
    for entry in state['entries']:
        if not isinstance(entry, dict) or entry.get('status') not in {'pending', 'linked', 'duplicate', 'invalid', 'failed'}:
            raise ValueError('malformed stored input')
        if entry['status'] in {'pending', 'failed'}:
            validate_url(entry['url'])
    for nid, item in state['items'].items():
        if (not re.fullmatch(NOTE_ID, nid) or not isinstance(item, dict)
                or item.get('note_id') != nid or item.get('status') not in {'pending', 'running', 'captured', 'partial', 'failed'}
                or validate_url(item['url'])['note_id'] != nid):
            raise ValueError('malformed stored note identity')
        for f in [item.get('body'), item.get('clip'), *item.get('files', [])]:
            if f:
                safe_path(root, f['path'])
    return state


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    capture = sub.add_parser('capture')
    capture.add_argument('--input', required=True)
    capture.add_argument('--media', choices=['all', 'skip'], default='all')
    resume = sub.add_parser('resume', help='retry whole incomplete notes; skip intact completed notes')
    status = sub.add_parser('status', help='offline hashes only; never calls OpenCLI')
    for command in (capture, resume, status):
        command.add_argument('--run-dir', required=True)
    for command in (capture, resume):
        command.add_argument('--backend', choices=['opencli'], default='opencli', help='compatibility alias')
    args = parser.parse_args(argv)
    try:
        root = run_path(args.run_dir)
        if args.command == 'capture':
            text = sys.stdin.read() if args.input == '-' else Path(args.input).read_text(encoding='utf-8')
            root.parent.mkdir(parents=True, exist_ok=True)
            root.mkdir()  # Exclusive creation: even an existing empty directory is protected.
            state = {'schema': 2, 'date': dt.datetime.now().astimezone().isoformat(),
                     'media': args.media, 'entries': parse_input(text), 'items': {}}
            with locked(root):
                atomic_text(root / 'input.txt', text)
                atomic_json(root / 'state.json', state)
                process(root, state)
        elif args.command == 'resume':
            load_state(root)  # Reject legacy schemas before even creating a lock.
            with locked(root):
                state = load_state(root)
                process(root, state)
        else:
            state = load_state(root)
        summary = summarize(root, state)
        print(json.dumps(summary, ensure_ascii=False, separators=(',', ':')))
        return int(bool(summary['invalid_inputs'] or summary['failed'] or summary['partial'] or summary['pending'] or summary['missing_or_changed']))
    except CallUser as exc:
        summary = summarize(root, state)
        summary.update(status='call_user', error=str(exc), action_required='check_chrome_bridge_login_or_security')
        print(json.dumps(summary, ensure_ascii=False, separators=(',', ':')))
        return 3
    except (OSError, ValueError, KeyError, TypeError) as exc:
        message = str(exc) if isinstance(exc, ValueError) else 'invalid path/state or existing run; preserve existing data and use a new --run-dir under INBOX_DIR/webclip'
        print(json.dumps({'status': 'error', 'error': message}, separators=(',', ':')))
        print(message, file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
