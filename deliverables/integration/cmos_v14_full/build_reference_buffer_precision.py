"""Refine both reference-buffer noise spectra without changing physical inputs."""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
CHANGES={'harms=1023':'harms=2047','maxstep=1p':'maxstep=0.5p',
         'maxacfreq=96G':'maxacfreq=192G','maxsideband=1023':'maxsideband=2047'}

def main():
    proof=H/'results/reference_buffer_noise_validation.json';v=json.loads(proof.read_text())
    original=H/'results/reference_buffer_noise_protocol.json';p=json.loads(original.read_text())
    assert v['complete'] and v['noise_all_valid'] and v['protocol_sha256']==sha(original)
    target=H/'results/reference_buffer_precision_protocol.json';assert not target.exists()
    rows=[]
    for old,measured in zip(p['cases'],v['cases']):
        assert old['case']==measured['case']
        src=H/'tb'/(old['case']+'.scs');assert sha(src)==old['tb_sha256']
        rp=ROOT/measured['source_result'];assert sha(rp)==measured['source_sha256']
        body=src.read_text()
        for before,after in CHANGES.items():
            assert body.count(before)==1;body=body.replace(before,after)
        case='reference_buffer_'+old['variant']+'_refined_tt';tb=H/'tb'/(case+'.scs')
        assert not tb.exists();tb.write_text(body,encoding='utf-8',newline='\n')
        rows.append(dict(old,case=case,run='refbufferprecision01',tb_sha256=sha(tb),
                         source_case=old['case'],source_result=measured['source_result'],
                         source_sha256=measured['source_sha256']))
    out=dict(p,scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),cases=rows,
             baseline_validation=proof.name,baseline_validation_sha256=sha(proof),
             baseline_protocol_sha256=sha(original),numerical_changes=CHANGES,
             numerical_settings=dict(maxstep_ps=.5,maxacfreq_ghz=192,harms=2047,maxsideband=2047),
             precision_limits=dict(max_psd_change_db=.1,max_relative_rms_change=.01),
             launch_scope='Two serial one-thread eight-MOS diagnostics; fresh PSS each, 7200s per-case guard. Capacity must be checked before launch.')
    target.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(rows,indent=2))

if __name__=='__main__':main()
