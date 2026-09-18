"""Compare independent numerical refinements against accepted R2 endpoint runs."""
from analyze import *

def main():
    rows=[]
    for corner,k,code,run in [('ff',17,101,'precision_r2_ax'),('ss',41,6,'precision_r2_ss'),('tt',14,243,'precision_r2_ax')]:
        name=f'r2_{corner}_k{k}_c{code}'
        base=R/name/name;fine=R/run/f'precision_{corner}_k{k}'
        if not (fine/'result.json').exists():continue
        rec=json.loads((fine/'result.json').read_text())
        assert rec['ok'] and rec['remote_inputs_match']
        log=(fine/'spectre.out').read_text()
        assert re.search(r'maxstep\s*=\s*1 ps',log)
        assert re.search(r'spectre completes with 0 errors,',log[-3000:])
        windows=endpoint_windows((base/'inputs'/f'{name}.scs').read_text())
        b=[measure(base,w) for w in windows];f=[measure(fine,w) for w in windows]
        errors=[(y['f_ghz']-x['f_ghz'])*1e9 for x,y in zip(b,f)]
        target=k*24e6*b[0]['m']
        margin=min(target-min(x['f_ghz']*1e9 for x in f),max(x['f_ghz']*1e9 for x in f)-target)
        row=dict(corner=corner,k=k,code=code,baseline=b,refinement=f,frequency_change_hz=errors,
                 refined_margin_hz=margin,refined_solver='APS conservative' if corner=='ss' else 'Spectre X AX with maxstep override',
                 maximum_vco_power_change_mw=max(abs(y['vco_mw']-x['vco_mw']) for x,y in zip(b,f)),
                 pass_check=bool(all(x['divide_valid'] for x in b+f) and max(abs(x) for x in errors)<2e6 and margin>2e6))
        rows.append(row)
        print(corner,k,'frequency change MHz', [round(x/1e6,5) for x in errors], 'margin MHz',round(margin/1e6,5),'pass',row['pass_check'])
    (H/'results/precision_validation.json').write_text(json.dumps(dict(expected=3,completed=len(rows),all_pass=len(rows)==3 and all(x['pass_check'] for x in rows),cases=rows),indent=2)+'\n')

if __name__=='__main__':main()
