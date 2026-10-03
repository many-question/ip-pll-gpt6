"""Compare the single-change CF40pF VCO candidate with the fine six-point source.

Actual fresh-PSS device noise, fixedM4/static-reference fixture. Six points
are never integrated as a free-running or PLL jitter result.
"""
from pathlib import Path
import hashlib,json,re,argparse
import numpy as np
from noise_utils import parse,devices

H=Path(__file__).resolve().parent;ROOT=H.parents[3]
R=ROOT/'research/runs/spectre_cmos_v14_full'
parser=argparse.ArgumentParser()
parser.add_argument('--variant',choices=['cf40','tail2'],default='cf40')
args=parser.parse_args()
candidate=R/('vcotail2_01/vco_bias_cf40_tail2_tt' if args.variant=='tail2' else 'vcocf40_01/vco_bias_cf40_tt')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def selected_components(p, names, total):
    """Read MOS thermal/flicker fields and verify their sum against device total."""
    text=p.read_text();types={}
    for typename,body in re.findall(r'"([^\"]+)" STRUCT\((.*?)\) PROP\(',text,re.S):
        fields=re.findall(r'^"([^\"]+)" FLOAT DOUBLE PROP\(',body,re.M)
        if 'total' in fields:types[typename]=fields
    traces=dict(re.findall(r'^"([^\"]+)" "([^\"]+)"$',text.split('\nTRACE\n',1)[1].split('\nVALUE\n',1)[0],re.M))
    arrays={name:[] for name in names}
    for name,body in re.findall(r'^"([^\"]+)" \(\n(.*?)\n\)',text.split('\nVALUE\n',1)[1],re.M|re.S):
        if name in arrays:arrays[name].append(np.fromstring(body,sep=' '))
    result={}
    for name,values in arrays.items():
        fields=types[traces[name]];a=np.asarray(values)
        assert a.shape==(len(total),len(fields))
        atotal=a[:,fields.index('total')]
        terms=a[:,[i for i,k in enumerate(fields) if k!='total']]
        err=float(max(abs(terms.sum(axis=1)/atotal-1)))
        assert err<1e-6
        result[name]=dict(component_sum_relative_error=err,
            fraction_of_output_psd={k:(a[:,fields.index(k)]/total).tolist() for k in ['id','fn','total']})
    return result
sources=([R/'vcocf40_01/vco_bias_cf40_tt'] if args.variant=='tail2' else
         [p.parent for p in R.glob('vconoise*/vco_noise_check6_tt/result.json')
          if json.loads(p.read_text()).get('ok')])
assert len(sources)==1,sources
baseline=sources[0]
if not (candidate/'result.json').exists():
    print('Candidate still running; no acceptance result written.');raise SystemExit(0)
rec=json.loads((candidate/'result.json').read_text())
if not rec.get('local_outputs_sha256'):
    print('Candidate collection incomplete; no result written.');raise SystemExit(0)

def read(j):
    r=json.loads((j/'result.json').read_text());log=(j/'spectre.out').read_text(errors='replace')
    assert r['ok'] and r['remote_inputs_match'] and 'spectre completes with 0 errors' in log
    assert not r.get('periodic_state'),'Use fresh PSS until MOS reuse discrepancy is resolved'
    raw=j/(j.name+'.raw');fd=parse(raw/'pss.fd.pss');td=parse(raw/'pss.td.pss');pn=parse(raw/'pn.pm.pnoise')
    f=pn['relative frequency'];assert len(f)==6
    assert np.allclose(f,[1e4,1e5,1e6,1e7,1e8,492e6],rtol=1e-8)
    t=td['time'];T=t[-1]-t[0];fc=float(fd['freq'][4]);peak=float(abs(fd['vp'][4]-fd['vn'][4]))
    numerical_peak=float(abs(2/T*np.trapezoid((td['vp']-td['vn'])*np.exp(-2j*np.pi*4*(t-t[0])/T),t)))
    h={k:int(round(fd['freq'][1+np.argmax(abs(fd[k][1:]))]/fd['freq'][1])) for k in ['vp','vn','clk','q1','data','out']}
    endpoint=max(float(abs(td[k][-1]-td[k][0])) for k in h)
    periodic=bool(h==dict(vp=4,vn=4,clk=4,q1=2,data=1,out=1) and abs(fc*T/4-1)<1e-8 and endpoint<1e-3)
    p=raw/'pn.pm.pnoise';dev=devices(p,len(f));total=pn['out']**2;carrier=peak**2/2
    err=float(max(abs(sum(dev.values())/total-1)))
    excluded=float(max(np.asarray(sum(v for k,v in dev.items() if not k.startswith('XV.')))/total))
    assert periodic and err<1e-6 and excluded<1e-8 and abs(numerical_peak/peak-1)<.002
    one=int(np.argmin(abs(f/1e6-1)))
    row=dict(run=j.parent.name,case=j.name,source_result=(j/'result.json').relative_to(ROOT).as_posix(),
        source_sha256=sha(j/'result.json'),pnoise_sha256=sha(p),pss_fresh=True,simulator_completed=True,
        frequency_hz=fc,rf_carrier_peak_v=peak,carrier_td_relative_error=numerical_peak/peak-1,
        dominant_harmonics=h,endpoint_max_v=endpoint,periodic_passed=periodic,offsets_hz=f.tolist(),
        ssb_pm_dbc_per_hz=(10*np.log10(total/carrier)).tolist(),
        device_sum_relative_error=err,excluded_noise_fraction=excluded,
        bias_resistor_ssb_pm_psd=(dev['XV.XL.RF']/carrier).tolist(),
        bias_resistor_fraction_1mhz=float(dev['XV.XL.RF'][one]/total[one]),
        selected_device_components=selected_components(p,['XV.XL.MT','XV.XL.MN0','XV.XL.MN1'],total),
        vco_supply_power_mw=float(-1.2*np.trapezoid(td['VVCO:p'],t)/T*1e3),
        nfilt_range_v=[float(min(td['XV.XL.nfilt'])),float(max(td['XV.XL.nfilt']))],
        top_contributors_at_1mhz=sorted([dict(device=k,fraction=float(v[one]/total[one]))
            for k,v in dev.items()],key=lambda x:-x['fraction'])[:12])
    return r,row

