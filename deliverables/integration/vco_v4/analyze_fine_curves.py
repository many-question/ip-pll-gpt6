"""Independent measurements of the loaded R2 fine-control curves."""
from analyze import *

def main():
    stim=json.loads((H/'results/fine_curve_stimulus.json').read_text());rows=[]
    for corner,k,code in stim['cases']:
        p=R/'r2_fine_curves'/f'fine_curve_{corner}_k{k}'
        if not (p/'result.json').exists():continue
        rec=json.loads((p/'result.json').read_text())
        assert rec['ok'] and rec['remote_inputs_match']
        points=[dict(control_v=v,**measure(p,(i*stim['stage_s']+stim['measure_after_s'],(i+1)*stim['stage_s']))) for i,v in enumerate(stim['control_v'])]
        slopes=[(b['f_ghz']-a['f_ghz'])*1e9/(b['control_v']-a['control_v']) for a,b in zip(points,points[1:])]
        row=dict(corner=corner,k=k,code=code,points=points,interval_kvco_hz_per_v=slopes,
                 pass_check=all(x>0 for x in slopes) and all(x['divide_valid'] for x in points))
        rows.append(row);print(corner,k,'Kvco MHz/V',[round(x/1e6,3) for x in slopes],'pass',row['pass_check'])
    (H/'results/fine_curve_validation.json').write_text(json.dumps(dict(expected=3,completed=len(rows),all_pass=len(rows)==3 and all(x['pass_check'] for x in rows),cases=rows),indent=2)+'\n')

if __name__=='__main__':main()
