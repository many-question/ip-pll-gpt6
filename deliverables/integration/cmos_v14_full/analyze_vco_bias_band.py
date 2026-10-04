"""Compare dense fresh-PSS CF10/CF40 VCO spectra; integrate only offsets >=1 MHz."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from noise_utils import parse,devices

H=Path(__file__).resolve().parent;ROOT=H.parents[3]
R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def integral(f,s,lo,hi,powerlaw=False):
    assert f[0]<=lo<hi<=f[-1]
    x=np.r_[lo,f[(f>lo)&(f<hi)],hi]
    if not powerlaw:return float(np.trapezoid(np.interp(x,f,s),x))
    y=np.exp(np.interp(np.log(x),np.log(f),np.log(s)))
    lr=np.log(x[1:]/x[:-1]);q=np.log(y[1:]/y[:-1])/lr+1
    factor=np.empty(len(q));small=abs(q)<1e-10
    factor[small]=lr[small];factor[~small]=np.expm1(q[~small]*lr[~small])/q[~small]
    return float(np.sum(y[:-1]*x[:-1]*factor))

def canonical_tb(s):
    s=s.replace('lc_vco_cf40_v14','lc_vco_physical_v14')
    s=s.replace('values=[10k 100k 1M 10M 100M 492M]','start=10k stop=492M dec=20')
    s=re.sub(r'maxstep=\S+','maxstep=STEP',s)
    s=re.sub(r'\bharms=\S+','harms=HARMS',s)
    s=re.sub(r'maxsideband=\S+','maxsideband=SIDES',s)
    return re.sub(r'writefinal="[^"]+"','writefinal="STATE"',s)

def verify_physical(a,b):
    """Allow exactly CF10->CF40 and matching subckt renames, or identical circuits."""
    def dep(j):
        names=[p for p in (j/'inputs').iterdir() if p.name!=j.name+'.scs']
        out={}
        for p in names:
            name=p.name.replace('lc_core_cf40_v14','lc_core_physical_v14').replace('lc_vco_cf40_v14','lc_vco_physical_v14')
            s=p.read_text().replace('lc_core_cf40_v14','lc_core_physical_v14').replace('lc_vco_cf40_v14','lc_vco_physical_v14')
            if name=='lc_core_physical_v14.scs':
                assert s.count('CF (nfilt vss) capacitor c=')==1
                s=s.replace('CF (nfilt vss) capacitor c=40p','CF (nfilt vss) capacitor c=10p')
            out[name]=s
        return out
    assert dep(a)==dep(b),'Unexpected physical dependency change'
    assert canonical_tb((a/'inputs'/(a.name+'.scs')).read_text())==canonical_tb((b/'inputs'/(b.name+'.scs')).read_text())

def read(j,min_points=90,expected_span_hz=(1e4,492e6)):
    r=json.loads((j/'result.json').read_text());log=(j/'spectre.out').read_text()
    assert r['ok'] and r['remote_inputs_match'] and not r.get('periodic_state')
    assert 'spectre completes with 0 errors' in log and 'steady-state solution was achieved' in log
    assert all(sha(j/'inputs'/k)==v for k,v in r['inputs_sha256'].items())
    raw=j/(j.name+'.raw');fp=raw/'pn.pm.pnoise'
    pn=parse(fp);fd=parse(raw/'pss.fd.pss');td=parse(raw/'pss.td.pss')
    f=pn['relative frequency'];fc=float(fd['freq'][4]);t=td['time'];T=t[-1]-t[0]
    assert len(f)>=min_points and np.all(np.diff(f)>0)
    assert abs(f[0]/expected_span_hz[0]-1)<1e-8 and abs(f[-1]/expected_span_hz[1]-1)<1e-8
    peak=float(abs(fd['vp'][4]-fd['vn'][4]));cp=peak**2/2
    timepeak=float(abs(2/T*np.trapezoid((td['vp']-td['vn'])*np.exp(-2j*np.pi*4*(t-t[0])/T),t)))
    harmonics={k:int(round(fd['freq'][1+np.argmax(abs(fd[k][1:]))]/fd['freq'][1])) for k in ['vp','vn','clk','q1','data','out']}
    endpoint=max(float(abs(td[k][-1]-td[k][0])) for k in harmonics)
    assert harmonics==dict(vp=4,vn=4,clk=4,q1=2,data=1,out=1) and abs(fc*T/4-1)<1e-8 and endpoint<1e-3
    assert abs(timepeak/peak-1)<.002
    total=pn['out']**2;parts=devices(fp,len(f));L=total/cp
    assert np.all(np.isfinite(L)) and np.all(L>0)
    closure=float(max(abs(sum(parts.values())/total-1)))
    excluded=float(max(np.asarray(sum(v for k,v in parts.items() if not k.startswith('XV.')))/total))
    assert closure<1e-7 and excluded<1e-8
    groups={}
    for n,s in parts.items():
        if not n.startswith('XV.'):continue
        if '.XL.XP.' in n or '.XL.XN.' in n:g='inductor_RLC'
        elif '.XL.MN' in n:g='cross_coupled_core'
        elif '.XL.' in n:g='tail_and_bias'
        elif '.XBP.' in n or '.XBN.' in n:g='switched_cap_bank'
        else:g='other'
        groups[g]=groups.get(g,0)+s/cp
    row=dict(case=j.name,source_result=(j/'result.json').relative_to(ROOT).as_posix(),source_sha256=sha(j/'result.json'),
        raw_pm_sha256=sha(fp),fresh_pss=True,wrapper_errors=r['errors'],rf_hz=fc,rf_carrier_peak_v=peak,
        carrier_td_relative_error=timepeak/peak-1,dominant_harmonics=harmonics,endpoint_max_v=endpoint,
        device_sum_relative_error=closure,excluded_noise_fraction=excluded,offsets_hz=f.tolist(),
        ssb_pm_dbc_per_hz=(10*np.log10(L)).tolist(),periodic_passed=True)
    width=re.search(r'estimated line width of the oscillator is\s+([0-9.eE+-]+)\s*([kMG]?)Hz',log)
    if width:
        row['tool_estimated_linewidth_hz']=float(width[1])*{'':1,'k':1e3,'M':1e6,'G':1e9}[width[2]]
        row['minimum_integrated_offset_to_linewidth_ratio']=1e6/row['tool_estimated_linewidth_hz']
    return row,dict(f=f,L=L,groups=groups,parts={k:s/cp for k,s in parts.items() if k.startswith('XV.')})

def main():
    pp=H/'results/vco_bias_band_protocol.json';p=json.loads(pp.read_text());rows=[];spectra={};jobs={}
    for spec in p['cases']:
        j=R/p['run']/spec['case'];rp=j/'result.json'
        if not rp.exists() or not json.loads(rp.read_text()).get('local_outputs_sha256'):continue
        row,s=read(j);src=R/('vconoise02' if spec['variant']=='cf10_fine' else 'vcocf40_01')/spec['source_tb'].removesuffix('.scs')
        verify_physical(src,j)
        row.update(variant=spec['variant'],physical_source_verified=True)
        oldraw=src/(src.name+'.raw');oldpn=parse(oldraw/'pn.pm.pnoise');oldfd=parse(oldraw/'pss.fd.pss')
        oldL=oldpn['out']**2/(abs(oldfd['vp'][4]-oldfd['vn'][4])**2/2)
        ix=[int(np.argmin(abs(s['f']/f-1))) for f in oldpn['relative frequency']]
        assert np.allclose(s['f'][ix],oldpn['relative frequency'],rtol=1e-8,atol=0)
        row['six_point_source_comparison']=dict(source_result=(src/'result.json').relative_to(ROOT).as_posix(),
            source_result_sha256=sha(src/'result.json'),offsets_hz=oldpn['relative frequency'].tolist(),
            ssb_delta_db=(10*np.log10(s['L'][ix]/oldL)).tolist(),
            same_numerical_settings=spec['variant']!='cf40_finer')
        rows.append(row);spectra[spec['variant']]=s;jobs[spec['variant']]=j
    if not rows:print('No completed dense spectrum; no validation written.');return
    upper=min(x['rf_hz']/8 for x in rows)
    for row in rows:
        s=spectra[row['variant']];scale=2/(2*np.pi*row['rf_hz'])**2;bands=[]
        for lo in p['high_offset_integrals']['lower_bounds_hz']:
            v=scale*integral(s['f'],s['L'],lo,upper);vp=scale*integral(s['f'],s['L'],lo,upper,True)
            gv={g:scale*integral(s['f'],x,lo,upper) for g,x in s['groups'].items()}
            assert abs(sum(gv.values())/v-1)<1e-10
            bands.append(dict(lower_hz=lo,upper_hz=upper,timing_rms_fs=float(np.sqrt(v)*1e15),
                powerlaw_rms_fs=float(np.sqrt(vp)*1e15),group_variance_fraction={g:x/v for g,x in gv.items()}))
        row['cumulative_high_offset_bands']=bands
        row['variance_fraction_1_to_10mhz']=integral(s['f'],s['L'],1e6,1e7)/integral(s['f'],s['L'],1e6,upper)
        row['top_devices_1mhz_to_upper']=sorted([dict(device=n,timing_rms_fs=float(np.sqrt(scale*integral(s['f'],x,1e6,upper))*1e15)) for n,x in s['parts'].items()],key=lambda x:-x['timing_rms_fs'])[:12]
    out=dict(scope=__doc__,condition=p['condition'],protocol_sha256=sha(pp),complete=len(rows)==3,cases=rows,
        common_upper_offset_hz=upper,normalization='S_t=2 L_SSB/(2*pi*fRF)^2; RFcarrier/4 is fixture output, not PLL prediction.',
        full_pll_jitter_fs=None,full_pll_acceptance=False,main_dut_modified=False,limitations=p['limitations'])
    lookup={x['variant']:x for x in rows}
    if 'cf10_fine' in lookup:
        coarse=R/'vconoise01/vco_noise_coarse_tt';verify_physical(coarse,jobs['cf10_fine'])
        cr,cs=read(coarse);fs=spectra['cf10_fine']
        assert np.allclose(cs['f'],fs['f'],rtol=1e-12,atol=0),'Different sweep grid beyond ASCII roundoff'
        delta=10*np.log10(fs['L']/cs['L']);fr=lookup['cf10_fine']['rf_hz']/cr['rf_hz']-1
        hi=min(upper,cr['rf_hz']/8);rms=[]
        for lo in p['high_offset_integrals']['lower_bounds_hz']:
            v0=2*integral(cs['f'],cs['L'],lo,hi)/(2*np.pi*cr['rf_hz'])**2
            v1=2*integral(fs['f'],fs['L'],lo,hi)/(2*np.pi*lookup['cf10_fine']['rf_hz'])**2
            rms.append(float(np.sqrt(v1/v0)-1))
        lim=p['numerical_limits']
        out['baseline_full_grid_precision']=dict(coarse_source=cr['source_result'],coarse_source_sha256=cr['source_sha256'],
            fine_source=lookup['cf10_fine']['source_result'],fine_source_sha256=lookup['cf10_fine']['source_sha256'],
            common_upper_hz=hi,ssb_pm_change_db=delta.tolist(),max_absolute_psd_change_db=float(max(abs(delta))),
            frequency_grid_max_relative_difference=float(max(abs(fs['f']/cs['f']-1))),
            relative_rf_change=fr,relative_high_band_rms_changes=rms,
            passed=bool(max(abs(delta))<lim['max_phase_noise_delta_db'] and abs(fr)<lim['max_relative_rf_frequency_change'] and max(abs(x) for x in rms)<lim['max_high_band_rms_relative_change']))
    for label,a,b in [('candidate_comparison','cf10_fine','cf40_fine'),('precision','cf40_fine','cf40_finer')]:
        if a not in lookup or b not in lookup:continue
        verify_physical(jobs[a],jobs[b]);sa=spectra[a];sb=spectra[b]
        assert np.allclose(sa['f'],sb['f'],rtol=1e-12,atol=0),'Different sweep grid beyond ASCII roundoff'
        delta=10*np.log10(sb['L']/sa['L']);fr=lookup[b]['rf_hz']/lookup[a]['rf_hz']-1
        rms=[y['timing_rms_fs']/x['timing_rms_fs']-1 for x,y in zip(lookup[a]['cumulative_high_offset_bands'],lookup[b]['cumulative_high_offset_bands'])]
        out[label]=dict(ssb_pm_change_db=delta.tolist(),max_absolute_psd_change_db=float(max(abs(delta))),relative_rf_change=fr,relative_high_band_rms_changes=rms,
            frequency_grid_max_relative_difference=float(max(abs(sb['f']/sa['f']-1))))
        if label=='precision':
            lim=p['numerical_limits']
            out[label]['checks']=dict(phase_noise=bool(max(abs(delta))<lim['max_phase_noise_delta_db']),
                rf_frequency=bool(abs(fr)<lim['max_relative_rf_frequency_change']),
                high_band_rms=bool(max(abs(x) for x in rms)<lim['max_high_band_rms_relative_change']))
            out[label]['limits']=lim
            out[label]['passed']=all(out[label]['checks'].values())
    (H/'results/vco_bias_band_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(complete=out['complete'],cases=[dict(variant=x['variant'],rf_hz=x['rf_hz'],bands=x['cumulative_high_offset_bands']) for x in rows],precision=out.get('precision')),indent=2))

if __name__=='__main__':main()
