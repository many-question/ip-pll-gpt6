"""Integrate only high-offset isolated-VCO PM bands to guide the next noise work."""
from pathlib import Path
import hashlib,json
import numpy as np
from noise_utils import parse,devices
H=Path(__file__).resolve().parent;ROOT=H.parents[3];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
validation=H/'results/vco_noise_validation.json';v=json.loads(validation.read_text())
base=next(x for x in v['cases'] if x['case']=='vco_noise_coarse_tt');assert base['single_case_valid'] and v['precision']['passed']
rp=ROOT/Path(base['source_result']);r=json.loads(rp.read_text());j=rp.parent
assert r['ok'] and r['remote_inputs_match'] and not r.get('periodic_state')
assert 'spectre completes with 0 errors' in (j/'spectre.out').read_text()
assert {k:z for k,z in r['inputs_sha256'].items() if k!=j.name+'.scs'}==v['circuit_hashes']
tb=(j/'inputs'/(j.name+'.scs')).read_text();assert 'noiseout=[usb am pm]' in tb and 'relharmnum=4' in tb and 'noiseon_inst=[XV]' in tb
raw=j/(j.name+'.raw');npth=raw/'pn.pm.pnoise';pn=parse(npth);fd=parse(raw/'pss.fd.pss')
f=pn['relative frequency'];fc=float(fd['freq'][4]);peak=float(abs(fd['vp'][4]-fd['vn'][4]));carrier_power=peak**2/2
assert fc==base['frequency_hz'] and peak==base['rf_carrier_peak_v']
L=pn['out']**2/carrier_power;parts=devices(npth,len(f))
assert np.all(np.diff(f)>0) and np.all(np.isfinite(L)) and np.all(L>0)
assert max(abs(sum(parts.values())/(pn['out']**2)-1))<1e-7
assert max(abs(np.asarray(sum(x for n,x in parts.items() if not n.startswith('XV.')))))==0
with np.load(H/'results/vco_noise_spectra.npz') as z:
    assert np.array_equal(f,z['vco_noise_coarse_tt_f']) and np.allclose(L,z['vco_noise_coarse_tt_L'],rtol=1e-14,atol=0)
groups={}
for n,x in parts.items():
    if not n.startswith('XV.'):continue
    if '.XL.XP.' in n or '.XL.XN.' in n:g='inductor_RLC'
    elif '.XL.MN' in n:g='cross_coupled_core'
    elif '.XL.' in n:g='tail_and_bias'
    elif '.XBP.' in n or '.XBN.' in n:g='switched_cap_bank'
    else:g='other'
    groups[g]=groups.get(g,0)+x/carrier_power
upper=fc/8;assert f[0]<1e6<upper<f[-1]
scale=2/(2*np.pi*fc)**2
def linear_integral(s,lo,hi):
    grid=np.r_[lo,f[(f>lo)&(f<hi)],hi]
    return float(np.trapezoid(np.interp(grid,f,s),grid))
def power_integral(lo,hi):
    grid=np.r_[lo,f[(f>lo)&(f<hi)],hi];s=np.exp(np.interp(np.log(grid),np.log(f),np.log(L)))
    logr=np.log(grid[1:]/grid[:-1]);a=np.log(s[1:]/s[:-1])/logr;q=a+1
    area=np.empty(len(q));small=abs(q)<1e-10
    area[small]=s[:-1][small]*grid[:-1][small]*logr[small]
    area[~small]=s[:-1][~small]*grid[:-1][~small]*np.expm1(q[~small]*logr[~small])/q[~small]
    return float(sum(area))
