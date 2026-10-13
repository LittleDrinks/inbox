"""Synthetic executable at the subprocess boundary, not live website evidence."""
import json
import os
from pathlib import Path
import re
import struct
import sys
import zlib

args = sys.argv[1:]
with Path(os.environ['FIXTURE_CALLS']).open('a') as log:
    log.write(json.dumps(args) + '\n')
assert args[0] == 'xiaohongshu' and args[1] in {'note', 'download'}, args
mode = os.environ.get('FIXTURE_MODE', 'normal')
nid = re.search(r'/(?:explore|note)/([0-9a-fA-F]{24})', args[2]).group(1)
if mode in {'bridge', 'auth', 'security'}:
    print({'bridge': 'Browser Bridge extension not connected', 'auth': 'AUTH_REQUIRED',
           'security': 'SECURITY_BLOCK'}[mode] + ' ' + args[2] + ' cookie=SECRET', file=sys.stderr)
    sys.exit(1)
if mode in {'bridge_code', 'auth_code'}:
    print('opaque upstream error', file=sys.stderr)
    sys.exit(69 if mode == 'bridge_code' else 77)
if args[1] == 'download' and mode == 'download_bridge':
    print('BROWSER_CONNECT profile-disconnected ' + args[2], file=sys.stderr)
    sys.exit(69)
if mode == 'fail' or (mode == 'first_fail' and nid.startswith('0')):
    print('EMPTY_RESULT ' + args[2] + ' token=SECRET', file=sys.stderr)
    sys.exit(1)
if args[1] == 'note':
    fields = {'title': '', 'author': 'fixture author', 'content': 'fixture body',
              'likes': '3', 'collects': '2', 'comments': '1'}
    if mode == 'mentions_security':
        fields['content'] = 'How to handle SECURITY_BLOCK and authentication errors'
    if mode == 'wrong_id':
        fields['noteId'] = 'b' * 24
    if mode == 'bad_body':
        fields['content'] = {}
    print(json.dumps([{'field': k, 'value': v} for k, v in fields.items()]))
else:
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(b'\x00\xff\x00\x00')) + chunk(b'IEND', b''))
    output = Path(args[args.index('--output') + 1]) / nid
    output.mkdir(parents=True)
    rows = []
    for index in (1, 2):
        kind = 'video' if mode == 'video' and index == 1 else 'image'
        payload = Path(os.environ['FIXTURE_VIDEO']).read_bytes() if kind == 'video' else png
        if index == 2:
            if mode == 'html':
                payload = b'<html>error</html>'
            elif mode == 'zero':
                payload = b''
            elif mode == 'corrupt':
                payload = b'\x89PNG\r\n\x1a\n' + b'corrupt'
        path = output / f"{nid}_{index}.{'mp4' if kind == 'video' else 'jpg'}"
        if mode == 'symlink' and index == 2:
            path.symlink_to(os.environ['FIXTURE_VIDEO'])
        elif mode != 'missing' or index == 1:
            path.write_bytes(payload)
        rows.append({'index': index, 'type': kind, 'status': 'success', 'size': '1 KB'})
        if mode == 'wrong_download_id':
            rows[-1]['note_id'] = 'b' * 24
    if mode == 'extra':
        (output / 'unexpected.jpg').write_bytes(png)
    if mode == 'failed_row':
        rows[1]['status'] = 'failed'
    if mode == 'duplicate_index':
        rows[1]['index'] = 1
    if mode == 'gap':
        rows[1]['index'] = 3
    print(json.dumps(list(reversed(rows))))  # Ordering must follow index, not JSON order.
