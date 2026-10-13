"""Browser startup behavior with Windows process/launcher seams isolated."""
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import xhs_feed as backend

TASKLIST = '/mnt/c/Windows/System32/tasklist.exe'
CHROME = '/mnt/c/Program Files/Google/Chrome/Application/chrome.exe'
URL = 'https://www.xiaohongshu.com/explore/0123456789abcdef01234567?xsec_token=ABC=='


def result(code=0, stdout='', stderr=''):
    return subprocess.CompletedProcess([], code, stdout, stderr)


class ChromeStartup(unittest.TestCase):
    def test_missing_bridge_opens_chrome_once_then_retries_after_connectivity(self):
        with patch.object(backend.subprocess, 'run', side_effect=[
                result(69, stderr='BROWSER_CONNECT'), result(stdout='INFO: No tasks'),
                result(stdout='[OK] Connectivity: connected in 0.1s\n'),
                result(stdout='[{"field":"title","value":"captured"}]')]) as run, \
                patch.object(backend.subprocess, 'Popen') as launch, \
                patch.object(Path, 'is_file', return_value=True):
            self.assertEqual(backend.opencli('note', URL), [{'field': 'title', 'value': 'captured'}])
        launch.assert_called_once_with([CHROME], stdin=subprocess.DEVNULL,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                      start_new_session=True)
        self.assertEqual(run.call_args_list[1].args[0],
                         [TASKLIST, '/FI', 'IMAGENAME eq chrome.exe', '/FO', 'CSV', '/NH'])
        self.assertEqual(run.call_args_list[2].args[0], ['opencli', 'doctor'])
        self.assertEqual(run.call_args_list[0], run.call_args_list[3])


    def test_running_chrome_does_not_launch_or_retry(self):
        with patch.object(backend.subprocess, 'run', side_effect=[
                result(69, stderr='BROWSER_CONNECT'), result(stdout='"chrome.exe","123"')]) as run, \
                patch.object(backend.subprocess, 'Popen') as launch:
            with self.assertRaises(backend.CallUser):
                backend.opencli('note', URL)
        launch.assert_not_called()
        self.assertEqual(run.call_count, 2)

    def test_auth_and_security_never_check_or_launch_chrome(self):
        for code, diagnostic in [(77, ''), (69, 'AUTH_REQUIRED BROWSER_CONNECT'),
                                 (1, 'SECURITY_BLOCK'), (1, '请登录')]:
            with self.subTest(code=code, diagnostic=diagnostic), \
                    patch.object(backend.subprocess, 'run', return_value=result(code, stderr=diagnostic)) as run, \
                    patch.object(backend.subprocess, 'Popen') as launch:
                with self.assertRaises(backend.CallUser):
                    backend.opencli('note', URL)
                run.assert_called_once()
                launch.assert_not_called()

    def test_launch_timeout_requires_actual_connectivity_not_exit_zero(self):
        with patch.object(backend.subprocess, 'run', side_effect=[
                result(69), result(stdout='INFO: No tasks'),
                result(stdout='[MISSING] Extension: not connected\n[FAIL] Connectivity: failed\n')]) as run, \
                patch.object(backend.subprocess, 'Popen') as launch, \
                patch.object(Path, 'is_file', return_value=True), \
                patch.object(backend.time, 'monotonic', side_effect=[0, 0, 20, 20]):
            with self.assertRaisesRegex(backend.CallUser, 'did not connect'):
                backend.opencli('note', URL)
        launch.assert_called_once()
        self.assertEqual(run.call_count, 3)

    def test_failed_retry_does_not_open_chrome_again(self):
        with patch.object(backend.subprocess, 'run', side_effect=[
                result(69), result(stdout='INFO: No tasks'),
                result(stdout='[OK] Connectivity: connected in 0.1s\n'), result(69)]) as run, \
                patch.object(backend.subprocess, 'Popen') as launch, \
                patch.object(Path, 'is_file', return_value=True):
            with self.assertRaises(backend.CallUser):
                backend.opencli('note', URL)
        launch.assert_called_once()
        self.assertEqual(run.call_count, 4)

    def test_missing_chrome_or_failed_process_check_does_not_launch(self):
        for tasks, available in [(result(stdout='INFO: No tasks'), False), (result(1), True)]:
            with self.subTest(available=available), \
                    patch.object(backend.subprocess, 'run', side_effect=[result(69), tasks]), \
                    patch.object(backend.subprocess, 'Popen') as launch, \
                    patch.object(Path, 'is_file', return_value=available):
                with self.assertRaises(backend.CallUser):
                    backend.opencli('note', URL)
                launch.assert_not_called()


if __name__ == '__main__':
    unittest.main()
