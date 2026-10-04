"""Deterministic edge measurements for reference-loading diagnostics."""
import numpy as np
from noise_utils import cross

def interval_to_next(first,second,max_interval):
    first=np.asarray(first);second=np.asarray(second)
    i=np.searchsorted(second,first,side='right');valid=i<len(second)
    delta=second[i[valid]]-first[valid]
    return delta[(delta>0)&(delta<max_interval)]

def clock_metrics(t,y,supply=1.2,nominal_hz=24e6):
    rise=cross(t,y,supply/2);fall=cross(t,supply-y,supply/2)
    tr=interval_to_next(cross(t,y,.1*supply),cross(t,y,.9*supply),.25/nominal_hz)
    tf=interval_to_next(cross(t,supply-y,.1*supply),cross(t,supply-y,.9*supply),.25/nominal_hz)
    high=interval_to_next(rise,fall,1.1/nominal_hz)
    return dict(rising_edges=len(rise),falling_edges=len(fall),
        average_period_ns=float(np.mean(np.diff(rise))*1e9) if len(rise)>1 else None,
        mean_rise_10_90_ps=float(np.mean(tr)*1e12) if len(tr) else None,
        mean_fall_90_10_ps=float(np.mean(tf)*1e12) if len(tf) else None,
        mean_high_width_ns=float(np.mean(high)*1e9) if len(high) else None,
        measured_min_v=float(np.min(y)),measured_max_v=float(np.max(y)))

def loading_timing(t,d):
    ref=cross(t,d['ref']);buffered=cross(t,d['XP.refb']);pulse=cross(t,d['XP.pulse'])
    delay=interval_to_next(ref,buffered,5e-9);cpdelay=interval_to_next(buffered,pulse,10e-9)
    out=dict(reference_buffer=clock_metrics(t,d['XP.refb']),cp_pulse=clock_metrics(t,d['XP.pulse']),
        reference_to_buffer_mean_delay_ps=float(np.mean(delay)*1e12) if len(delay) else None,
        reference_buffer_to_cp_mean_delay_ps=float(np.mean(cpdelay)*1e12) if len(cpdelay) else None,
        scope='Noiseless transient edge shape/delay; not jitter. Windows can begin or end inside a pulse.')
    if 'XP.XS.refb' in d:out['sampler_inverted_reference']=clock_metrics(t,d['XP.XS.refb'])
    return out

def analytic_timing_control():
    period=1/24e6;tr=100e-12;tf=150e-12;width=20e-9
    t=np.arange(0,500e-9,3e-12);phase=np.mod(t-.5e-9,period)
    y=np.where(phase<tr,1.2*phase/tr,np.where(phase<tr+width,1.2,np.where(phase<tr+width+tf,1.2*(1-(phase-tr-width)/tf),0.)))
    m=clock_metrics(t,y)
    error=max(abs(m['mean_rise_10_90_ps']/80-1),abs(m['mean_fall_90_10_ps']/120-1),abs(m['average_period_ns']/(period*1e9)-1))
    return dict(expected_rise_ps=80,expected_fall_ps=120,recovered=m,max_relative_error=float(error),passed=bool(error<1e-9))
