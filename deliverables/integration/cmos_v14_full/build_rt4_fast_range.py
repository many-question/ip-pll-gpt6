"""Small TT AX screen requested by the user; physical RT4 baseline unchanged."""
from pathlib import Path
import csv, datetime, hashlib, json, re
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
P=H/'results/rt4_fast_range_protocol.json'
def main():
    assert not P.exists(),'Never overwrite an issued protocol'
    baseline=H/'results/rt4_adopted_baseline.json';b=json.loads(baseline.read_text())
    for x in b['dependencies']:assert sha(ROOT/x['path'])==x['sha256']
    plan={int(x['k']):x for x in csv.DictReader((ROOT/'share/deliverables/architecture/initial_screen/frequency_plan.csv').open())}
    rows=[];src=H/'tb/rt4bank_capture_tt.scs';original=src.read_text()
    for k in [14,41,9,10,12,19,28]:
        case=f'rt4_fast_k{k}_tt';run=f'rt4fastk{k}ssd01'
        s=original.replace('reltol=1e-4','reltol=1e-3').replace('maxstep=4p','maxstep=8p')
        s=re.sub(r' savetime=\[[^]]+\] savefile="[^"]+"','',s)
        for bit in range(6):s=re.sub(r'^VK'+str(bit)+r' .*$',f'VK{bit} (k{bit} 0) vsource dc={1.2 if (k>>bit)&1 else 0}',s,flags=re.M)
        assert 'readic=' not in s and 'recover=' not in s and '/home/jielu' not in s
        tb=H/'tb'/(case+'.scs');assert not tb.exists();tb.write_text(s,encoding='utf-8')
        rows.append(dict(kind='capture',run=run,case=case,k=k,m=int(plan[k]['m']),target_out_mhz=k*24,target_rf_mhz=int(plan[k]['fvco_hz'])/1e6,stop_s=64e-6,tb_sha256=sha(tb)))
    src_range=H/'tb/range_c255_v02_tt.scs';template=src_range.read_text().split('// TB-only isolated')[0]
    template=template.replace('cmos_even_bank_acq_v14','bank_pulsetrip_v14').replace('rt_light24s12_out083_v14','rt_noise_scale4_v14')
    template=template.replace('reltol=1e-5 vabstol=1e-7 iabstol=1e-13','reltol=1e-3 vabstol=1e-6 iabstol=1e-12').replace('maxstep=1p','maxstep=8p').replace('errpreset=conservative','errpreset=moderate')
    # Four corners of the coarse/fine rectangle, plus the binary carry 127->128 overlap.
    for code,v in [(255,.2),(0,1.),(255,1.),(0,.2),(127,.2),(128,1.)]:
        tag=f'c{code}_v{int(v*10):02d}';case='rt4_fast_range_'+tag;run='rt4range'+tag.replace('_','')+'ssd01'
        s=template
        for bit in range(8):s=re.sub(r'^VB'+str(bit)+r' .*$',f'VB{bit} (b{bit} 0) vsource dc={1.2 if (code>>bit)&1 else 0}',s,flags=re.M)
        s=re.sub(r'^VC .*$',f'VC (ctrl 0) vsource dc={v:g}',s,flags=re.M)
        # Use the selected RT4 divider/retimer with the same oscillator/sampler loading.
        m=14 if code==255 else 4
        select=['0']*6;select[[4,6,8,10,12,14].index(m)]='vdd'
        s=re.sub(r'^XD .*$',f"XD (clk div_reset {' '.join(select)} q1 data acqclk vdd 0) bank_pulsetrip_v14",s,flags=re.M)
        s=s.replace(') cp_physical_v14\n',') cp_physical_v14 bias_r=24000\n')
        tb=H/'tb'/(case+'.scs');assert not tb.exists();tb.write_text(s,encoding='utf-8')
        rows.append(dict(kind='tuning',run=run,case=case,coarse_code=code,control_v=v,m=m,stop_s=400e-9,output_start_s=340e-9,tb_sha256=sha(tb)))
    p=dict(time=datetime.datetime.now().astimezone().isoformat(),scope=__doc__,selected_baseline=dict(path=baseline.relative_to(ROOT).as_posix(),sha256=sha(baseline)),
           user_instruction='先跑全频点和调谐范围验证，适度调低精度，Spectre X AX，不要太多点，先快速得到整体结论。',
           mode='ax',preset_override='all',maxstep_s=8e-12,reltol=1e-3,vabstol=1e-6,iabstol=1e-12,method='traponly',noise=False,
           condition='TT27, 1.2V, 24MHz, 10fF, original selected RT4 physical dependencies including 4.4fF bank and Q5 RLC.',
           cases=rows,target_rf_range_mhz=[2688,3936],planned_channels=33,representative_capture_channels=7,
           capture_initialization='Independent reset/apply; supply already DC1.2V; 10uV differential seed only. No forced slow controls or near-lock state.',
           capture_screen=dict(window_s=1e-6,mean_frequency_relative_error_limit=.005,window_frequency_relative_spread_limit=.005,qualified_high_fraction_min=.99,frequency_good_high_fraction_min=.99,range_error_max_v=.2),
           tuning_scope='Loaded VCO + sampler/RF receiver/new divider/RT4; external coarse and fine voltage clamps; not closed-loop lock. Six points only, not all 256 codes.',
           capture_scope='One point per divider family plus RF/output maximum; K14 and K28 separately check 2.688GHz with M8 and M4. Other 26 channels unsimulated in this screen.',
           source_tb_sha256={src.name:sha(src),src_range.name:sha(src_range)},resource_cap=dict(threads=18,long_jobs=4,short_jobs=1),
           no_precision_or_seed_matrix=True,full_pll_jitter_acceptance=False)
    P.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(protocol=str(P),captures=7,tuning_points=6)))
if __name__=='__main__':main()
