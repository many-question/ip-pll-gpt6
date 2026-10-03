"""Deterministic coherent-line measurements; no random-jitter integration."""
import numpy as np

def line_metrics(f,voltage,carrier_hz,offset_min_hz=1e4,offset_max_hz=None):
    f=np.asarray(f);v=np.asarray(voltage)
    assert f.ndim==v.ndim==1 and len(f)==len(v) and np.all(np.diff(f)>0)
    assert np.all(np.isfinite(v)) and np.all(np.isfinite(f))
    i=int(np.argmin(abs(f-carrier_hz)))
    assert abs(f[i]/carrier_hz-1)<1e-10 and abs(v[i])>1e-12,'Missing/noncoherent carrier'
    upper=carrier_hz/2 if offset_max_hz is None else offset_max_hz
    offsets=f-carrier_hz
    mask=(abs(offsets)>=offset_min_hz)&(abs(offsets)<=upper*(1+1e-12))
    mask[i]=False
    rows=[]
    for k in np.flatnonzero(mask):
        ratio=abs(v[k])/abs(v[i])
        rows.append(dict(frequency_hz=float(f[k]),offset_hz=float(offsets[k]),amplitude_ratio=float(ratio),
                         dbc=float(20*np.log10(max(ratio,1e-300)))))
    assert rows
    return dict(carrier_hz=float(f[i]),carrier_amplitude_v=float(abs(v[i])),
                offset_band_hz=[float(offset_min_hz),float(upper)],lines=rows,
                largest_line=max(rows,key=lambda x:x['dbc']),
                normalization='20log10(abs(Vline)/abs(Vcarrier)); single spectral line, no sum of two sidebands.')

def project_lines(t,y,frequencies,fund_hz):
    """Independent nonuniform-time quadrature, using a complete coherent period."""
    t=np.asarray(t);y=np.asarray(y)
    assert t.shape==y.shape and len(t)>2 and np.all(np.diff(t)>0)
    period=t[-1]-t[0]
    assert abs(period*fund_hz-1)<1e-7,'Time window is not one declared fundamental period'
    tt=t-t[0]
    return np.asarray([2/period*np.trapezoid(y*np.exp(-2j*np.pi*fr*tt),tt) for fr in frequencies])
