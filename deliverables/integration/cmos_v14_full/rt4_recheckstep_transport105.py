"""Verified existing-host SSH route for monitoring/recovering run104 only.

The former IPv6 jump route became unreachable after the original SSH session
reset. No SSH configuration or simulation input is changed by this module.
"""
import base64
import json
import subprocess

SSH = ['C:/Windows/System32/OpenSSH/ssh.exe', '-o', 'BatchMode=yes',
       '-o', 'ConnectTimeout=10', 'thu-xia']


def remote(code, timeout=60):
    encoded = base64.b64encode(code.encode()).decode()
    command = '/usr/bin/python -c "import base64;exec(base64.b64decode(\'' + encoded + '\'))"'
    return json.loads(subprocess.check_output(SSH + [command], timeout=timeout))


def verify_identity():
    identity = remote('import os,socket,pwd,json\nprint(json.dumps(dict('
                      'uid=os.getuid(),user=pwd.getpwuid(os.getuid()).pw_name,'
                      'hostname=socket.gethostname())))')
    assert identity == {'uid': 528, 'user': 'jielu', 'hostname': 'thu-xia'}, identity
    return identity
