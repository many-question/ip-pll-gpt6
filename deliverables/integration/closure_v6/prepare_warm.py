"""Build driven LC PSS from a collected, hash-checked 4 us transient final state.

Only testbench observer equations are removed. Physical node/device states are
kept, and initial sources match the original sources at the restart phase.
The runner uploads and verifies the initial-state file before simulation.
"""
import argparse,hashlib,json,re
from pathlib import Path
from analyze import H,R

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=['base','clamp','base8'],required=True);args=ap.parse_args()
 v=args.variant
 run,case,total_us=('base_continue','loop_base_continue',8) if v=='base8' else (('baseline_strict' if v=='base' else 'clamp_strict'),f'loop_{v}_strict',4)
 job=R/run/case
 rec=json.loads((job/'result.json').read_text());assert rec['ok'] and rec.get('remote_inputs_match') and rec['state_file']['collected']
 src=job/'final.ic';assert sha(src)==rec['local_outputs_sha256']['final.ic']
 folder=H/'state_inputs';folder.mkdir(exist_ok=True)
 name='loop_base_8us.ic' if v=='base8' else f'loop_{v}_4us.ic';dest=folder/name;assert not dest.exists(),'Do not silently replace an experiment initial state'
 lines=src.read_text().splitlines();kept=[];removed=[]
 for line in lines:
  if line.startswith('# Number of equations'):continue
  key=line.split()[0] if line.split() else ''
  if key.startswith('obs') or key.startswith('XOBS'):
   removed.append(key);continue
  kept.append(line)
 dest.write_text('\n'.join(kept)+'\n',encoding='utf-8',newline='\n')
 s=(job/'inputs'/f'{case}.scs').read_text()
 assert 'stop=4u' in s # 4 us = exactly 96 reference periods, compatible source phase.
 s=re.sub(r'^ahdl_include "lc_loop_observer.va"\n|^XOBS .*\n|^ic .*\n','',s,flags=re.M)
 s=re.sub(r'^VE .*$', 'VE (en 0) vsource dc=1.2',s,flags=re.M)
 s=re.sub(r'^VRST .*$', 'VRST (rst 0) vsource dc=0',s,flags=re.M)
 s=re.sub(r'^tran tran.*$',f'pss pss fund=24M harms=164 tstab=100n maxstep=2p method=traponly errpreset=conservative maxperiods=20 skipdc=yes readic="{name}" writefinal="__FINAL_STATE__" saveinit=yes',s,flags=re.M)
 s=re.sub(r'^save obsphase.*$', 'save out ctrl vc1 hp hn sp sn pulse refb en VDD:p VVCO:p VO:p',s,flags=re.M)
 tb=H/'tb'/f'loop_{v}_warm_pss.scs';assert not tb.exists();tb.write_text(s,encoding='utf-8',newline='\n')
 provenance=dict(source_run=job.parent.name,source_case=job.name,source_state_sha256=sha(src),derived_state=name,derived_state_sha256=sha(dest),removed_observer_equations=removed,retained_physical_state=True,source_phase=f'{total_us} us / (1/24 MHz) = {total_us*24} complete reference cycles. Restart sources reference waveform unchanged, enable=1.2 V,reset=0 V.',scope='Warm-start fixed-code periodic operating-point search, not cold capture or stability proof. Circuit remains the corresponding strict transient variant. For base8, total time is 4us plus 4us state continuation.',testbench_sha256=sha(tb))
 (H/'results'/f'warm_{v}_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
 print('Prepared',tb.name,'removed observer equations:',len(removed))

if __name__=='__main__':main()
