"""Public CLI tests through a synthetic OpenCLI executable, never a live browser."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'scripts' / 'xhs_feed.py'
NID = '0123456789abcdef01234567'
URL = 'https://www.xiaohongshu.com/explore/' + NID + '?xsec_token=ABC==&xsec_source=app_share'
SECOND = URL.replace(NID, 'a' * 24)


class CLIContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.run_dir = self.base / 'webclip' / 'run'
        self.input = self.base / 'pasted.txt'
        bindir = self.base / 'bin'
        bindir.mkdir()
        exe = bindir / 'opencli'
        exe.write_text('#!' + sys.executable + '\n' + (ROOT / 'tests/fixtures/opencli_fixture.py').read_text())
        exe.chmod(0o755)
        self.log = self.base / 'calls.jsonl'
        self.env = dict(os.environ, INBOX_DIR=str(self.base),
                        PATH=str(bindir) + os.pathsep + os.environ['PATH'],
                        FIXTURE_CALLS=str(self.log), FIXTURE_MODE='normal',
                        FIXTURE_VIDEO=str(ROOT / 'tests/fixtures/minimal.mp4'))

    def cli(self, *args, short_timeout=False):
        # Keep synthetic bridge failures away from the real Windows launcher.
        runner = '''
import runpy, subprocess, sys
from unittest.mock import patch, Mock
sys.path.insert(0, str(__import__('pathlib').Path(sys.argv[1]).parent))
real_run, real_popen = subprocess.run, subprocess.Popen

def run(argv, *args, **kwargs):
    if argv[0] == '/mnt/c/Windows/System32/tasklist.exe':
        return subprocess.CompletedProcess(argv, 0, '"chrome.exe","123"', '')
    return real_run(argv, *args, **kwargs)

def launch(argv, *args, **kwargs):
    if str(argv[0]).endswith('chrome.exe'):
        raise AssertionError('Tests must not open real Chrome')
    return real_popen(argv, *args, **kwargs)

with patch('subprocess.run', side_effect=run), patch('subprocess.Popen', side_effect=launch):
    SHORT_TIMEOUT_PATCH
    runpy.run_path(sys.argv.pop(1), run_name='__main__')
'''
        timeout_patch = ("opener = Mock(); opener.open.side_effect = TimeoutError('transport timed out'); "
                         "patch('urllib.request.build_opener', return_value=opener).start()"
                         if short_timeout else 'pass')
        runner = runner.replace('SHORT_TIMEOUT_PATCH', timeout_patch)
        return subprocess.run([sys.executable, '-c', runner, str(CLI), *args], env=self.env,
                              capture_output=True, text=True, timeout=30)

    def capture(self, text=URL, media='skip'):
        self.input.write_text(text)
        return self.cli('capture', '--input', str(self.input), '--run-dir', str(self.run_dir), '--media', media)

    def resume(self):
        return self.cli('resume', '--run-dir', str(self.run_dir))

    def state(self):
        return json.loads((self.run_dir / 'state.json').read_text())

    def item(self):
        return self.state()['items'][NID]

    def clip(self):
        return self.run_dir / 'clips' / (NID + '.md')

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def test_body_mentioning_security_errors_is_not_a_bridge_error(self):
        self.env['FIXTURE_MODE'] = 'mentions_security'
        result = self.capture()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('SECURITY_BLOCK', self.clip().read_text())

    def test_upstream_rows_without_noteid_use_input_identity(self):
        result = self.capture()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('identity_source: "input_signed_url"', self.clip().read_text())
        self.assertNotIn('identity_status: "verified"', self.clip().read_text())
        self.assertEqual(self.calls()[0][2], URL)
        self.assertEqual(self.item()['status'], 'captured')

    def test_batch_dedupes_and_preserves_literal_signed_url(self):
        result = self.capture('分享 ' + URL + '\n' + URL + '\n' + URL.replace('ABC==', 'OTHER%3D') + '\n' + SECOND)
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual((summary['items'], summary['captured'], summary['duplicate_inputs']), (2, 2, 2))
        self.assertEqual([c[2] for c in self.calls()], [URL, SECOND])
        self.assertEqual((self.run_dir / 'input.txt').read_text(), self.input.read_text())
        before = self.calls()
        self.assertEqual(self.resume().returncode, 0)
        self.assertEqual(self.calls(), before)

    def test_real_decode_and_ordered_upstream_inventory(self):
        self.env['FIXTURE_MODE'] = 'video'
        result = self.capture(media='all')
        self.assertEqual(result.returncode, 0, result.stderr)
        item = self.item()
        self.assertEqual([f['index'] for f in item['files']], [1, 2])
        self.assertEqual([f['type'] for f in item['files']], ['video', 'image'])
        self.assertTrue(all((self.run_dir / f['path']).stat().st_size for f in item['files']))
        text = self.clip().read_text()
        self.assertLess(text.index('[video 1]'), text.index('[image 2]'))
        self.assertEqual(self.calls()[1][2], URL)
        before = self.calls()
        self.assertEqual(self.resume().returncode, 0)
        self.assertEqual(self.calls(), before)

    def test_bad_media_preserves_partial_body_then_retries_whole_note(self):
        for mode in ('html', 'zero', 'corrupt', 'missing', 'extra', 'failed_row', 'duplicate_index', 'gap', 'symlink', 'wrong_download_id'):
            with self.subTest(mode=mode):
                self.run_dir = self.base / 'webclip' / mode
                self.env['FIXTURE_MODE'] = mode
                result = self.capture(media='all')
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(json.loads(result.stdout)['captured'], 0)
                self.assertEqual(self.item()['status'], 'partial')
                self.assertIn('capture_status: "partial"', self.clip().read_text())
                self.assertIn('fixture body', self.clip().read_text())
                self.assertTrue((self.run_dir / self.item()['body']['path']).exists())
                self.assertEqual(self.item()['files'], [])  # No per-media checkpoints.
        self.env['FIXTURE_MODE'] = 'normal'
        old_body = self.item()['body']['path']
        before = len(self.calls())
        result = self.resume()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([c[1] for c in self.calls()[before:]], ['note', 'download'])
        self.assertNotEqual(self.item()['body']['path'], old_body)
        self.assertTrue((self.run_dir / old_body).exists())
        self.assertNotIn('partial', self.clip().read_text())

    def test_missing_completed_media_retries_whole_note(self):
        self.assertEqual(self.capture(media='all').returncode, 0)
        original = self.item()['files'][0]['path']
        (self.run_dir / original).unlink()
        before = len(self.calls())
        status = self.cli('status', '--run-dir', str(self.run_dir))
        self.assertEqual(status.returncode, 1)
        self.assertEqual(json.loads(status.stdout)['captured'], 0)
        self.assertEqual(self.resume().returncode, 0)
        self.assertEqual([c[1] for c in self.calls()[before:]], ['note', 'download'])
        self.assertNotEqual(self.item()['files'][0]['path'], original)

    def test_bridge_auth_security_stop_batch_and_redact_diagnostics(self):
        for mode in ('bridge', 'auth', 'security', 'bridge_code', 'auth_code'):
            with self.subTest(mode=mode):
                self.run_dir = self.base / 'webclip' / mode
                self.env['FIXTURE_MODE'] = mode
                before = len(self.calls())
                result = self.capture(URL + '\n' + SECOND)
                self.assertEqual(result.returncode, 3, result.stderr)
                self.assertEqual(json.loads(result.stdout)['status'], 'call_user')
                self.assertEqual(len(self.calls()) - before, 1)
                self.assertNotIn('ABC==', result.stdout + result.stderr)
                self.assertNotIn('SECRET', (self.run_dir / 'state.json').read_text() + result.stderr)
                self.assertEqual(self.state()['items']['a' * 24]['status'], 'pending')

    def test_download_disconnect_keeps_partial_body_and_stops_batch(self):
        self.env['FIXTURE_MODE'] = 'download_bridge'
        result = self.capture(URL + '\n' + SECOND, media='all')
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertEqual([c[1] for c in self.calls()], ['note', 'download'])
        self.assertEqual(self.item()['status'], 'partial')
        self.assertIn('capture_status: "partial"', self.clip().read_text())
        self.assertEqual(self.state()['items']['a' * 24]['status'], 'pending')
        self.env['FIXTURE_MODE'] = 'normal'
        self.assertEqual(self.resume().returncode, 0)
        self.assertEqual([c[1] for c in self.calls()[2:]], ['note', 'download', 'note', 'download'])

    def test_ordinary_failure_continues_then_resume_only_failed_note(self):
        self.env['FIXTURE_MODE'] = 'first_fail'
        result = self.capture(URL + '\n' + SECOND)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)['captured'], 1)
        self.assertNotIn('ABC==', result.stdout + result.stderr)
        self.env['FIXTURE_MODE'] = 'normal'
        before = len(self.calls())
        self.assertEqual(self.resume().returncode, 0)
        self.assertEqual([c[2] for c in self.calls()[before:]], [URL])

    def test_optional_contradictory_id_and_invalid_body_fail(self):
        for mode in ('wrong_id', 'bad_body'):
            self.run_dir = self.base / 'webclip' / mode
            self.env['FIXTURE_MODE'] = mode
            result = self.capture()
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertFalse(self.clip().exists())

    def test_edited_markdown_is_never_overwritten_or_refetched(self):
        self.assertEqual(self.capture(media='all').returncode, 0)
        changed = self.clip().read_text() + '\nUSER EDIT\n'
        self.clip().write_text(changed)
        before = self.calls()
        result = self.resume()
        self.assertEqual(result.returncode, 1)
        self.assertIn('user-edited', result.stderr)
        self.assertEqual(self.clip().read_text(), changed)
        self.assertEqual(self.calls(), before)

    def test_pending_markdown_write_is_not_reported_complete(self):
        self.assertEqual(self.capture().returncode, 0)
        state = self.state()
        state['items'][NID]['pending_clip_hash'] = '0' * 64
        (self.run_dir / 'state.json').write_text(json.dumps(state))
        result = self.cli('status', '--run-dir', str(self.run_dir))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)['captured'], 0)
        before = len(self.calls())
        self.assertEqual(self.resume().returncode, 0)
        self.assertEqual(len(self.calls()) - before, 1)

    def test_status_is_offline_read_only_even_with_broken_bridge(self):
        self.assertEqual(self.capture().returncode, 0)
        before = {p: p.read_bytes() for p in self.run_dir.rglob('*') if p.is_file()}
        self.env['FIXTURE_MODE'] = 'bridge'
        self.env['PATH'] = str(self.base / 'missing-bin')
        calls = self.calls()
        result = self.cli('status', '--run-dir', str(self.run_dir))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), calls)
        self.assertEqual(before, {p: p.read_bytes() for p in self.run_dir.rglob('*') if p.is_file()})

    def test_paths_existing_runs_and_symlink_traversal_are_rejected(self):
        valid = self.run_dir
        for path in (self.base, self.base / 'run', self.base / 'webclip', self.base.parent / 'outside'):
            self.run_dir = path
            self.assertEqual(self.capture().returncode, 2)
        self.run_dir = valid
        self.assertEqual(self.capture().returncode, 0)
        before = (valid / 'state.json').read_bytes()
        self.assertEqual(self.capture().returncode, 2)
        self.assertEqual((valid / 'state.json').read_bytes(), before)
        outside = self.base / 'outside'
        outside.mkdir()
        link = self.base / 'webclip' / 'link'
        link.symlink_to(outside, target_is_directory=True)
        self.run_dir = link / 'bad'
        self.assertEqual(self.capture().returncode, 2)
        self.assertFalse((outside / 'bad').exists())
        self.run_dir = valid
        clip = self.clip()
        clip.unlink()
        clip.symlink_to(outside / 'victim.md')
        self.assertEqual(self.resume().returncode, 2)
        self.assertFalse((outside / 'victim.md').exists())

    def test_new_batch_cannot_be_nested_inside_existing_batch(self):
        self.assertEqual(self.capture().returncode, 0)
        original = self.run_dir
        before = (original / 'state.json').read_bytes()
        self.run_dir = original / 'nested'
        result = self.capture()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse(self.run_dir.exists())
        self.assertEqual((original / 'state.json').read_bytes(), before)

    def test_lock_prevents_concurrent_resume(self):
        self.assertEqual(self.capture().returncode, 0)
        with (self.run_dir / '.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.resume()
        self.assertEqual(result.returncode, 2)

    def test_schema_one_rejected_without_mutating_old_data(self):
        self.run_dir.mkdir(parents=True)
        (self.run_dir / 'state.json').write_text('{"schema":1,"items":{},"entries":[]}')
        before = (self.run_dir / 'state.json').read_bytes()
        for cmd in ('status', 'resume'):
            result = self.cli(cmd, '--run-dir', str(self.run_dir))
            self.assertEqual(result.returncode, 2)
            self.assertIn('new --run-dir', result.stderr)
        self.assertEqual((self.run_dir / 'state.json').read_bytes(), before)
        self.assertFalse((self.run_dir / '.lock').exists())

    def test_short_link_transport_timeout_continues_valid_urls(self):
        self.input.write_text('http://xhslink.com/ABC\n' + URL)
        result = self.cli('capture', '--input', str(self.input), '--run-dir',
                          str(self.run_dir), '--media', 'skip', short_timeout=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads(result.stdout)['captured'], 1)
        self.assertEqual(self.state()['entries'][0]['status'], 'failed')
        self.assertEqual(self.state()['entries'][0]['error'],
                         'short-link resolution failed; supply full signed URL')
        self.assertEqual([c[2] for c in self.calls()], [URL])

    def test_short_redirects_use_signed_url_and_reject_unsafe_hops(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        import threading
        requests = []
        destination = [URL]
        response_code = [302]
        class Redirect(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                self.send_response(response_code[0])
                self.send_header('Location', destination[0])
                self.end_headers()

            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Redirect)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            proxy = f'http://127.0.0.1:{server.server_port}'
            self.env.update(http_proxy=proxy, HTTP_PROXY=proxy, no_proxy='', NO_PROXY='')
            result = self.capture('分享：http://xhslink.com/ABC，\n' + URL)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual([c[2] for c in self.calls()], [URL])
            self.assertEqual(json.loads(result.stdout)['duplicate_inputs'], 1)
            self.assertEqual(requests, ['http://xhslink.com/ABC'])
            self.run_dir = self.base / 'webclip' / 'unsafe-redirect'
            destination[0] = 'http://evil.example/steal'
            before = self.calls()
            result = self.capture('http://xhslink.com/ABC')
            self.assertEqual(result.returncode, 1)
            self.assertEqual(self.calls(), before)
            self.assertEqual(requests, ['http://xhslink.com/ABC', 'http://xhslink.com/ABC'])
            self.run_dir = self.base / 'webclip' / 'blocked-redirect'
            response_code[0] = 403
            result = self.capture('http://xhslink.com/ABC\n' + URL)
            self.assertEqual(result.returncode, 3, result.stderr)
            self.assertEqual(json.loads(result.stdout)['status'], 'call_user')
            self.assertEqual(self.calls(), before)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_link_validation_is_visible_at_cli_boundary(self):
        invalid = [NID, URL.replace('www.xiaohongshu.com', 'xiaohongshu.com.evil'),
                   URL.replace('www.xiaohongshu.com', 'user@www.xiaohongshu.com'),
                   URL.replace(NID, ''), URL.split('?')[0], URL.replace('ABC==', ''),
                   URL + '&xsec_token=second', 'xhslink.cn/o/']
        result = self.capture('\n'.join(invalid))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads(result.stdout)['invalid_inputs'], 8)
        self.assertEqual(self.calls(), [])
        self.run_dir = self.base / 'webclip' / 'encoded-token'
        encoded = URL.replace('ABC==', 'ABC%3D%3D')
        result = self.capture(encoded)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls()[0][2], encoded)

    def test_invalid_urls_and_retired_commands_do_not_call_opencli(self):
        result = self.capture(NID + '\nhttps://evil.example/x\n' + URL.split('?')[0])
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)['invalid_inputs'], 3)
        self.assertEqual(self.calls(), [])
        for command in ('enrich', 'doctor', 'capture --transcribe', 'capture --download-images'):
            self.assertEqual(self.cli(*command.split()).returncode, 2)


if __name__ == '__main__':
    unittest.main()
