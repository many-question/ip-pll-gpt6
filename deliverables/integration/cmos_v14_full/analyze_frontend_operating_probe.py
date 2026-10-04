"""Read actual BSIM4 resistive currents, gm and headroom over the frontend period."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from analyze_frontend_gain import measurement
from noise_utils import parse,cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
normal=lambda s:re.sub(r'\b(writefinal|writepss)="[^"]+"',r'\1="STATE"',s).strip()

def main():
    pp=H/'results/frontend_operating_probe_protocol.json';p=json.loads(pp.read_text())
    proof=H/'results'/p['source_validation'];assert sha(proof)==p['source_validation_sha256']
    j=R/p['run']/p['case'];m=measurement(j,p['phase_deg'])
    if not m.get('completed'):print('Frontend intrinsic operating probe pending');return
    out=dict(scope=__doc__,condition=p['condition'],protocol_sha256=sha(pp),periodic=m,
             operating_data_valid=False,noise_measured=False,full_pll_acceptance=False,limitations=p['limitations'])
    if m.get('periodic_passed'):
        r=json.loads((j/'result.json').read_text());src=R/p['source_run']/p['source_case'];old=json.loads((src/'result.json').read_text())
        dep=lambda r,n:{k:v for k,v in r['inputs_sha256'].items() if k!=n+'.scs'}
        assert dep(r,j.name)==dep(old,src.name) and not r.get('periodic_state')
        body=(j/'inputs'/(j.name+'.scs')).read_text()
        extra='\n// Instrumentation only: resistive currents and charge are distinct from terminal currents.\nsave '+' '.join(p['extra_observations'])+'\n'
        assert body.count(extra)==1 and normal(body.replace(extra,''))==normal((src/'inputs'/(src.name+'.scs')).read_text())
        d=parse(j/(j.name+'.raw')/'pss.td.pss');missing=sorted(set(p['extra_observations'])-set(d));assert not missing,missing
        t=d['time'];T=t[-1]-t[0];mean=lambda a:float(np.trapezoid(a,t)/T)
        falls=cross(t,-d['XCP.gate'],-.6);assert len(falls)==1;age=(t-falls[0])%T
        off=d['XCP.gate']<=.6
        windows=dict(gate_high=~off,gate_low=off,early_off_0_to_250ps=off&(age<.25e-9),late_off_after5ns=off&(age>=5e-9))
        rows=[]
        for dev in p['devices']:
            data={param:d[dev+':'+param] for param in p['parameters']}
            assert all(len(x)==len(t) and np.all(np.isfinite(x)) for x in data.values())
            op=dict(device=dev,window={},whole_period_mean_resistive_id_a=mean(data['id']),
                    qd_endpoint_change_c=float(data['qd'][-1]-data['qd'][0]),
                    qjd_endpoint_change_c=float(data['qjd'][-1]-data['qjd'][0]))
            if dev+':d' in d:
                terminal=d[dev+':d'];op.update(whole_period_mean_terminal_d_a=mean(terminal),
                                             whole_period_current_difference_a=mean(terminal-data['id']))
                scale=max(abs(mean(terminal)),abs(mean(data['id'])))
                op['whole_period_resistive_terminal_consistent']=bool(abs(op['whole_period_current_difference_a'])<max(1e-10,scale*1e-3))
                difference=terminal-data['id'];norm=float(np.sqrt(mean(difference**2)))
                assert norm>0
                op['charge_derivative_diagnostics']={}
                for label,charge in [('qd',data['qd']),('qd_plus_qjd',data['qd']+data['qjd']),('qd_minus_qjd',data['qd']-data['qjd'])]:
                    derivative=np.gradient(charge,t,edge_order=2)
                    error=difference-derivative
                    op['charge_derivative_diagnostics'][label]=dict(relative_rms_error=float(np.sqrt(mean(error**2))/norm),
                        mean_absolute_error_a=mean(abs(error)),terminal_minus_resistive_rms_a=norm)
            for label,mask in windows.items():
                z=mask.astype(float);fraction=mean(z);assert fraction>0
                avg=lambda a:mean(a*z)/fraction
                regions=sorted(set(float(x) for x in data['region'][mask]));assert all(x in [0,1,2,3,4] for x in regions)
                row=dict(fraction=fraction,mean_id_a=avg(data['id']),mean_ids_a=avg(data['ids']),mean_gm_s=avg(data['gm']),
                         mean_vgs_v=avg(data['vgs']),mean_vth_v=avg(data['vth']),mean_vds_v=avg(data['vds']),mean_vdsat_v=avg(data['vdsat']),
                         signed_resistive_drain_charge_c=mean(data['id']*z)*T,
                         raw_region_time_fractions={str(int(x)):avg((data['region']==x).astype(float)) for x in regions},
                         abs_vgs_below_abs_vth_fraction=avg((abs(data['vgs'])<abs(data['vth'])).astype(float)),
                         reverse_mode_fraction=avg((data['reversed']>.5).astype(float)))
                if dev+':d' in d:
                    row.update(mean_terminal_d_a=avg(terminal),mean_terminal_minus_resistive_a=avg(terminal-data['id']))
                op['window'][label]=row
            rows.append(op)
        all_region_zero=all(np.all(d[dev+':region']==0) for dev in p['devices'])
        out.update(operating_data_valid=True,devices=rows,physical_observation_only_change_verified=True,
                   balanced=abs(m['mean_clamp_current_a'])/json.loads(proof.read_text())['kphi_magnitude_a_per_rf_rad']<.0005,
                   raw_region_all_zero=bool(all_region_zero),region_classification_accepted=False,
                   region_anomaly='Every saved region is zero, including conducting bias MB. Do not interpret these codes as off-state evidence.',
                   all_observed_whole_period_currents_consistent=all(x.get('whole_period_resistive_terminal_consistent',True) for x in rows))
        out['limitations']+=['Raw region values are preserved but not interpreted: all-zero reporting conflicts with nonzero MB conduction and gate-over-threshold waveforms.',
                            'Charge derivatives use finite differences on the accepted time grid; all three explicit charge conventions are reported, with no fitted scaling.']
    (H/'results/frontend_operating_probe_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
