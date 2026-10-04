"""Probe RF phase to CP baseband current with fresh PSS and four PAC points.

The external measured-waveform source gains an electrical phase port. One
volt on this port adds one RF radian to every harmonic's common phase.
The actual frontend and its DC operating point are otherwise unchanged.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,re

H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks/cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--round',type=int,choices=[1,2,3],default=2)
    choice=ap.add_mutually_exclusive_group();choice.add_argument('--reference-candidate',action='store_true')
    choice.add_argument('--cp-variant',choices=['fasttail','mid70']);args=ap.parse_args()
    assert args.reference_candidate or args.cp_variant or args.round==2,'Baseline transfer is fixed to validated round 2.'
    prefix=f'cp_{args.cp_variant}_phase_transfer_r{args.round}' if args.cp_variant else (
        f'reference_frontend_phase_transfer_r{args.round}' if args.reference_candidate else 'frontend_phase_transfer')
    proof=H/'results'/(f'cp_{args.cp_variant}_balance{args.round}_validation.json' if args.cp_variant else (
        f'reference_frontend_balance{args.round}_validation.json' if args.reference_candidate else 'frontend_local_gain2_validation.json'))
    v=json.loads(proof.read_text())
    assert all(v[k] for k in ['complete','periodic_all_passed','local_gain_verified','balanced_center_verified'])
    c=v['cases'][1];rp=ROOT/c['source_result'];assert sha(rp)==c['source_sha256']
    r=json.loads(rp.read_text());src=rp.parent/'inputs'/(c['case']+'.scs')
    old=B/'tank_replay_phase_v14.va';assert sha(old)==r['inputs_sha256'][old.name]
    name='tank_replay_pm_v14';va=B/(name+'.va')
    case=(f'reference_frontend_r{args.round}_phase_transfer_tt' if args.reference_candidate else
          (prefix+'_tt' if args.cp_variant else 'frontend_phase_transfer_r2_tt'))
    tb=H/'tb'/(case+'.scs');pp=H/'results'/(prefix+'_protocol.json')
    assert not any(x.exists() for x in [tb,pp])
    a=old.read_text().replace('tank_replay_phase_v14',name)
    a=a.replace('(vp,vn,vss);','(vp,vn,phi,vss);')
    a=a.replace('input vss;electrical vp,vn,vss;','input phi,vss;electrical vp,vn,phi,vss;')
    a=a.replace('phase_deg*`M_PI/180;','phase_deg*`M_PI/180+V(phi,vss);')
    restored=a.replace(name,'tank_replay_phase_v14').replace('(vp,vn,phi,vss);','(vp,vn,vss);')
    restored=restored.replace('input phi,vss;electrical vp,vn,phi,vss;','input vss;electrical vp,vn,vss;')
    assert restored.replace('+V(phi,vss);',';')==old.read_text()
    a=a.replace('// External measured-waveform replay only; not an internal VCO model.',
                '// External RF phase perturbation fixture: phi volts equals RF radians.')
    body=src.read_text().replace('tank_replay_phase_v14',name)
    body=body.replace('XRF (vp vn 0)','XRF (vp vn phi 0)')
    # Sources are zero during PSS; PAC magnitude is a linear normalization.
    body+='\nVPH (phi 0) vsource dc=0 pacmag=1 pacphase=0\nsave phi VPH:p\n'
    body+='pa pac values=[10k 100k 1M 10M] sidebands=[0] sweeptype=absolute freqaxis=in\n'
    assert 'readpss=' not in body and 'recover=' not in body and 'pnoise' not in body
    if va.exists():assert va.read_text()==a,'Existing external phase fixture differs; do not overwrite.'
    else:va.write_text(a,encoding='utf-8',newline='\n')
    tb.write_text(body,encoding='utf-8',newline='\n')
    deps={k:w for k,w in r['inputs_sha256'].items() if k!=src.name}
    del deps[old.name];deps[va.name]=sha(va)
    run=f'cp{args.cp_variant}pac0{args.round}' if args.cp_variant else (
        f'referencefrontpac0{args.round}' if args.reference_candidate else 'frontendpac01')
    p=dict(scope=__doc__,run=run,case=case,time=datetime.datetime.now().astimezone().isoformat(),
           source_validation=proof.name,source_validation_sha256=sha(proof),source_result=c['source_result'],source_sha256=sha(rp),
           source_tb_sha256=sha(src),source_va_sha256=sha(old),phase_deg=c['phase_deg'],
           signed_static_gain_a_per_rf_rad=v['signed_gain_a_per_rf_rad'],condition=v['condition'],
           control_clamp_v=v['control_clamp_v'],tb_sha256=sha(tb),dependencies_sha256=deps,
           offsets_hz=[1e4,1e5,1e6,1e7],phase_port_scale_rf_rad_per_v=1,
           low_frequency_relative_complex_error_limit=.02,balanced_phase_limit_rad=.0005,
           launch_scope='One diagnostic slot, one thread, fresh PSS and four PAC points; 3600s guard. Candidate uses a long slot unless no other short diagnostic is active.',
           main_dut_modified=False,full_pll_acceptance=False,noise_measured=False,
           limitations=['RF source is noiseless and zero impedance; actual LC loading/backaction is absent.',
                        'Baseband CP-current response is not full closed-loop PLL phase transfer.',
                        'PAC is a derivative about the measured periodic orbit, not finite one-radian modulation.',
                        'Four points locate dynamic effects; no full-band integration or PVT qualification.',
                        'Only external RF stimulus changes; static gain must agree at10kHz within2% complex error.'])
    pp.write_text(json.dumps(p,indent=2)+'\n');print(json.dumps(dict(run=p['run'],case=case),indent=2))

if __name__=='__main__':main()
