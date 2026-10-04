"""Build one separate periodic-core candidate after complete counter verification.

The hypothesis is that reset stack drift impedes shooting. Clearing that
drift is not assumed to solve PSS, and no existing PLL is replaced here.
"""
from pathlib import Path
import datetime, hashlib, json, re

H = Path(__file__).resolve().parent
ROOT = H.parents[3]
B = H.parents[1] / 'blocks/cmos_v14_full'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    proof = H / 'results/reset_clear_counter_validation.json'
    if not proof.exists():
        print('Full counter verification pending; no core files generated')
        return
    v = json.loads(proof.read_text())
    if not (v['complete'] and v['passed']):
        print('Full counter verification not passed; no core files generated')
        return
    assert len(v['cases']) == 3
    assert all(len(c['count_checks']) == 30 and c['passed'] for c in v['cases'])
    counter_protocol = H / 'results/reset_clear_counter_protocol.json'
    cp = json.loads(counter_protocol.read_text())
    assert v['protocol_sha256'] == sha(counter_protocol)
    for c in v['cases']:
        assert sha(ROOT / c['source_result']) == c['source_sha256']
    for name in ['reset_clear_cells_v14.scs', 'fll_counter_reset_clear_v14.scs']:
        assert sha(B / name) == cp['dependencies_sha256'][name]
    source = H / 'results/core_dac_discharge_noise_protocol.json'
    p = json.loads(source.read_text())
    old_name = 'pll_noise_dacdischarge_core_v14'
    new_name = 'pll_noise_counterclear_core_v14'
    old = B / (old_name + '.scs')
    assert sha(old) == p['physical_dependencies_sha256'][old.name]
    body = old.read_text().replace(old_name, new_name)
    body = body.replace('include "fll_circuit.scs"',
                        'include "fll_circuit.scs"\ninclude "fll_counter_reset_clear_v14.scs"')
    body, count = re.subn(r'^(XCOUNT .*) tx_fll_counter$',
                         r'\1 fll_counter_reset_clear_v14', body, flags=re.M)
    assert count == 1
    restored = body.replace(new_name, old_name).replace('\ninclude "fll_counter_reset_clear_v14.scs"', '')
    restored = re.sub(r'^(XCOUNT .*) fll_counter_reset_clear_v14$', r'\1 tx_fll_counter', restored, flags=re.M)
    assert restored == old.read_text()
    run = 'corecounterclear01'
    case = 'core_counter_clear_noise_tt'
    block = B / (new_name + '.scs')
    tb = H / 'tb' / (case + '.scs')
    seed = H / 'state_inputs' / (case + '.ic')
    protocol = H / 'results/core_counter_clear_noise_protocol.json'
    assert not any(x.exists() for x in [block, tb, seed, protocol])
    old_seed = H / 'state_inputs' / p['initial_state_file']
    assert sha(old_seed) == p['seed_sha256']
    # Same node names and measured initial values; new device charge must settle.
    seed.write_bytes(old_seed.read_bytes())
    block.write_text(body, encoding='utf-8', newline='\n')
    body = (H / 'tb/core_dac_discharge_noise_tt.scs').read_text()
    body = body.replace(old_name, new_name).replace(p['initial_state_file'], seed.name)
    body = body.replace('maxperiods=10', 'maxperiods=6')
    save = '/home/jielu/TSMC180/MP/IP-PLL-GPT6/simulation/cmos_v14_full/' + run + '_' + case + '.srf'
    body = re.sub(r'savefile="[^"]+"', 'savefile="' + save + '"', body)
    existing = set(' '.join(re.findall(r'^save (.*)$', body, re.M)).split())
    stacks = [f'XP.XCOUNT.XF{i}.XF.X{s}.XN.x' for i in range(14) for s in ['M', 'S']]
    added = [n for n in stacks if n not in existing]
    body += '\n// Observe every reset stack; initialization is not accepted PSS.\nsave ' + ' '.join(added) + '\n'
    assert 'recover=' not in body and 'readpss=' not in body
    tb.write_text(body, encoding='utf-8', newline='\n')
    physical = dict(p['physical_dependencies_sha256'])
    del physical[old.name]
    for path in [block, B / 'fll_counter_reset_clear_v14.scs', B / 'reset_clear_cells_v14.scs']:
        physical[path.name] = sha(path)
    p.update(scope=__doc__, run=run, case=case, time=datetime.datetime.now().astimezone().isoformat(),
             source_protocol_sha256=sha(source), counter_validation_sha256=sha(proof),
             counter_protocol_sha256=sha(counter_protocol), tb_sha256=sha(tb), seed_sha256=sha(seed),
             initial_state_file=seed.name, native_savefile=save, physical_dependencies_sha256=physical,
             condition=p['condition'] + ' Only XCOUNT uses reset-stack isolation/discharge cells; 28 added MOS.',
             rationale='Test measured reset-stack drift hypothesis after 30 counter checks at TT27/SS60/FF0. Failure after removal weakens that hypothesis.',
             numerical_change='Same measured text seed, 2us stabilization, 1ps Gear2 and tolerances as DAC-discharge AX trial. Limit shooting to six iterations; add 22 stack observations.',
             added_stack_observations=added, main_dut_modified=False, full_pll_acceptance=False)
    p['timing']['maxperiods'] = 6
    p['limitations'] += [
        'Unit quiet-reset settling and counter function passed; running-clock stack peak below1mV did not pass.',
        'Gate order and reset discharge devices change physical parasitics and timing; this is a circuit candidate.',
        'Text seed contains measured voltages/currents only, not a transferred native or periodic charge state.',
        'No assumption that eliminating reset-stack drift establishes or repairs the cause of failed shooting.']
    protocol.write_text(json.dumps(p, indent=2) + '\n')
    print(json.dumps(dict(run=run, case=case, source_counter_passed=True), indent=2))


if __name__ == '__main__':
    main()
