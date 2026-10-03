"""Audit physical text-state drift and equivalent reset-counter NAND states.

Two endpoints separated by3us are compared at the same forcing phase. This
is not a one-period residual, and no assertion of PSS convergence is made.
The independent local-chain PSS supplies a check of identical reset-latch
cells, not a valid periodic state of the actualLC core.
"""
from pathlib import Path
import hashlib,json,re
import numpy as np
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def state(p):
    result={}
    for line in p.read_text().splitlines():
        if not line.strip() or line.startswith('#'):continue
        fields=line.split();key=fields[0];assert key not in result
        result[key]=dict(value=float(fields[1]),unit='A' if '#unit A' in line else 'V')
    return result
initial=H/'state_inputs/core_pulsetrip_supply_seed_tt.ic'
final=H/'state_inputs/core_pulsetrip_late_seed_tt.ic'
protocol=json.loads((H/'results/core_late_seed_protocol.json').read_text())
assert sha(final)==protocol['seed_sha256']
a,b=state(initial),state(final);assert a.keys()<=b.keys()
added=sorted(b.keys()-a.keys());assert set(added)=={'XP.VRT:p','XP.VRX:p','XP.VVCO:p'}
rows=[]
for k in a:
    assert a[k]['unit']==b[k]['unit']
    rows.append(dict(node=k,unit=a[k]['unit'],initial=a[k]['value'],final=b[k]['value'],delta=b[k]['value']-a[k]['value']))
volts=sorted([x for x in rows if x['unit']=='V'],key=lambda x:abs(x['delta']),reverse=True)
source=R/'rt4fineaudit01/chain_rt4_fine_edges_tt';record=json.loads((source/'result.json').read_text())
assert record['ok'] and record['remote_inputs_match'] and 'spectre completes with 0 errors' in (source/'spectre.out').read_text()
assert sha(source/'final.ic')==record['local_outputs_sha256']['final.ic']
core_record=json.loads((ROOT/protocol['source_result']).read_text())
shared=['cells.scs','digital_cells_v2.scs','fll_circuit.scs']
for name in shared:assert record['inputs_sha256'][name]==core_record['inputs_sha256'][name]
c=state(source/'final.ic');comparisons=[]
# tx_fll_counter is held reset and disabled in both TBs. For each physical
# tx_latch_r, its NAND inputs are latch x and resetb; output is local qb.
for i in range(14):
    for latch in ['XM','XS']:
        prefix=f'XCOUNT.XF{i}.XF.';local=prefix+latch+'.';node=local+'XN.x'
        pins=dict(a=local+'x',b=prefix+'resetb',y=local+'qb')
        values={pin:dict(core=b['XP.'+k]['value'],source=c[k]['value']) for pin,k in pins.items()}
        err=max(abs(v['core']-v['source']) for v in values.values())
        # These checks concern pin values at endpoints; the structural reset
        # guarantees logic behavior, but capacitive feedthrough remains possible.
        assert abs(values['b']['core'])<10e-6 and abs(values['b']['source'])<10e-6
        comparisons.append(dict(node='XP.'+node,core_v=b['XP.'+node]['value'],source_v=c[node]['value'],
            delta_to_source_v=c[node]['value']-b['XP.'+node]['value'],pins=values,pin_match_max_v=err,
            endpoint_pins_match=bool(err<10e-6)))
out=dict(scope=__doc__,initial_file=initial.relative_to(ROOT).as_posix(),initial_sha256=sha(initial),
    final_file=final.relative_to(ROOT).as_posix(),final_sha256=sha(final),
    endpoint_separation_us=3.,periods_of_250ns=12,state_entries=len(b),compared_entries=len(rows),voltage_entries=len(volts),
    current_entries=sum(v['unit']=='A' for v in b.values()),added_entries={k:b[k] for k in added},
    voltage_changes_over_1mv=sum(abs(x['delta'])>.001 for x in volts),
    largest_voltage_changes=volts[:40],all_entries=rows,
    reset_latch_comparison=dict(source=(source/'result.json').relative_to(ROOT).as_posix(),source_sha256=sha(source/'result.json'),
        shared_dependencies_sha256={name:record['inputs_sha256'][name] for name in shared},
        condition='TT27/1.2V, same MOS reset counter disabled and reset high; actualLC core baseline vs fresh-PSS RT4 local chain.',
        rows=comparisons,all_endpoint_pins_match=all(x['endpoint_pins_match'] for x in comparisons),
        max_endpoint_pin_difference_v=max(x['pin_match_max_v'] for x in comparisons)),
    interpretation='Stable external observer frequency does not establish stability of every internal voltage. Slow NAND-stack nodes are one initial-state concern; this does not prove the cause of shooting failure.',
    limitations=['Endpoint separation3us is not a one-period norm and does not give a unique settling time constant.',
        'Local-chain PSS operates with a different RF source and retimer. Only identical reset-latch cells with checked pins are compared; no fast-clock gate state is assumed transferable.',
        'Physical612 entries comprise601 voltages plus11 currents, including two inductor currents. TextIC does not preserve every simulator-private charge/history state.',
        'No state is changed by this analyzer. A constructed seed would require fresh transient and PSS verification.'],
    pss_convergence_proven=False,random_jitter_measured=False,main_dut_modified=False)
(H/'results/core_state_drift.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(state_entries=out['state_entries'],voltage_entries=len(volts),current_entries=out['current_entries'],
    largest=volts[:5],all_counter_pins_match=out['reset_latch_comparison']['all_endpoint_pins_match'],
    maximum_pin_difference_v=out['reset_latch_comparison']['max_endpoint_pin_difference_v']),indent=2))
