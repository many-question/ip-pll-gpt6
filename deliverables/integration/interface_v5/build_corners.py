"""Keep six established extreme working codes and apply the interface candidate."""
from pathlib import Path
import csv,json,argparse
from build_screen import interface
H=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=['both','quiet10'],default='both');args=ap.parse_args()
channel=list(csv.DictReader((H.parent/'vco_v4/results/channel_map.csv').open()))
conditions=[]
for corner,k in [('tt',14),('tt',41),('ss',14),('ss',41),('ff',14),('ff',41),('ff',17)]:
 row=next(r for r in channel if r['corner']==corner and int(r['K'])==k)
 old=f'r2_{corner}_k{k}_c{row["code"]}'
 prefix='corner' if args.variant=='both' else 'q10corner'
 name=f'{prefix}_{corner}_k{k}'
 s=interface((H.parent/'vco_v4/tb'/f'{old}.scs').read_text(),True,True)
 if args.variant=='quiet10':
  s=s.replace('resistor r=1Meg','resistor r=10k').replace(') tx_divider_bank_v5',') tx_divider_bank_v5 rb_input=50k rb_clock=50k cdec=10p')
 (H/'tb'/f'{name}.scs').write_text(s)
 conditions.append(dict(case=name,baseline=old,**row))
(H/'results'/('corner_conditions.json' if args.variant=='both' else 'q10corner_conditions.json')).write_text(json.dumps(conditions,indent=2)+'\n')
print(' '.join(x['case'] for x in conditions))
