"""Record the same-input APS comparison after launch; no circuit edit or state reuse."""
from pathlib import Path
import datetime, hashlib, json, re
H=Path(__file__).resolve().parent; ROOT=H.parents[3]
R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def canonical(text):
    return re.sub(r'\b(readic|writefinal|writepss|savefile)="[^"]+"',r'\1="RUN_LOCAL_PATH"',text)

def main():
    source=R/'coredacnoise01/core_dac_discharge_noise_tt'
    target=R/'coredacaps01/core_dac_discharge_noise_tt'
    a=json.loads((source/'result.json').read_text()); b=json.loads((target/'launch.json').read_text())
    assert a['remote_inputs_match'] and b['mode']=='aps' and b['threads']==6
    case=source.name; net=case+'.scs'
    assert {k:v for k,v in a['inputs_sha256'].items() if k!=net}=={k:v for k,v in b['inputs_sha256'].items() if k!=net}
    assert canonical((source/'inputs'/net).read_text())==canonical((target/'inputs'/net).read_text())
    seed=lambda r:sorted(x['sha256'] for x in r['initial_states'].values())
    assert seed(a)==seed(b) and not b['native_state'] and not b['periodic_state']
    pp=H/'results/core_dac_discharge_noise_protocol.json'; p=json.loads(pp.read_text())
    p.update(run='coredacaps01',status='running',time=datetime.datetime.now().astimezone().isoformat(),
        source_protocol_sha256=sha(pp),source_result=(source/'result.json').relative_to(ROOT).as_posix(),source_result_sha256=sha(source/'result.json'),
        predecessor_cancellation=json.loads((source/'cancellation.json').read_text()),
        predecessor_cancellation_sha256=sha(source/'cancellation.json'),
        command_change='Replace +preset=ax +mt=6 -preset_override with +aps +mt=6; netlist numerical options unchanged.',
        comparison_input_checks_passed=True,
        numerical_change='None in netlist. Compare actual logged numerical settings before interpreting engine comparison.',
        native_savefile='/home/jielu/TSMC180/MP/IP-PLL-GPT6/simulation/cmos_v14_full/coredacaps01_'+case+'.srf')
    p['limitations']+=['The predecessor was intentionally interrupted after five noncontracting Newton norms; wrapper crash classification is not evidence of a spontaneous solver failure.',
        'APS comparison is a numerical-method diagnostic. Neither a mode defect nor improved physical jitter is established by dispatch.']
    dest=H/'results/core_dac_aps_noise_protocol.json'; assert not dest.exists()
    dest.write_text(json.dumps(p,indent=2)+'\n')
    print(json.dumps(dict(protocol=dest.relative_to(ROOT).as_posix(),same_physical_inputs=True,same_text_seed=True,same_netlist_settings=True)))

if __name__=='__main__':main()
