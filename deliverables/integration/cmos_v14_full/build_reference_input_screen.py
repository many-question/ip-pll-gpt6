"""Prepare finite-driver transient sensitivity cases, without declaring input specs.

The human input-edge question is still open. The grid below is an explicit
engineering screening assumption: source 10-90% edges 10/100/1000 ps and
Thevenin resistance 0/50/500 ohm. No source noise or jitter is measured here.
"""
from pathlib import Path
import datetime,hashlib,json

H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks';ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    dest=H/'results/reference_input_screen_protocol.json';assert not dest.exists()
    source=H/'results/reference_buffer_noise_protocol.json';p=json.loads(source.read_text())
    proof=H/'results/reference_input_load_validation.json';load=json.loads(proof.read_text())
    header=(H/'tb/reference_buffer_baseline_tt.scs').read_text().split('VDD (')[0]
    assert 'simulatorOptions options' in header
    header=header.replace('include "cells.scs"','include "cells.scs"\ninclude "reference_buffer_taper2_v14.scs"')
    header+='VDD (vdd 0) vsource dc=1.2\n'
    T=1/24e6;rows=[];body=header;save=[]
    for i,(edge,r) in enumerate((e,r) for e in [10,100,1000] for r in [0,50,500]):
        for variant,subckt in [('baseline','tx_reference_buffer'),('taper2','reference_buffer_taper2_v14')]:
            tag=f'{variant}_{i}';src='src_'+tag;inp='in_'+tag;out='out_'+tag;inst='X_'+tag
            ramp=edge*1e-12/.8
            body+=f'V_{tag} ({src} 0) vsource type=pulse val0=0 val1=1.2 period={T:.17g} width={T/2-ramp:.17g} rise={ramp:.17g} fall={ramp:.17g} delay=1n\n'
            if r:body+=f'R_{tag} ({src} {inp}) resistor r={r}\n'
            else:inp=src
            body+=f'{inst} ({inp} {out} vdd 0) {subckt}\nC_{tag} ({out} 0) capacitor c=2p\n'
            traces=list(dict.fromkeys([src,inp,out,inst+'.a','V_'+tag+':p']))
            rows.append(dict(tag=tag,variant=variant,source_10_90_ps=edge,source_resistance_ohm=r,source_node=src,
                             input_node=inp,output_node=out,first_stage_node=inst+'.a',input_current='V_'+tag+':p'))
            save+=traces
    body+='save '+' '.join(save)+'\nsaveOptions options save=selected\n'
    numerical=dict(coarse='2p',fine='1p');cases=[]
    for kind,step in numerical.items():
        case=f'reference_input_screen_{kind}_tt';tb=H/'tb'/(case+'.scs');assert not tb.exists()
        text=body+f'tran tran stop=500n maxstep={step} method=gear2only errpreset=conservative skipstart=375n writefinal="__FINAL_STATE__"\n'
        tb.write_text(text,encoding='utf-8',newline='\n')
        cases.append(dict(case=case,run='refinputscreen01',precision=kind,tb_sha256=sha(tb),maxstep_ps=2 if kind=='coarse' else 1))
    dependencies={'cells.scs':sha(B/'transistor_v1/cells.scs'),'reference_buffer_taper2_v14.scs':sha(B/'cmos_v14_full/reference_buffer_taper2_v14.scs')}
    out=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),cases=cases,branches=rows,
             source_protocol_sha256=sha(source),input_load_validation_sha256=sha(proof),dependencies_sha256=dependencies,
             condition='TT27/1.2V/24MHz/2pF output load, 18 electrically separate source/buffer branches sharing an ideal supply.',
             input_requirements_confirmed=False,source_grid_is_screening_assumption=True,
             functional_gates=dict(expected_edges_each_polarity=3,output_low_max_v=.2,output_high_min_v=1.0),
             numerical_limits=dict(max_abs_delay_change_ps=1.,max_relative_transition_change=.01),
             measurement_window_s=[375e-9,500e-9],main_dut_modified=False,noise_measured=False,full_pll_acceptance=False,
             launch_scope='Two serial fresh transient runs, one thread, 900s guard per case. Launch only after an actual resource slot is free; not yet submitted.',
             limitations=['The Thevenin source is a deterministic driver approximation, not a transistor input driver.',
                          'No sampled RF/CP backaction at the output; the 2pF load is the established standalone diagnostic.',
                          'Passing output swing and edge checks does not validate jitter, PVT or supply/load sensitivity.'])
    dest.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(cases=cases,branches=len(rows),requirements_confirmed=False,launched=False),indent=2))

if __name__=='__main__':main()
