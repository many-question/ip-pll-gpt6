"""Save BSIM4 intrinsic operating quantities to resolve CP terminal-current ambiguity."""
from pathlib import Path
import datetime,hashlib,json
from build_frontend_noise_probe import CP_OBSERVATIONS
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
DEVICES=['XCP.MB','XCP.MT','XCP.MIP','XCP.MIN','XCP.MPO','XCP.MPD']
PARAMETERS=['id','ids','gm','vgs','vds','vth','vdsat','region','reversed','qd','qjd']

def main():
    proof=H/'results/frontend_local_gain2_validation.json';v=json.loads(proof.read_text())
    assert v['complete'] and v['balanced_center_verified'] and v['local_gain_verified']
    snapshot=H/'results/frontend_off_windows_validation.json';s=json.loads(snapshot.read_text())
    assert s['partition_absolute_charge_error_c']<1e-24
    center=v['cases'][1];source=H/'tb'/(center['case']+'.scs');body=source.read_text()
    assert 'pnoise' not in body and 'readpss=' not in body
    extra=CP_OBSERVATIONS+[f'{dev}:{param}' for dev in DEVICES for param in PARAMETERS]
    body+='\n// Instrumentation only: resistive currents and charge are distinct from terminal currents.\nsave '+' '.join(extra)+'\n'
    case='frontend_operating_r2_tt';tb=H/'tb'/(case+'.scs');pp=H/'results/frontend_operating_probe_protocol.json'
    assert not tb.exists() and not pp.exists();tb.write_text(body,encoding='utf-8',newline='\n')
    p=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),run='frontendop01',case=case,
           source_validation=proof.name,source_validation_sha256=sha(proof),source_case=center['case'],source_run='frontendlocal02',
           source_tb_sha256=sha(source),tb_sha256=sha(tb),source_off_windows_sha256=sha(snapshot),
           phase_deg=center['phase_deg'],condition=v['condition'],extra_observations=extra,
           devices=DEVICES,parameters=PARAMETERS,
           help_sources={n:sha(ROOT/'research'/n) for n in ['spectre_bsim4_help.txt','spectre_save_help.txt']},
           parameter_meanings=dict(id='BSIM4 resistive drain current',ids='BSIM4 resistive drain-to-source current',
                                   qd='Total drain charge: intrinsic, overlap and fringing; charge completeness must be checked',qjd='Drain-bulk junction charge'),
           main_dut_modified=False,noise_measured=False,full_pll_acceptance=False,
           limitations=['FreshPSS at the existing measured balanced point; no circuit changes.',
                        'Operating quantities are diagnostics, not noise PSD; actual noise run continues separately.',
                        'Terminal-minus-resistive current interpretation needs measured whole-period and charge-balance checks.',
                        'Region is an estimated BSIM4 classification, not a substitute for voltage/headroom waveforms.'])
    pp.write_text(json.dumps(p,indent=2)+'\n');print(json.dumps(dict(run=p['run'],case=case,observations=len(extra)),indent=2))

if __name__=='__main__':main()
