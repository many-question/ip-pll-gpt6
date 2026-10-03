"""Widen unrun RT4 control probes after the measured baseline KVCO evidence."""
from pathlib import Path
import datetime,hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
target=H/'results/rt4_loading_protocol.json';p=json.loads(target.read_text())
assert p['status']=='prepared_not_run' and not (ROOT/'research/runs/spectre_cmos_v14_full'/p['run']).exists()
v=json.loads((H/'results/sampler_loading_validation.json').read_text())
rows={x['case']:x for x in v['cases'] if x['valid_for_diagnosis']}
low=rows['samplerload_track_vm_tt'];mid=rows['samplerload_track_tt']
kvco=(mid['rf_hz']-low['rf_hz'])/(mid['control_v']-low['control_v'])
assert 20e6<kvco<80e6
archive=H/'results/rt4_loading_protocol_initial.json';assert not archive.exists();archive.write_bytes(target.read_bytes())
original=list(p['cases']);nominal=original[0];body=(H/'tb/rt4load_nominal_tt.scs').read_text()
seed=(H/'state_inputs/rt4load_nominal_tt.ic').read_text();new=[nominal]
for name,delta in [('minus100m',-.1),('minus250m',-.25)]:
    case='rt4load_'+name+'_tt';control=nominal['control_v']+delta
    assert .2<control<1.0
    state=H/'state_inputs'/(case+'.ic');assert not state.exists()
    text,n=re.subn(r'^XP\.ctrl\s+.*$',f'XP.ctrl {control:.16g}',seed,flags=re.M);assert n==1
    state.write_text(text)
    tb,n=re.subn(r'^VCTRL .*$',f'VCTRL (XP.ctrl 0) vsource dc={control:.16g}',body,flags=re.M);assert n==1
    tb=tb.replace('rt4load_nominal_tt.ic',state.name);file=H/'tb'/(case+'.scs');assert not file.exists();file.write_text(tb)
    new.append(dict(case=case,control_v=control,delta_from_baseline_v=delta,tb_sha256=sha(file),seed_sha256=sha(state)))
p['cases']=new
p['span_revision']=dict(time=datetime.datetime.now().astimezone().isoformat(),
    superseded_protocol=archive.relative_to(ROOT).as_posix(),superseded_unrun_cases=[x['case'] for x in original[1:]],
    evidence=[dict(source=x['source_result'],sha256=x['source_sha256']) for x in [low,mid]],
    baseline_one_sided_kvco_hz_per_v=float(kvco),
    rationale='Measured baseline statictracking secant~37MHz/V suggests the original50mV span changes frequency only~1.86MHz, smaller than the observed~8MHz RT4nearlock mismatch. Widen probes to100/250mV below nominal; this is experimental range selection, not extrapolated RT4 performance.',
    unchanged='Nominal A/B case, RT4 circuit, supply, load, duration, initial-state provenance, and in-range interpolation-only acceptance remain unchanged.')
target.write_text(json.dumps(p,indent=2)+'\n');print([x['control_v'] for x in new])
