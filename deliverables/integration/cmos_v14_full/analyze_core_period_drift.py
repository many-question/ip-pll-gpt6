"""Measure successive transient-period mismatch without interpreting it as noise.

The source audit identifies either a completed/stopped run's initial transient
or an independently hash-verified stable snapshot from a still-running job.
This compares the last two 250 ns periods at identical forcing phases, not a
valid PSS solution. Unsaved internal states and eventual PSS convergence remain
outside this check.
"""
from pathlib import Path
from array import array
import argparse,hashlib,json,re
import numpy as np
from noise_utils import cross

H=Path(__file__).resolve().parent;ROOT=H.parents[3]
parser=argparse.ArgumentParser()
parser.add_argument('--run',default='coretripsupply01')
parser.add_argument('--case',default='core_pulsetrip_supply_noise_tt')
parser.add_argument('--audit',default='core_supply_trial_audit.json')
parser.add_argument('--output',default='core_period_drift.json')
parser.add_argument('--snapshot',help='Read an independently hash-verified initialization snapshot subdirectory instead of the runner raw directory')
args=parser.parse_args()
assert all(re.fullmatch(r'[A-Za-z0-9_]+',x) for x in [args.run,args.case])
assert all(Path(x).name==x and x.endswith('.json') for x in [args.audit,args.output])
j=ROOT/'research/runs/spectre_cmos_v14_full'/args.run/args.case
if args.snapshot:assert re.fullmatch(r'[A-Za-z0-9_]+',args.snapshot)
source=j/(args.snapshot or j.name+'.raw')/'pss.tran.pss'
audit=json.loads((H/'results'/args.audit).read_text())
cache=j/('tstab_'+args.snapshot+'_last_two_periods.npz' if args.snapshot else 'tstab_last_two_periods.npz')
period=250e-9
units={};in_trace=False
with source.open() as f:
    for line in f:
        if line.strip()=='TRACE':in_trace=True;continue
        if line.strip()=='VALUE':break
        if in_trace:
            m=re.fullmatch(r'"([^"]+)" "([VI])"\s*',line)
            assert m,line
            units[m[1]]=m[2]
with source.open('rb') as f:
    f.seek(max(0,source.stat().st_size-1024*1024))
    tail=f.read()
# A running simulator may retain its last PSF record in a user-space buffer.
# An unchanged on-disk hash does not establish a complete final sample.
tail_records=[]
for block in re.split(rb'(?m)^"time"\s+',tail)[1:]:
    lines=block.splitlines();stamp=float(lines[0])
    names={line.split()[0].strip(b'"').decode() for line in lines[1:] if line.startswith(b'"')}
    tail_records.append((stamp,sorted(set(units)-names)))
assert tail_records
incomplete_tail=[dict(time_s=t,missing_signals=missing) for t,missing in tail_records if missing]
if incomplete_tail:
    assert args.snapshot and len(incomplete_tail)==1 and tail_records[-1][1],incomplete_tail
complete_tail=[t for t,missing in tail_records if not missing]
assert complete_tail
end=complete_tail[-1]
start=end-2*period
if not cache.exists():
    cols={k:array('d') for k in ['time',*units]};record={};active=False;within=False;duplicates=0
    def flush():
        if not record:return
        assert set(cols)<=set(record),record.get('time')
        for k in cols:cols[k].append(record[k])
    digest=hashlib.sha256()
    with source.open('rb') as f:
        for rawline in f:
            digest.update(rawline)
            if not active:
                if rawline.strip()==b'VALUE':active=True
                continue
            if rawline.startswith(b'"time" '):
                flush();record={};t=float(rawline.split()[1]);within=t>=start-2e-12
                if within:record['time']=t
            elif within:
                z=rawline.split()
                if len(z)!=2:continue
                k=z[0].strip(b'"').decode()
                if k in cols:
                    if k in record:duplicates+=1
                    record[k]=float(z[1])
    if record and not set(cols)<=set(record):
        assert args.snapshot and record['time']>end and incomplete_tail
    else:flush()
    assert digest.hexdigest()==audit['raw_tstab']['sha256']
    data={k:np.asarray(v) for k,v in cols.items()}
    assert np.all(np.diff(data['time'])>0) and data['time'][0]<=start
    np.savez_compressed(cache,**data,source_sha256=digest.hexdigest(),duplicates=duplicates)
with np.load(cache) as z:data={k:z[k] for k in z.files}
assert str(data['source_sha256'])==audit['raw_tstab']['sha256']
t=data['time'];grid=np.linspace(start,start+period,250001)
rows=[]
for k,unit in units.items():
    y=data[k];a=np.interp(grid,t,y);b=np.interp(grid+period,t,y);delta=b-a
    edges1=cross(t,y);edges1=edges1[(edges1>=start)&(edges1<start+period)]
    edges2=cross(t,y);edges2=edges2[(edges2>=start+period)&(edges2<end)]
    row=dict(node=k,unit=unit,range=[float(min(a.min(),b.min())),float(max(a.max(),b.max()))],
        difference_mean=float(np.mean(delta)),difference_rms=float(np.sqrt(np.mean(delta**2))),
        difference_peak=float(max(abs(delta))),endpoint_difference=float(delta[-1]),
        first_period_edges=len(edges1),second_period_edges=len(edges2))
    if unit=='V' and len(edges1)==len(edges2) and len(edges1)>0:
        shifts=edges2-edges1-period
        row['matched_edge_shift_ps']=dict(mean=float(np.mean(shifts)*1e12),
            min=float(min(shifts)*1e12),max=float(max(shifts)*1e12),
            peak_to_peak=float(np.ptp(shifts)*1e12))
    rows.append(row)
out=dict(scope=__doc__,source=source.relative_to(ROOT).as_posix(),source_sha256=str(data['source_sha256']),
    intervals_us=[[start*1e6,(start+period)*1e6],[(start+period)*1e6,end*1e6]],
    comparison_grid_step_ps=1.,rows=rows,periodic_state_valid=False,random_jitter_measured=False,
    full_pll_acceptance=False,
    snapshot_incomplete_tail_records=incomplete_tail,
    last_complete_sample_s=end,
    limitations=['Linear interpolation at1ps is a deterministic trajectory diagnostic, not a femtosecond noise measurement.',
        'Only saved states are covered; absent internal device/charge states cannot be cleared.',
        'This is the saved initialization trajectory, not the later growing Newton corrections.'])
(H/'results'/args.output).write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(intervals_us=out['intervals_us'],largest_voltage_mismatches=sorted(
    [x for x in rows if x['unit']=='V'],key=lambda x:x['difference_peak'],reverse=True)[:8]),indent=2))