br,b=read(baseline);cr,c=read(candidate)
newcore,oldcore,newvco,oldvco=(('lc_core_cf40_tail2_v14','lc_core_cf40_v14','lc_vco_cf40_tail2_v14','lc_vco_cf40_v14')
    if args.variant=='tail2' else ('lc_core_cf40_v14','lc_core_physical_v14','lc_vco_cf40_v14','lc_vco_physical_v14'))
def canonical_tb(j):
    s=(j/'inputs'/(j.name+'.scs')).read_text().replace(newvco,oldvco)
    return re.sub(r'writefinal="[^"]+"','writefinal="STATE"',s)
assert canonical_tb(baseline)==canonical_tb(candidate),'Unexpected testbench/settings change'
rename={newcore+'.scs':oldcore+'.scs',newvco+'.scs':oldvco+'.scs'}
def deps(r,case):return {k:v for k,v in r['inputs_sha256'].items() if k!=case+'.scs' and k not in set(rename)|set(rename.values())}
assert deps(br,baseline.name)==deps(cr,candidate.name)
for new,old in rename.items():
    newtext=(candidate/'inputs'/new).read_text().replace(newcore,oldcore).replace(newvco,oldvco)
    if new.startswith('lc_core'):
        if args.variant=='cf40':
            assert newtext.count('CF (nfilt vss) capacitor c=40p')==1
            newtext=newtext.replace('CF (nfilt vss) capacitor c=40p','CF (nfilt vss) capacitor c=10p')
        else:
            oldmt='MT (tail nfilt vss vss) nch w=300u l=1u ad=300u*240n as=300u*240n pd=2*(300u+240n) ps=2*(300u+240n)'
            newmt='MT (tail nfilt vss vss) nch w=600u l=2u ad=600u*240n as=600u*240n pd=2*(600u+240n) ps=2*(600u+240n)'
            assert newtext.count(newmt)==1
            newtext=newtext.replace(newmt,oldmt)
    assert newtext==(baseline/'inputs'/old).read_text(),'Unexpected physical change: '+new
delta=np.array(c['ssb_pm_dbc_per_hz'])-b['ssb_pm_dbc_per_hz']
freqshift=c['frequency_hz']/b['frequency_hz']-1;ampshift=c['rf_carrier_peak_v']/b['rf_carrier_peak_v']-1
change=('Only MT W300um/L1um -> W600um/L2um and its diffusion geometry; CF40pF and other circuitry unchanged.'
        if args.variant=='tail2' else 'Only CF10pF->40pF; all other circuit/stimulus dependencies identical.')
out=dict(scope='Fresh-PSS six-offset VCO candidate comparison; no integrated or PLL jitter.',variant=args.variant,condition='TT27/1.2V/Q5RLC,coarse23/control0.679V,actualfixedM4/10fF,referenceDC0,onlyXVnoise;0.5ps/255sidebands.',
    physical_change_verified=change,
    baseline=b,candidate=c,ssb_pm_change_db=delta.tolist(),relative_rf_frequency_change=freqshift,
    relative_carrier_change=ampshift,bias_resistor_psd_ratio=(np.array(c['bias_resistor_ssb_pm_psd'])/b['bias_resistor_ssb_pm_psd']).tolist(),
    comparable_operating_point=bool(abs(freqshift)<.001 and abs(ampshift)<.01),
    main_dut_modified=False,full_pll_jitter_fs=None,full_pll_acceptance=False,
    remaining=['Actual bias power-up/settling;RC time constant10us->40us','Active sampling/fullprogrammable load','Closed-loop/PVT validation'],
    limitation='Six offsets do not establish an integrated free-running or PLL jitter. Near-carrier free-running linearized noise retains linewidth limitations.')
output='vco_tail_noise_validation.json' if args.variant=='tail2' else 'vco_bias_noise_validation.json'
(H/'results'/output).write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:out[k] for k in ['ssb_pm_change_db','relative_rf_frequency_change','relative_carrier_change','bias_resistor_psd_ratio','comparable_operating_point']},indent=2))
