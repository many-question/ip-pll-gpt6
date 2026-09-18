from pathlib import Path
import re
H=Path(__file__).resolve().parent

def main():
 base=(H.parent/'transistor_v2/tb/loop_s9_noise_output.scs').read_text()
 # S10 isolates replacement of pulse timing. The oscillator remains VA.
 base=base.replace('ahdl_include "sampler_interface.va"', 'include "digital_cells_v2.scs"\ninclude "cp_timing.scs"')
 base=base.replace('XSS (refb hp hn sample fll_sample pulse vdd 0) sampler_interface','XTIME (refb enable rst pulse vdd 0) tx_cp_timing')
 base=base.replace(' fll_sample','').replace(' sample','')
 for c,temp in [('tt',27),('ss',60),('ff',0)]:
  s=base.replace('section=tt\n',f'section={c}\n').replace('temp=27',f'temp={temp}')
  (H/'tb'/f'loop_s10_timing_{c}.scs').write_text(s)
 # S11 includes the physical bundled-data config and digital handoff supervisor.
 # Sensing ports stay low: this test does NOT assert or claim analog phase lock.
 s=base.replace('parameters vddval=1.2','include "pll_config.scs"\ninclude "pll_supervisor.scs"\nparameters vddval=1.2')
 s=s.replace('VEN (enable 0) vsource dc=1.2','VEN (fll_enable 0) vsource dc=1.2')
 s=s.replace('VRST (rst 0)', 'VRST (reset 0)')
 s=s.replace('XDIV (vp vn rst vdd 0 0 0 0 0 div','XDIV (vp vn rst s0 s1 s2 s3 s4 s5 div')
 extra='VAPPLY (apply 0) vsource type=pulse val0=0 val1=1.2 delay=60n rise=50p fall=50p width=300n period=100u\n'
 extra+='\n'.join(f'VK{i} (k{i} 0) vsource dc={1.2 if 41&(1<<i) else 0}' for i in range(6))+'\n'
 extra+='XCONFIG (refb reset apply '+' '.join(f'k{i}' for i in range(6))+' '+' '.join(f'ak{i}' for i in range(6))+' '+' '.join(f's{i}' for i in range(6))+' ready invalid rst vdd 0) tx_pll_config\n'
 extra+='XSUP (refb reset ready fll_enable 0 0 0 enable qualified restart fault vdd 0) tx_pll_supervisor\n'
 s=s.replace('CLOAD (out 0)',extra+'CLOAD (out 0)').replace('save cycle_ctrl','save ready invalid rst enable qualified restart fault cycle_ctrl')
 (H/'tb/loop_s11_control_tt.scs').write_text(s)
 # Matched device-noise comparison: actual MOS pulser replaces ideal source.
 s=(H.parent/'transistor_v2/tb/tb_joint_final_center.scs').read_text()
 s=re.sub(r'VG \(pulse 0\).*\n','include "digital_cells_v2.scs"\ninclude "cp_timing.scs"\nXT (ref vdd 0 pulse vdd 0) tx_cp_timing\n',s)
 for tag,deg in [('lo',-.02),('center',0),('hi',.02)]:
  t=s.replace('217.869884783412',str(217.869884783412+deg)).replace('397.869884783412',str(397.869884783412+deg))
  if tag!='center':t=re.sub(r'pn pnoise .*\n','',t)
  (H/'tb'/f'tb_joint_timing_{tag}.scs').write_text(t)
if __name__=='__main__':main()
