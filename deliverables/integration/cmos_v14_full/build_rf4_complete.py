"""Build the programmable physical PLL and count RF/4 during acquisition.

Frequency watchdog still measures the final output. Clock mux changes only with
the shared counter reset and disabled. No functional behavioral block in DUT.
"""
from pathlib import Path
import collections,json,subprocess,sys
H=Path(__file__).resolve().parent;D=H.parents[1];B=D/'blocks/cmos_v14_full';ROOT=H.parents[3]
name='fll_controller_rf4_v14'
src=(B/'fll_controller_full_v14.v').read_text().replace('fll_controller_full_v14',name)
src=src.replace('// Internal acquisition-window choice:32 reference periods,0.75MHz output count quantum.',
 '// Acquisition counts RF/4 for32 reference periods:3MHz RF count quantum.')
src=src.replace("wire [13:0] target = {3'b0,target_k,5'b0};", """// Target = K*M*8. Explicit channel plan matches kickstart/02.
 wire [13:0] kext = {8'b0,target_k};
 wire [13:0] target = (target_k==9) ? ((kext<<6)+(kext<<5)+(kext<<4)) :
   (target_k<=11) ? ((kext<<6)+(kext<<5)) :
   (target_k<=13) ? ((kext<<6)+(kext<<4)) :
   (target_k<=18) ? (kext<<6) :
   (target_k<=27) ? ((kext<<5)+(kext<<4)) : (kext<<5);""")
(B/(name+'.v')).write_text(src)
out=B/(name+'_mapped.json')
cmd=f'read_verilog "{(B/(name+".v")).as_posix()}"; hierarchy -top {name}; proc; flatten; opt; techmap; opt; dffunmap; opt_clean; setundef -zero; opt_clean; write_json "{out.as_posix()}"'
p=subprocess.run([sys.executable,str(ROOT/'research/run_yosys.py'),'-p',cmd],capture_output=True,text=True)
(ROOT/'research/v14_rf4_synthesis.log').write_text(p.stdout+p.stderr)
if p.returncode:raise RuntimeError(p.stderr)
m=json.loads(out.read_text())['modules'][name];names={};ports=[]
for n,info in m['ports'].items():
 for i,bit in enumerate(info['bits']):
  label=n if len(info['bits'])==1 else f'{n}{i}';names[bit]=label;ports.append(label)
def node(bit):return {'0':'vss','1':'vdd'}.get(bit,names.get(bit,f'n{bit}'))
mapping={'$_AND_':('tx_and','ABY'),'$_OR_':('tx_or','ABY'),'$_NOT_':('pll_inv','AY'),'$_XOR_':('tx_xor','ABY'),'$_XNOR_':('tx_xnor','ABY'),'$_MUX_':('tx_mux','ABSY'),'$_DFF_PP0_':('tx_dff_r0','DCRQ'),'$_DFF_PP1_':('tx_dff_r1','DCRQ')}
s=['simulator lang=spectre','subckt tx_'+name+' ('+' '.join(ports)+' vdd vss)']
for i,(_,c) in enumerate(sorted(m['cells'].items())):
 sub,order=mapping[c['type']];nets=' '.join(node(c['connections'][k][0]) for k in order);s.append(f'X{i} ({nets} vdd vss) {sub}')
