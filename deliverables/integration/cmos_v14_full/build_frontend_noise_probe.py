"""Three-point fresh-PSS current-noise probe at a measured balanced frontend.

Generate only after the local gain and centre have actually passed. The
clamped output current PSD is module evidence, not closed-loop PLL jitter.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,re

H=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
GROUPS=dict(reference=['XREF'],sampler=['XS'],charge_pump=['XCP'],pulser=['XT'],bias=['XBM','RBP','RBN'],validity=['XDET'])
CP_OBSERVATIONS=['XCP.nb','XCP.ng','XCP.tail','XCP.mir','XCP.gate','XCP.gateb',
                 'XCP.MT:d','XCP.MIP:d','XCP.MIN:d','XCP.MPO:d','XCP.MPD:d']

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--round',type=int,choices=[1,2,3],required=True)
    ap.add_argument('--group',choices=['all']+list(GROUPS),default='all')
    ap.add_argument('--reference-candidate',action='store_true');a=ap.parse_args()
    prefix='reference_frontend_noise' if a.reference_candidate else 'frontend_noise'
    proof=H/'results'/(f'reference_frontend_balance{a.round}_validation.json' if a.reference_candidate else f'frontend_local_gain{a.round}_validation.json');v=json.loads(proof.read_text())
    assert v['complete'] and v['periodic_all_passed'] and v['local_gain_verified'] and v['balanced_center_verified']
    center=v['cases'][1];assert center['amplitude_good_fraction']>.999 and center['phase_good_fraction']>.999
    source=H/'tb'/(center['case']+'.scs');body=source.read_text();assert 'pnoise' not in body
    allproof=None
    if a.group!='all':
        allproof=H/'results'/f'{prefix}_r{a.round}_all_validation.json'
        allv=json.loads(allproof.read_text());assert allv['noise_valid'] and allv['balanced_center_verified']
        body,n=re.subn(r'^(simulatorOptions options .*)$',lambda m:m[0]+' noiseon_inst=['+' '.join(GROUPS[a.group])+'] noiseon_type=all',body,flags=re.M);assert n==1
    body+='\nsave '+' '.join(CP_OBSERVATIONS)+'\n'
    body+='\npn pnoise oprobe=VO values=[10k 1M 10M] maxsideband=4095 pnoisemethod=fullspectrum\n'
    case=f'{prefix}_r{a.round}_{a.group}_tt';dst=H/'tb'/(case+'.scs');assert not dst.exists()
    dst.write_text(body,encoding='utf-8',newline='\n')
    p=dict(scope=__doc__,run=f'referencefrontnoise{a.round}{a.group}' if a.reference_candidate else f'frontendnoise{a.round}{a.group}',case=case,group=a.group,phase_deg=center['phase_deg'],
           source_validation=proof.name,source_validation_sha256=sha(proof),source_case=center['case'],
           source_run=f'referencebalance0{a.round}' if a.reference_candidate else f'frontendlocal0{a.round}',source_tb_sha256=sha(source),tb_sha256=sha(dst),
           condition=v['condition'],control_clamp_v=v['control_clamp_v'],kphi_magnitude_a_per_rf_rad=v['kphi_magnitude_a_per_rf_rad'],
           noise_offsets_hz=[1e4,1e6,1e7],group_instances=GROUPS,balanced_phase_limit_rad=.0005,
           fresh_pss=True,extra_observations=CP_OBSERVATIONS,main_dut_modified=False,full_pll_acceptance=False,
           time=datetime.datetime.now().astimezone().isoformat(),
           limitations=v['limitations']+['Current-noise points use a noiseless control clamp. Frequency-dependent loop impedance and LC loading are excluded.',
           'Static Kphi supplies a low-frequency equivalent phase-noise estimate only, not an exact dynamic transfer.',
           'No integration of three isolated PSD points. Fresh isolated noise-on must be checked against the all-noise device contributions.'])
    if allproof is not None:p.update(all_noise_validation=allproof.name,all_noise_validation_sha256=sha(allproof))
    if a.reference_candidate:p['candidate_block_sha256']=v['candidate_block_sha256']
    pp=H/'results'/f'{prefix}_r{a.round}_{a.group}_protocol.json';assert not pp.exists()
    pp.write_text(json.dumps(p,indent=2)+'\n');print(json.dumps(dict(run=p['run'],case=case,phase_deg=center['phase_deg']),indent=2))

if __name__=='__main__':main()
