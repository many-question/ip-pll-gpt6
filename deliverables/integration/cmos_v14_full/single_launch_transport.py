"""Project-local SSH policy: never replay a command after an unknown outcome.

The installed bridge retries failed persistent-shell commands, including long
Spectre launches. A lost response does not imply that the remote child stopped.
Use one transport attempt and an atomic, permanent per-directory launch claim.
After a transport error inspect the existing remote process; use a NEW run ID
only after its outcome and ownership have been established. Do not remove claims.
"""
import os
import re
import shlex
import subprocess
from virtuoso_bridge.spectre.runner import SpectreSimulator, SSHRunner
from virtuoso_bridge.transport.ssh import CommandResult

REMOTE = '/home/jielu/TSMC180/MP/IP-PLL-GPT6/simulation/cmos_v14_full'


def claim_command(command):
    if 'SPID=$!' not in command and 'spectre.pid' not in command:
        # Fail closed if the bridge changes its launch syntax.
        if re.search(r'\bspectre\s+-64\b', command):
            raise ValueError('Unrecognized Spectre launch syntax; refusing unguarded launch')
        return command
    matches = re.findall(r'echo \$SPID > (' + re.escape(REMOTE) + r'/[a-f0-9]{8})/spectre\.pid; wait \$SPID', command)
    if len(matches) != 1 or 'SPID=$!' not in command:
        raise ValueError('Unexpected launch path or PID protocol')
    directory = matches[0]
    claim = shlex.quote(directory + '/.launch_claim')
    return ('if ! mkdir ' + claim + '; then\n'
            '  echo "PROJECT_LAUNCH_ALREADY_CLAIMED: inspect existing run; never replay" >&2\n'
            '  exit 73\nfi\n' + command + '\n'
            'project_rc=$?\nprintf "%s\\n" "$project_rc" > ' + claim + '/exit_code\n'
            'exit "$project_rc"\n')


class SingleAttemptSSHRunner(SSHRunner):
    def run_command(self, command, timeout=None):
        guarded = claim_command(command)
        # Bypass BOTH the persistent-shell retry and subprocess retry paths.
        argv = self._build_ssh_base() + ['sh', '-l']
        self._print_cmd(argv)
        self._print_cmd(['single-attempt', command])
        options = dict(creationflags=subprocess.CREATE_NO_WINDOW) if os.name == 'nt' else {}
        result = subprocess.run(argv, input=guarded.encode('utf-8'), capture_output=True,
                                timeout=timeout or self._timeout, **options)
        return CommandResult(result.returncode, result.stdout.decode('utf-8', errors='replace'),
                             result.stderr.decode('utf-8', errors='replace'))


class ProjectSpectreSimulator(SpectreSimulator):
    def _get_ssh_runner(self):
        if self._ssh_runner is None:
            self._ssh_runner = SingleAttemptSSHRunner(
                host=self._remote_host, user=self._remote_user,
                jump_host=self._jump_host, jump_user=self._jump_user,
                ssh_key_path=self._ssh_key_path, ssh_config_path=self._ssh_config_path,
                timeout=self._timeout, persistent_shell=False, verbose=True)
        return self._ssh_runner
