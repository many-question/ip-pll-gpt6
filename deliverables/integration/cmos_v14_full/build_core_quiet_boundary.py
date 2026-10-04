"""Prepare one boundary-phase comparison from the recovered late-seed trajectory.

Only tstab changes. This translates the shooting interval, while leaving the
same physical seed, 250 ns period, device circuit and accuracy settings.
"""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
audit=json.loads((H/'results/core_late_trial_audit.json').read_text())
boundary=json.loads((H/'results/core_late_boundary_diagnosis.json').read_text())
assert not audit['periodic_state_valid'] and not audit['pnoise_ran'] and audit['cancellation']['stopped']
assert audit['raw_tstab']['sha256']==boundary['raw_source_sha256']
assert boundary['candidate_guarded_max_slope_v_per_s']<boundary['original_guarded_max_slope_v_per_s']/1.5
shift=boundary['candidate_offset_ps']*1e-12;assert 0<shift<250e-9
source=H/'tb/core_pulsetrip_late_noise_tt.scs';body=source.read_text()
assert body.count('tstab=1u ')==1 and 'readpss=' not in body
token=f'tstab={1e-6+shift:.15g} '
body=body.replace('tstab=1u ',token)
assert body.replace(token,'tstab=1u ')==source.read_text()
target=H/'tb/core_pulsetrip_quiet_noise_tt.scs';assert not target.exists();target.write_text(body)
out=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),status='prepared_not_run',
    run='coretripquiet01',case=target.stem,source_tb_sha256=sha(source),candidate_tb_sha256=sha(target),
    predecessor_result=audit['source_result'],predecessor_result_sha256=audit['source_sha256'],
    raw_basis_sha256=audit['raw_tstab']['sha256'],boundary_diagnosis_sha256=sha(H/'results/core_late_boundary_diagnosis.json'),
    changed_tstab_s=1e-6+shift,shooting_phase_shift_ps=boundary['candidate_offset_ps'],
    previous_guarded_max_logic_slew_v_per_s=boundary['original_guarded_max_slope_v_per_s'],
    selected_guarded_max_logic_slew_v_per_s=boundary['candidate_guarded_max_slope_v_per_s'],
    hypothesis='A boundary away from simultaneous digital switching may improve the Newton map. This does not establish that switching is the only cause; hidden states and slow modes remain.',
    evidence='Installed Spectre21.1 PSS help, research/spectre_help/pss.txt lines580-598; actual late-seed saved transient determines the phase.',
    launch_gate='Predecessor owned Spectre process must be stopped and raw data recovered. Reuse that six-thread long slot within18 requested threads,4long+1short.',
    acceptance='Same periodic/noise gates; six offsets are not RMS. No tolerance relaxation, PSS-period change, hand-edited dynamic state or main-DUT adoption.',
    main_dut_modified=False,full_pll_acceptance=False)
(H/'results/core_quiet_boundary_protocol.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