s.append('ends tx_'+name);(B/(name+'.scs')).write_text('\n'.join(s)+'\n')
(H/'results/control_rf4_mapping.json').write_text(json.dumps(dict(cells=len(m['cells']),types=dict(collections.Counter(c['type'] for c in m['cells'].values())),count_window_ref_periods=32,rf_resolution_hz=3e6),indent=2)+'\n')
verify=(H/'verify_fll_logic.py').read_text().replace('fll_controller_full_v14',name).replace(')/ratio',')/4').replace('ratio*24e6/32','4*24e6/32').replace('fll_logic_validation.json','fll_rf4_logic_validation.json')
(H/'verify_fll_rf4_logic.py').write_text(verify)
bank=(B/'cmos_even_bank_tree_v14.scs').read_text().replace('cmos_even_bank_tree_v14','cmos_even_bank_acq_v14')
bank=bank.replace('q1 out vdd vss)','q1 out fllclk vdd vss)')
# Avoid increasing loading of the internal RF/4 timing node.
bank=bank.replace('XD8 (d8b d4', 'XFAC0 (d4 fab vdd vss) pll_inv wn=0.5u wp=1u\nXFAC1 (fab fllclk vdd vss) pll_inv wn=2u wp=4u\nXD8 (d8b d4')
(B/'cmos_even_bank_acq_v14.scs').write_text(bank)
wrap=(B/'pll_control_sampled_v14.scs').read_text().replace('pll_control_sampled_v14','pll_control_rf4_v14').replace('tx_fll_controller_full_v14','tx_'+name)
wrap=wrap.replace('k5 outclk phase_good','k5 outclk acqclk phase_good')
wrap=wrap.replace('XCOUNT (outclk','''// acquired changes with counter gated off and reset asserted.
XACQI (acquired acquired_b vdd vss) pll_inv
XACQ0 (acqclk clock_mux acquired_b acquired vdd vss) pll_tg wn=1u wp=2u
XACQ1 (outclk clock_mux acquired acquired_b vdd vss) pll_tg wn=1u wp=2u
XACB0 (clock_mux clock_b vdd vss) pll_inv wn=1u wp=2u
XACB1 (clock_b count_clock vdd vss) pll_inv wn=2u wp=4u
XCOUNT (count_clock''')
(B/'pll_control_rf4_v14.scs').write_text(wrap)
top=(B/'pll_complete_k41_sampled_v14.scs').read_text().replace('pll_complete_k41_sampled_v14','pll_complete_v14').replace('pll_control_sampled_v14','pll_control_rf4_v14').replace('fll_controller_full_v14',name)
top=top.replace('include "div_fb50buf24_v14.scs"','include "cmos_even_bank_acq_v14.scs"')
top=top.replace('// First integration is explicitly K41/M4. Other K codes are not supported by this proof top.','// Programmable K9..41 physical PLL; functional coverage is recorded separately.')
top=top.replace('XD (clk q1 data vdd vss) div_fb50buf24_v14','XD (clk divider_reset s0 s1 s2 s3 s4 s5 q1 data acqclk vdd vss) cmos_even_bank_acq_v14')
top=top.replace('k5 out phase_good frequency_good b0','k5 out acqclk phase_good frequency_good b0')
(B/'pll_complete_v14.scs').write_text(top)
for corner in ['tt','ss','ff']:
 s=(H/'tb'/f'acquire_k41_{corner}.scs').read_text().replace('pll_complete_k41_v14','pll_complete_v14')
 s=s.replace('VDD (vdd 0) vsource dc=1.2','VDD (vdd_source 0) vsource dc=1.2\nahdl_include "supply_energy_observer.va"\nXE (vdd_source vdd 0 energy_nj power_mw) supply_energy_observer')
 s=s.replace('save obsphase','save energy_nj power_mw XP.XC.phase_held\nsave obsphase')
 s=s.replace('stop=42u','stop=36u')
 (H/'tb'/f'complete_k41_{corner}.scs').write_text(s)
for corner in ['tt','ss','ff']:
 for ratio in [4,6,8,10,12,14]:
  s=(H/'tb'/f'banktree_m{ratio}_{corner}.scs').read_text().replace('cmos_even_bank_tree_v14','cmos_even_bank_acq_v14')
  s=s.replace('include "cmos_even_bank_acq_v14.scs"','include "cmos_even_bank_acq_v14.scs"\ninclude "rtcomb_v13.scs"\ninclude "rt_light24s12_out083_v14.scs"')
  s=s.replace('q1 data vdd 0) cmos','q1 predata acqclk vdd 0) cmos')
  s=s.replace('CL (data','XR (predata clk data vdd 0) rt_light24s12_out083_v14\nCL (data')
  s=s.replace('save clk q1 data','save predata acqclk clk q1 data')
  (H/'tb'/f'bankrt_m{ratio}_{corner}.scs').write_text(s)
print('Built full programmable physical PLL; mapped',len(m['cells']),'FLL cells')
