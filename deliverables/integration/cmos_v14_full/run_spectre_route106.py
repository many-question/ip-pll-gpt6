"""Project runner on the verified existing thu-xia alias; process-local routing only."""
from pathlib import Path
import os
import run_spectre_verified106 as runner
from single_launch_transport import SingleAttemptSSHRunner
from rt4_recheckstep_transport105 import verify_identity

class VerifiedRouteSimulator(runner.SpectreSimulator):
    def _get_ssh_runner(self):
        if self._ssh_runner is None:
            os.environ['VB_SSH_CONFIG']=str(Path.home()/'.ssh/config')
            self._ssh_runner=SingleAttemptSSHRunner(host='thu-xia',user=None,
                jump_host=None,timeout=self._timeout,persistent_shell=False,verbose=True)
            # The bridge reloads its .env inside the SSH constructor. Override
            # the instance after that reload; never edit the installed config.
            self._ssh_runner._ssh_config_path=Path.home()/'.ssh/config'
            assert self._ssh_runner._build_ssh_base()[-1]=='thu-xia'
        return self._ssh_runner

if __name__=='__main__':
    verify_identity()
    runner.SpectreSimulator=VerifiedRouteSimulator
    runner.main()