def row(lo,hi):
    var=scale*linear_integral(L,lo,hi);other=scale*power_integral(lo,hi)
    gv={g:scale*linear_integral(s,lo,hi) for g,s in groups.items()};closure=abs(sum(gv.values())/var-1);assert closure<1e-10
    return dict(low_hz=lo,high_hz=hi,equivalent_timing_rms_fs=float(np.sqrt(var)*1e15),
        timing_variance_fs2=var*1e30,loglog_quadrature_rms_fs=float(np.sqrt(other)*1e15),
        quadrature_rms_difference_percent=float((np.sqrt(var/other)-1)*100),
        device_group_rms_fs={g:float(np.sqrt(x)*1e15) for g,x in gv.items()},
        device_group_variance_fraction={g:x/var for g,x in gv.items()},device_group_sum_relative_error=closure)
bands=[row(a,b) for a,b in zip([1e6,2e6,5e6,10e6,100e6],[2e6,5e6,10e6,100e6,upper])]
cumulative=[row(lo,upper) for lo in [1e6,2e6,5e6,10e6,100e6]]
top=[]
for n,s in parts.items():
    if not n.startswith('XV.'):continue
    variance=scale*linear_integral(s/carrier_power,1e6,upper)
    top.append(dict(device=n,equivalent_rms_fs=float(np.sqrt(variance)*1e15),variance_fraction=variance*1e30/cumulative[0]['timing_variance_fs2']))
top.sort(key=lambda x:x['variance_fraction'],reverse=True)
fraction=sum(x['timing_variance_fs2'] for x in bands[:3])/sum(x['timing_variance_fs2'] for x in bands)
out=dict(scope=__doc__,source_result=rp.relative_to(ROOT).as_posix(),source_result_sha256=sha(rp),raw_pm_psd_sha256=sha(npth),
    source_validation_sha256=sha(validation),condition=v['condition'],rf_hz=fc,actual_output_hz=fc/4,upper_offset_hz=upper,
    tool_estimated_linewidth_hz=base['tool_estimated_free_running_linewidth_hz'],minimum_offset_to_tool_linewidth_ratio=1e6/base['tool_estimated_free_running_linewidth_hz'],
    normalization='S_t=2*L_SSB/(2*pi*fRF)^2. ActualRFcarrier used; an ideal divider preserves time error, but no real divider or closed-loop noise transfer is inferred.',
    quadrature='Trapezoid on measured full-grid PSD with linear-in-frequency interpolation at band boundaries; independent piecewise power-law quadrature is a sensitivity check, not extra simulation convergence.',
    disjoint_bands=bands,cumulative_high_offset_bands=cumulative,top_devices_1mhz_to_upper=top[:15],variance_fraction_1_to_10mhz_within_1mhz_to_upper=float(fraction),
    actual_pll_noise_transfer_measured=False,full_pll_jitter_fs=None,full_pll_acceptance=False,
    interpretation='The isolated CF10 VCO has substantial1-10MHz PM noise. Measure actual closed-loop suppression and examine VCO thermal/bias contributions, as well as the digital chain. This is neither a PLL prediction nor an unavoidable PLL jitter floor.',
    limitations=['No10kHz-to-output/2 free-running or PLL totalRMS; offsets below1MHz are excluded, including the problematic close-in linewidth regime.',
        'Reference held DC0 with sampler tracking, coarse23/control.679V and original fixedM4 loading; differs from active24MHz sampling, RT4 and the repaired full bank.',
        'Only baseline CF10 dense95point spectrum is integrated. CF40 sixpoint data is not used for sparse numerical integration.',
        'Sixoffset fine check passed, but full-grid fine Spectre convergence is not closed.Quadrature agreement does not replace it.',
        'Actual loop bandwidth, peaking, sampler/CP/reference/control noise and inter-module coupling remain unmeasured in the complete PLL.'])
(H/'results/vco_high_offset_validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(cumulative=[{k:x[k] for k in ['low_hz','high_hz','equivalent_timing_rms_fs','quadrature_rms_difference_percent']} for x in cumulative],variance_fraction_1_to_10mhz=float(fraction),groups_1mhz_to_upper=cumulative[0]['device_group_variance_fraction']),indent=2))
