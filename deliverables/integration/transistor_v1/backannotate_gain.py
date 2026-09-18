"""Propagate measured deterministic gains into fixed-RC Python sensitivity.

Noise inputs remain hypotheses, so these are NOT transistor noise results.
"""
from pathlib import Path
from dataclasses import replace
import copy,json,sys
import numpy as np
from scipy.optimize import brentq
HERE=Path(__file__).resolve().parent
V1=HERE.parents[1]/'architecture/behavioral_v1'
sys.path.insert(0,str(V1))
from model import synthesize,grid,noise_kernels,integrate_points,continuous_open,sampled_matrices
ROOT=HERE.parents[3].parent
cfg=json.loads((V1/'results/candidate/candidate_B.json').read_text())
base=synthesize(cfg)
cases=[('B_hypothesis',.4,120e-6),('initial_sampler',.033619333768376204,120e-6),('stronger_driver_sampler',.12464823832840954,120e-6),('sampler_and_pulsed_gm',.12464823832840954,111.17679469224854e-6)]
out=[]
for name,slope,gm in cases:
    c=copy.deepcopy(cfg);c['noise']['detector_differential_slope_v_per_rad']=slope
    lp=replace(base,kpd=slope*gm*.05)
    f=grid(c);freq=brentq(lambda x:float(abs(continuous_open(lp,np.array([x]))[0]))-1,1e3,1e7)
    rows=integrate_points(c,f,noise_kernels(lp,c,f),freq)
    out.append({'case':name,'sampler_slope_v_rad':slope,'gm_s':gm,'average_kpd_a_rad':lp.kpd,
                'fixed_rc_ct_crossover_hz':freq,'sampled_radius':float(max(abs(np.linalg.eigvals(sampled_matrices(lp)[0])))),
                'worst_fixed_fs_under_old_noise_assumptions':max(r['total_fs'] for r in rows if r['window']=='10k_to_10M'),
                'worst_wide_fs_under_old_noise_assumptions':max(r['total_fs'] for r in rows if r['window']=='10k_to_fout_over_2')})
c['loop']['kpd_average_a_per_rad']=slope*gm*.05
proposal=synthesize(c)
rows=integrate_points(c,f,noise_kernels(proposal,c,f),1e6)
proposed={'status':'Unimplemented filter proposal; not adopted and not circuit verified.',
          'r_ohm':proposal.r,'c1_f':proposal.c1,'c2_f':proposal.c2,
          'worst_fixed_fs_under_old_noise_assumptions':max(r['total_fs'] for r in rows if r['window']=='10k_to_10M'),
          'worst_wide_fs_under_old_noise_assumptions':max(r['total_fs'] for r in rows if r['window']=='10k_to_fout_over_2')}
p=HERE/'results/gain_sensitivity.json';p.parent.mkdir(parents=True,exist_ok=True)
# Measured together at 3.936 GHz, 0.4 V differential peak, CP output 0.6 V.
# Only deterministic local gains are replaced; noise/Cs/Kvco stay hypothetical.
joint_slope=.096529879017982;joint_kpd=3.523579694371235e-7
cj=copy.deepcopy(cfg);cj['noise']['detector_differential_slope_v_per_rad']=joint_slope
lj=replace(base,kpd=joint_kpd);fj=grid(cj)
cross=brentq(lambda x:float(abs(continuous_open(lj,np.array([x]))[0]))-1,1e3,1e7)
jr=integrate_points(cj,fj,noise_kernels(lj,cj,fj),cross)
joint={'source_run':'joint02/tb_sampler_cp_fine','local_sampler_slope_v_rad':joint_slope,
       'local_kpd_a_rad':joint_kpd,'fixed_rc_ct_crossover_hz':cross,
       'worst_fixed_fs_under_old_noise_assumptions':max(r['total_fs'] for r in jr if r['window']=='10k_to_10M'),
       'worst_wide_fs_under_old_noise_assumptions':max(r['total_fs'] for r in jr if r['window']=='10k_to_fout_over_2'),
       'limitations':'Same-test deterministic local gain, but assumed noise, original Cs, fixed Kvco and different top-level CP output voltage. Not PDK jitter.'}
lc=replace(lj,r=100e3)
cc=brentq(lambda x:float(abs(continuous_open(lc,np.array([x]))[0]))-1,1e3,1e7)
cr=integrate_points(cj,fj,noise_kernels(lc,cj,fj),cc)
compensated={'r_ohm':lc.r,'c1_f':lc.c1,'c2_f':lc.c2,'local_kpd_a_rad':joint_kpd,
             'ct_crossover_hz':cc,'sampled_radius':float(max(abs(np.linalg.eigvals(sampled_matrices(lc)[0])))),
             'worst_fixed_fs_under_old_noise_assumptions':max(r['total_fs'] for r in cr if r['window']=='10k_to_10M'),
             'worst_wide_fs_under_old_noise_assumptions':max(r['total_fs'] for r in cr if r['window']=='10k_to_fout_over_2'),
             'limitations':joint['limitations']+' R=100 kohm is the S7 functional damping candidate.'}
p.write_text(json.dumps({'warning':'Gain sensitivity only. Assumed VCO/reference/CP/retimer noise retained. Not PDK jitter verification. Kvco still 20 MHz/V hypothesis.',
                         'fixed_filter':{'r_ohm':base.r,'c1_f':base.c1,'c2_f':base.c2},'cases':out,'filter_proposal':proposed,'joint_gain_sensitivity':joint,'r100k_sensitivity':compensated},indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(proposed,indent=2))
print(json.dumps(joint,indent=2))
print(json.dumps(compensated,indent=2))
