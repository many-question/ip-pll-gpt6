"""Compare edge phases relative to RF (PSS time axes reset to zero)."""
import json
import numpy as np
from analyze import H,R,parse,cross
F=3936e6

def phase(e):return float(np.angle(np.mean(np.exp(2j*np.pi*F*e)))/(2*np.pi*F))
def delta(a,b):return float(np.angle(np.exp(2j*np.pi*F*(a-b)))/(2*np.pi*F))
def measure(d,transient=False):
 t=d['time'];m=t>=70e-9 if transient else np.ones(len(t),dtype=bool);t=t[m]
 sig={'rf':(d['vp'][m]-d['vn'][m],0),'data':(d['dp'][m]-d['dn'][m],0),'clock':(d['XRT.ckp'][m]-d['XRT.ckn'][m],0),'retimed':(d['XRT.qp'][m]-d['XRT.qn'][m],0),'out':(d['out'][m],.6)}
 ph={k:phase(cross(t,v,lev)) for k,(v,lev) in sig.items()}
 return {k:delta(a,ph['rf'])*1e12 for k,a in ph.items() if k!='rf'}
def main():
 v=json.loads((H/'results/validation.json').read_text());by={r['case']:r for r in v};base='cml2_s2_tt'
 with np.load(R/by[base]['run']/base/'waveforms.npz') as z:tr=measure({k:z[k] for k in z.files},True)
 rows=[]
 for name in ['noise_cml2_s2_coarse','noise_cml2_s2_fine']:
  if name not in by or not by[name].get('periodic',{}).get('pass_periodic'):continue
  ph=measure(parse(R/by[name]['run']/name/(name+'.raw')/'pss.td.pss'))
  rows.append(dict(case=name,rising_edge_relative_to_rf_ps=ph,periodic_minus_transient_ps={k:delta(a*1e-12,tr[k]*1e-12)*1e12 for k,a in ph.items()}))
 out=dict(scope='One selected two-stage original-polarity scale2 fixture. Edge phases relative to RF modulo one RF period; absolute divided output phase is not established by this comparison. Descriptive cross-check, not a new acceptance criterion.',transient_source=base,transient_rising_edge_relative_to_rf_ps=tr,cases=rows)
 if len(rows)==2:out['fine_minus_coarse_ps']={k:delta(rows[1]['rising_edge_relative_to_rf_ps'][k]*1e-12,a*1e-12)*1e12 for k,a in rows[0]['rising_edge_relative_to_rf_ps'].items()}
 (H/'results/orbit_comparison.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()
