from analyze import *
def main():
    rows=[]
    for revision,corner in [(r,c) for r in ['r1','r2'] for c in ['tt','ss','ff']]:
        stim=json.loads((H/'results'/('r2_dynamic_stimulus.json' if revision=='r2' else 'dynamic_stimulus.json')).read_text())
        p=(R/'r2_checks'/f'r2_dynamic_{corner}') if revision=='r2' else (R/'dynamic'/f'dynamic_{corner}')
        if not (p/'result.json').exists():continue
        points=[]
        for j,code in enumerate(stim['codes']):
            x=measure(p,(j*stim['stage_s']+stim['measure_after_s'],(j+1)*stim['stage_s']))
            points.append(dict(code=code,**x))
        checks=[]
        for i in range(1,len(points)):
            if points[i]['code']>points[i-1]['code']:
                checks.append(dict(from_code=points[i-1]['code'],to_code=points[i]['code'],frequency_step_hz=(points[i]['f_ghz']-points[i-1]['f_ghz'])*1e9))
        return_error=points[-2]['f_ghz']/points[0]['f_ghz']-1
        low_error=points[-1]['f_ghz']/points[-3]['f_ghz']-1
        row=dict(revision=revision,corner=corner,points=points,transitions=checks,monotonic_at_tested_transitions=all(c['frequency_step_hz']<0 for c in checks),return_zero_fraction=return_error,return_255_fraction=low_error,
                 pass_check=all(c['frequency_step_hz']<0 for c in checks) and abs(return_error)<.001 and abs(low_error)<.001 and all(p['diff_pp_v']>.1 for p in points))
        rows.append(row);print(revision,corner,'pass',row['pass_check'],'zero repeat',return_error,'255 repeat',low_error,'minimum swing',min(p['diff_pp_v'] for p in points))
    (H/'results/dynamic_validation.json').write_text(json.dumps(rows,indent=2)+'\n')
if __name__=='__main__':main()
