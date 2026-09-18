from analyze import *
def main():
    rows=[]
    for p in sorted(list((R/'startup_ac').glob('startup_*'))+list((R/'r2_checks').glob('r2_startup_*'))):
        if not (p/'result.json').exists():continue
        rec=json.loads((p/'result.json').read_text())
        if not rec['ok']:continue
        d={k.removeprefix('ac_'):v for k,v in load_data(p/'waveforms.npz').items()};f=d['freq'];v=d['vp']-d['vn'];y=1/v
        idx=np.flatnonzero(y.imag[:-1]*y.imag[1:]<0)
        assert len(idx)==1,(p,len(idx))
        i=idx[0];a=-y.imag[i]/(y.imag[i+1]-y.imag[i]);f0=f[i]+a*(f[i+1]-f[i])
        conduct=lambda z:float(z.real[i]+a*(z.real[i+1]-z.real[i]))
        ip=d['XV.XL.MN0:d']+d['XV.XL.MN1:g'];inn=d['XV.XL.MN1:d']+d['XV.XL.MN0:g']
        core=.5*(ip-inn)/v
        net=conduct(y);active=conduct(core);loss=conduct(y-core)
        row=dict(case=p.name,resonance_hz=float(f0),net_conductance_s=net,core_conductance_s=active,passive_conductance_s=loss,
                 startup_gain_ratio=-active/loss,linear_startup=bool(net<0))
        rows.append(row);print(row)
    (H/'results/startup_admittance.json').write_text(json.dumps(rows,indent=2)+'\n')
if __name__=='__main__':main()
