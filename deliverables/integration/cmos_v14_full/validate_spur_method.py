"""Analytic AM/PM/one-sideband and pure-clock controls for spur measurement."""
from pathlib import Path
import json
import numpy as np
from scipy.special import jv
from spur_utils import line_metrics,project_lines
H=Path(__file__).resolve().parent
fund=4e6;fc=984e6;fm=24e6;T=1/fund;N=2**18
t=np.linspace(0,T,N+1);freq=np.arange(0,N//2+1)*fund
phase=2*np.pi*fc*t;mod=2*np.pi*fm*t;A=.4
fixtures=[
 ('pure_smooth_clock',.6+A*(np.sin(phase)+np.sin(3*phase)/3+np.sin(5*phase)/5),None),
 ('am',.6+A*(1+.001*np.cos(mod))*np.sin(phase),20*np.log10(.001/2)),
 ('pm',.6+A*np.sin(phase+.001*np.sin(mod)),20*np.log10(abs(jv(1,.001)/jv(0,.001)))),
 ('single_upper_sideband',.6+A*np.sin(phase)+A*.001*np.sin(phase+mod+.4),-60.)]
rows=[]
for name,y,expected in fixtures:
    # FFT excludes the repeated endpoint; quadrature includes both endpoints.
    fd=2*np.fft.rfft(y[:-1])/N
    metric=line_metrics(freq,fd,fc)
    fr=np.asarray([fc-fm,fc,fc+fm]);direct=project_lines(t,y,fr,fund)
    ix=np.rint(fr/fund).astype(int)
    err=float(max(abs(abs(direct)-abs(fd[ix]))/abs(fd[int(fc/fund)])))
    measured=metric['largest_line']['dbc']
    passed=measured<-180 if expected is None else abs(measured-expected)<1e-6
    rows.append(dict(fixture=name,expected_largest_line_dbc=expected,measured_largest_line_dbc=measured,
        largest_offset_hz=metric['largest_line']['offset_hz'],quadrature_vs_fft_carrier_normalized_error=err,
        passed=bool(passed and err<1e-10)))
try:project_lines(t*1.01,fixtures[0][1],[fc],fund)
except AssertionError:bad_window_rejected=True
else:bad_window_rejected=False
out=dict(scope=__doc__,method='Uniform coherent FFT independently checked by nonuniform-capable time quadrature and exact analytic sideband ratios.',
    cases=rows,noncoherent_window_rejected=bad_window_rejected,passed=all(x['passed'] for x in rows) and bad_window_rejected,
    full_pll_acceptance=False,requirement_band_status='Proposed10kHz-fout/2 single-sideband range awaiting user confirmation; fixture tests are independent of that decision.')
(H/'results/spur_method_validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
assert out['passed']
