from analyze import *

def main():
    rows=[]
    for f in sorted(R.glob('*/*/result.json')):
        p=f.parent;tb=(p/'inputs'/f'{p.name}.scs').read_text()
        if 'VC (ctrl 0) vsource type=pwl' not in tb:continue
        if not json.loads(f.read_text())['ok']:continue
        windows=endpoint_windows(tb);lo=measure(p,windows[0]);hi=measure(p,windows[1])
        code=sum(2**i for i in range(8) if f'VB{i} (b{i} 0) vsource dc=1.2' in tb)
        corner=re.search('section=(tt|ss|ff)',tb)[1]
        x=dict(run=p.parent.name,case=p.name,code=code,corner=corner,m=lo['m'],low=lo,high=hi,
               tuning_range_hz=[min(lo['f_ghz'],hi['f_ghz'])*1e9,max(lo['f_ghz'],hi['f_ghz'])*1e9],
               valid=lo['divide_valid'] and hi['divide_valid'])
        rows.append(x)
        print(x['run'],x['case'],[round(z/1e9,7) for z in x['tuning_range_hz']],x['valid'],[round(lo['diff_pp_v'],4),round(hi['diff_pp_v'],4)],round(hi['vco_mw'],4),round(hi['total_mw'],4))
    (H/'results/channel_endpoints.json').write_text(json.dumps(rows,indent=2)+'\n')
if __name__=='__main__':main()
