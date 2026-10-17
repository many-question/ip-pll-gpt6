"""Check saved K9/M14 configuration and reference-interval observer ratio."""
import numpy as np
def configuration_and_mode(t,d,p):
    def bits(pref,n):return sum((d[pref+str(i)]>.6).astype(np.int64)*(1<<i) for i in range(n))
    cm=t>=p['configuration_check_after_s']; active=bits('XP.XC.ak',6); select=bits('XP.s',6)
    config=dict(after_s=p['configuration_check_after_s'],active_k_values=np.unique(active[cm]).tolist(),select_values=np.unique(select[cm]).tolist(),ready_all_high=bool(np.all(d['cfg_ready'][cm]>.6)),invalid_max_V=float(np.max(d['XP.cfg_invalid'][cm])),divider_reset_max_V=float(np.max(d['XP.divider_reset'][cm])))
    config['matches_expected']=bool(np.all(active[cm]==9) and np.all(select[cm]==32) and config['ready_all_high'] and config['invalid_max_V']<.2 and config['divider_reset_max_V']<.2)
    updates=np.r_[False,(np.diff(d['obsphase'])!=0)|(np.diff(d['obscycles'])!=0)|(np.diff(d['obsdivcycles'])!=0)]
    om=(t>=t[-1]-1e-6)&updates;rf=d['obscycles'][om]*24;outf=d['obsdivcycles'][om]*24
    valid=outf>0;ratio=float(np.mean(rf[valid])/np.mean(outf[valid])) if np.any(valid) else None
    mode=dict(window_s=[float(t[-1]-1e-6),float(t[-1])],observer_updates=int(np.count_nonzero(om)),valid_updates=int(np.count_nonzero(valid)),rf_mean_MHz=float(np.mean(rf)) if len(rf) else None,output_mean_MHz=float(np.mean(outf)) if len(outf) else None,mean_rf_output_ratio=ratio,expected_output_divisor=14,acquisition_divisor=4,relative_mean_tolerance=p['observer_mean_ratio_relative_tolerance'])
    mode['ratio_screen_passed']=bool(np.all(valid) and len(outf)>0 and ratio is not None and abs(ratio/14-1)<=p['observer_mean_ratio_relative_tolerance'])
    return config,mode
