"""One-shot completion stage for a currently running reset experiment.

Wait for this specific runner's recovered final manifest, then analyze once.
Does not launch simulations, publish reports, or schedule recurring work.
"""
from pathlib import Path
import argparse,datetime,json,subprocess,sys,time
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
p=argparse.ArgumentParser();p.add_argument('run');p.add_argument('--case',required=True)
p.add_argument('--fine-window',type=int,required=True);p.add_argument('--timeout',type=int,default=46800)
a=p.parse_args();assert a.run.isalnum() and a.case.replace('_','').isalnum()
job=ROOT/'research/runs/spectre_cmos_v14_full'/a.run/a.case
assert (job/'inputs'/(a.case+'.scs')).exists()
status=job/'finalization.json';start=time.monotonic()
def save(state,**extra):
 status.write_text(json.dumps(dict(state=state,run=a.run,case=a.case,
     time=datetime.datetime.now().astimezone().isoformat(),**extra),indent=2)+'\n')
save('waiting_for_recovered_final_manifest')
while time.monotonic()-start<a.timeout:
 rp=job/'result.json'
 try:rec=json.loads(rp.read_text()) if rp.exists() else {}
 except json.JSONDecodeError:rec={}
 if rec.get('local_outputs_sha256'):
  assert rec['remote_inputs_match']
  log=(job/'spectre.out').read_text(errors='replace')
  if 'spectre completes with 0 errors' not in log:
   save('simulation_not_completed',note='No capture acceptance generated; inspect retained simulator diagnostics.')
   sys.exit(1)
  cmd=[sys.executable,str(H/'analyze_capture.py'),a.run,'--case',a.case,'--fine-window',str(a.fine_window)]
  cp=subprocess.run(cmd,capture_output=True,text=True)
  (job/'finalization_analysis.log').write_text(cp.stdout+cp.stderr)
  if cp.returncode:
   save('analysis_failed',returncode=cp.returncode);sys.exit(cp.returncode)
  output=H/'results'/('capture_'+a.run+'.json');d=json.loads(output.read_text())
  save('analyzed',capture_screen_passed=d['functional_capture_screen_passed'],
       result=output.relative_to(ROOT).as_posix(),stationarity=d['stationarity'],pre_handoff=d.get('pre_handoff'))
  print(status.read_text());sys.exit(0)
 time.sleep(30)
save('waiting_deadline_reached',note='Simulation is not stopped by this helper; inspect the runner.')
sys.exit(2)
