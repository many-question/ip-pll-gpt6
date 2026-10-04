"""Remove nonfunctional VA instruments to test their effect on strict full-PLL solve."""
from pathlib import Path
import datetime,hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    source=H/'tb/full_pll_noise_settling_tt.scs';body=source.read_text()
    state=H/'state_inputs/rt4bank_cold64_warm.ic';text=state.read_text();removed=[];lines=[];probe=None
    observers={'energy_nj','power_mw','obsphase','obscycles','obsctrl','obsdivcycles'}
    for line in text.splitlines():
        fields=line.split();key=fields[0] if fields else ''
        if key=='XE:meter_flow':probe=float(fields[1])
        if key in observers|{'VAP:p','VRST:p'} or key.startswith(('XE:','XOBS:')):
            removed.append(line);continue
        if line.startswith('# Number of equations'):continue
        lines.append(line)
    assert probe is not None
    lines+=['# Only measurement-equation entries removed; physical DUT entries retained.','VMEAS:p\t%.17g   #unit A'%probe]
    name='rt4bank_cold64_no_observer.ic';dst=H/'state_inputs'/name;assert not dst.exists();dst.write_text('\n'.join(lines)+'\n')
    body=re.sub(r'^ahdl_include .*\n','',body,flags=re.M)
    body=re.sub(r'^XE .*$', 'VMEAS (vdd_source vdd) vsource dc=0',body,flags=re.M)
    body=re.sub(r'^XOBS .*\n','',body,flags=re.M)
    body=body.replace('stop=2u','stop=100n').replace('strobeoutput=strobeonly','strobeoutput=all').replace('rt4bank_cold64_warm.ic',name)
    body=re.sub(r'^(save .*)$',lambda m:' '.join(x for x in m[1].split() if x not in observers),body,flags=re.M)
    body=body.replace('iabstol=1e-15','iabstol=1e-15 diagnose=yes')
    case='full_pll_no_observer_tt';tb=H/'tb'/(case+'.scs');assert not tb.exists();tb.write_text(body)
    # Ensure the actual DUT/load/reference statements are identical.
    for prefix in ['XP (','CL (','VR (','VDD (']:
        assert next(s for s in body.splitlines() if s.startswith(prefix))==next(s for s in source.read_text().splitlines() if s.startswith(prefix))
    pp=H/'results/full_pll_no_observer_protocol.json';assert not pp.exists()
    p=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),run='pllnova01',case=case,
        source_tb_sha256=sha(source),tb_sha256=sha(tb),text_state=name,text_state_sha256=sha(dst),source_state_sha256=sha(state),
        removed_initialization_entries=removed,added_probe_current_a=probe,stop_s=100e-9,
        changes='Replace ideal VA0V supply meter with ideal0V Spectre source. Remove the two nonfunctional measurement modules and their output saves. Actual transistor PLL, ideal external reference, load, supply and strict tolerances are unchanged.',
        reason='Detailed strict noise-OFF trial identifies power_mw in2055of2086 printed failed solution updates in a partial log. Causality requires this observer-removal comparison.',
        numerical=dict(reltol=1e-6,vabstol=1e-9,iabstol=1e-15,method='traponly',maxstep_s=.5e-12),
        noise_enabled=False,physical_dut_modified=False,full_pll_acceptance=False,
        limitations=['100ns method test, not stationary fullPLL jitter.',
          'Text initialization is approximate hidden-state reconstruction; check physical node values at t0.',
          'Removing measurement outputs also changes numerical error scaling; repeat step/noise validation on the corrected testbench.',
          'No power claim is made from sparse current samples; previous integrated-power evidence retains its original precision/observer conditions.'])
    pp.write_text(json.dumps(p,indent=2)+'\n');print(json.dumps(dict(run=p['run'],case=case,protocol_sha256=sha(pp)),indent=2))

if __name__=='__main__':main()
