"""Build a controlled shooting-origin pair from the verified 8 us, 1 ps state."""
from pathlib import Path
import datetime, hashlib, json, re
from analyze import H, R

def main():
    job = R / 'settle_1ps/continue_1ps'
    r = json.loads((job/'result.json').read_text())
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert r['ok'] and r['remote_inputs_match']
    assert sha(job/'final.ic') == r['local_outputs_sha256']['final.ic']
    validation = json.loads((H/'results/state_roundtrip_check.json').read_text())
    assert validation['continue_1ps']['pass_state_equality']
    kept, removed = [], []
    for line in (job/'final.ic').read_text().splitlines():
        if line.startswith('# Number of equations'): continue
        key = line.split()[0] if line.split() else ''
        if key.startswith(('obs', 'XOBS')): removed.append(key)
        else: kept.append(line)
    assert len(removed) == 8
    state = H/'state_inputs/clamp_from_v7_1ps_8us.ic'
    assert not state.exists()
    state.write_text('\n'.join(kept)+'\n', encoding='utf-8', newline='\n')
    body = (H/'tb/mesh_1ps_plain.scs').read_text()
    for name, tstab in [('clamp8_edge_pss', '83.3333333333333n'),
                        ('clamp8_mid_pss', '100n'),
                        ('clamp8_allopts_pss', '100n')]:
        s = re.sub(r'^tran tran.*$',
            f'pss pss fund=24M harms=164 tstab={tstab} maxstep=1p method=traponly '
            f'errpreset=conservative maxperiods=20 skipdc=yes readic="{state.name}" '
            'writefinal="__FINAL_STATE__" saveinit=yes', body, flags=re.M)
        s += 'save out ref\n'
        dest = H/'tb'/f'{name}.scs'
        assert not dest.exists()
        dest.write_text(s, encoding='utf-8', newline='\n')
    record = dict(time=datetime.datetime.now().astimezone().isoformat(),
        source_job=job.relative_to(R).as_posix(), source_sha256=sha(job/'final.ic'),
        derived_sha256=sha(state), removed_observer_equations=removed,
        question='Does moving the shooting boundary away from the reference transition improve convergence?',
        source_phase='Cumulative8us=192 reference periods; four-us cold1ps plus four-us1ps continuation. Same source phase and enable/reset final values.',
        conditions='TT27,1.2V,Q5,code6,/4,full v6 clamped bank,quiet10 sampler,fast filter; maxstep1ps,reltol1e-5,traponly,20 shooting iterations. No circuit or tolerance relaxation.',
        changed='Edge versus mid: only tstab83.3333333333333ns versus100ns and unique output paths. Allopts duplicates mid but runs with bare -preset_override; record effective values to compare absolute tolerances. All include out/ref waveforms. Changing tstab also changes stabilization duration; origin-effect inference is conditional.',
        source_help='research/spectre_help/pss.txt: shooting boundary placement discussion, lines585-600. Installed Spectre help, not a claim of convergence.',
        criteria='Require solver success plus independent24MHz period,164 VCO/41 output/1 reference edges, dominant harmonics164/41, control0.2..1V, plausible swing and endpoint mismatch<1mV. Not fullPLL/noise/capture signoff.')
    (H/'results/warm8_origin_protocol.json').write_text(json.dumps(record,indent=2)+'\n')
    print('Prepared verified8us state and three shooting-origin/tolerance trials')

if __name__ == '__main__': main()
