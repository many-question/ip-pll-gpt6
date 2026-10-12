"""Prepare matched original-V14 quiet trap/Gear runs with internal-node observations."""
from pathlib import Path
import datetime,hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    pp=H/'results/full_pll_main_bw320_pair_protocol.json';p=json.loads(pp.read_text())
    source=H/'tb'/(p['cases'][0]['case']+'.scs');assert sha(source)==p['cases'][0]['tb_sha256']
    body=source.read_text();assert 'param_vec=[0 0 1u 0]' in body and 'method=traponly' in body
    files={f.name:f for f in (H.parents[1]/'blocks').glob('*/*.scs')}
    assert all(sha(files[n])==v for n,v in p['physical_dependency_hashes'].items())
    assert sha(H/'state_inputs'/p['text_state'])==p['text_state_sha256']
    chain=[('pll_capture_v14.scs','pll_capture_v14','XC','pll_control_capture_v14'),
           ('pll_control_capture_v14.scs','pll_control_capture_v14','XF','tx_fll_best128_v14'),
           ('fll_best128_v14.scs','tx_fll_best128_v14','X57','tx_dff_r0'),
           ('digital_cells_v2.scs','tx_dff_r0','XS','tx_latch_r'),
           ('digital_cells_v2.scs','tx_latch_r','XN','pll_nand2')]
    proof=[]
    for filename,parent,instance,child in chain:
        text=files[filename].read_text();section=re.search(r'^subckt '+re.escape(parent)+r'\b.*?^ends '+re.escape(parent)+r'\b',text,re.M|re.S)[0]
        line=next(x for x in section.splitlines() if x.startswith(instance+' '))
        assert re.search(r'\)\s+'+re.escape(child)+r'(?:\s|$)',line)
        proof.append(dict(file=files[filename].relative_to(ROOT).as_posix(),sha256=sha(files[filename]),parent=parent,instance=instance,child=child,statement=line))
    leaf=files['cells.scs'].read_text();section=re.search(r'^subckt pll_nand2\b.*?^ends pll_nand2\b',leaf,re.M|re.S)[0]
    assert 'MN0 (y a x vss)' in section and 'MN1 (x b vss vss)' in section
    nodes=['XP.XC.XF.X57.XS.XN.x','XP.XC.XF.X57.XS.x','XP.XC.XF.X57.XS.qb',
           'XP.XC.XF.X57.qm','XP.XC.XF.X57.clkb','XP.XC.XF.X57.resetb','XP.XC.XF.n139','XP.XC.XF.n140']
    assert len(set(nodes))==len(nodes)
    cases=[]
    for label,method in [('trap','traponly'),('gear','gear2only')]:
        case='full_pll_main_ring_'+label+'_off_tt';dest=H/'tb'/(case+'.scs');assert not dest.exists()
        edited=body.replace('method=traponly','method='+method).rstrip()+' '+' '.join(nodes)+'\n'
        assert edited.replace(' '+' '.join(nodes)+'\n','\n').replace('method='+method,'method=traponly')==body
        dest.write_text(edited,encoding='utf-8',newline='\n')
        cases.append(dict(run='pllmainring'+label+'offssd01',case=case,noise_enabled=False,method=method,threads=4,tb_sha256=sha(dest)))
    p.update(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),cases=cases,parent_protocol_sha256=sha(pp),
        observations=p['observations']+nodes,extra_observations=nodes,hierarchy_proof=proof,leaf_cell_sha256=sha(files['cells.scs']),
        diagnostic_only=True,physical_dut_modified=False,full_pll_acceptance=False,
        comparison_parameter='Quiet integration method: traponly versus gear2only, with identical additional node saves.',
        deployment_rule='Both are noise-off diagnostics. No automatic noisy dispatch or candidate adoption.',
        purpose='Observe the unsaved NAND internal node implicated at 1.92753us in original320 quiet; compare propagation and output timing against method-matched controls.',
        quiet_gates=dict(minimum_reference_samples=23,phase_pp_rad_max=.02,abs_phase_drift_rad_per_us_max=.01,maximum_rf_cycles_error=.001,maximum_out_cycles_error=.001,initial_voltage_difference_v_max=1e-9),
        planned_analysis=['Verify actual terminal log/exit/END, raw hashes, all 27 saved initial voltages and whole final state.',
            'Retain all ringing diagnostics; added-save trap control must be compared with original320 quiet output timing before attributing method differences.',
            'Measure internal node extrema, adjacent-step alternation and coupled parent/output behavior around1.92753us and all reported events; a missing warning is not proof of no ringing.',
            'Use each method own quiet stationarity and output edge differences. Deterministic timing differences are not random jitter or an absolute numerical-error bound.'],
        limits=dict(max_requested_threads=18,max_long_jobs=4,max_short_jobs=1,requested_threads_per_case=4),
        expected_wall_hours_per_case=[4,8],wall_timeout_s=172800)
    p['limitations'] += ['Both new records keep isnoisy=0 throughout and cannot measure random jitter.','Additional saves and thread count can change solver scheduling; compare trap replay against retained prior quiet.','Observed internal ringing amplitude and method sensitivity do not by themselves select a physical truth or close noise convergence.']
    dest=H/'results/full_pll_main_ringing_diagnostic_protocol.json';assert not dest.exists();dest.write_text(json.dumps(p,indent=2)+'\n')
    print(json.dumps(dict(protocol=dest.relative_to(ROOT).as_posix(),cases=cases,nodes=nodes,hierarchy_verified=True),indent=2))

if __name__=='__main__':main()
