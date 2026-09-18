from pathlib import Path
from build_receiver import head
HERE=Path(__file__).resolve().parent
B=HERE.parents[1]/'blocks/transistor_v2'

def sources_bus(prefix,value,bits):
    return [f'V{prefix}{i} ({prefix}{i} 0) vsource dc={1.2 if value&(1<<i) else 0}' for i in range(bits)]

def main():
    extra='include "digital_cells_v2.scs"\ninclude "fll_circuit.scs"\n'
    for c,temp in [('tt',27),('ss',60),('ff',0)]:
        lines=[head(c,temp),extra,'VDD (vdd 0) vsource dc=1.2',
        'VC (clk 0) vsource type=pulse val0=0 val1=1.2 delay=20.25n rise=20p fall=20p width=480p period=1n',
        'VG (gate 0) vsource type=pulse val0=0 val1=1.2 delay=40n rise=20p fall=20p width=256n period=1u',
        'VR (rst 0) vsource type=pulse val0=1.2 val1=0 delay=10n rise=20p fall=20p width=1u period=2u',
        'XC (clk gate rst '+' '.join(f'q{i}' for i in range(14))+' vdd 0) tx_fll_counter',
        'tran tran stop=350n maxstep=20p errpreset=conservative',
        'save clk gate rst VDD:p '+' '.join(f'q{i}' for i in range(14)),'saveOptions options save=selected']
        (HERE/'tb'/f'tb_fll_counter_{c}.scs').write_text('\n'.join(lines)+'\n')
    ports=['refclk','reset']+[f'target_k{i}' for i in range(6)]+[f'measured{i}' for i in range(14)]+[f'coarse{i}' for i in range(8)]+[f'dac{i}' for i in range(6)]+['count_gate','count_reset','enable','range_error']+[f'state_out{i}' for i in range(3)]
    # Stimulus/measurement adapter only: its equations never replace DUT logic.
    decports=[f'c{i}' for i in range(8)]+[f'd{i}' for i in range(6)]+[f'm{i}' for i in range(14)]+[f's{i}' for i in range(3)]
    va=['`include "constants.vams"','`include "disciplines.vams"',
        'module fll_testplant('+','.join(decports+['preset','clk','code_mon','dac_mon','count_mon','state_mon','freq_mon'])+');',
        'inout '+','.join(decports+['preset','clk','code_mon','dac_mon','count_mon','state_mon','freq_mon'])+';',
        'electrical '+','.join(decports+['preset','clk','code_mon','dac_mon','count_mon','state_mon','freq_mon'])+';',
        'parameter real ratio=4; parameter real f0=4.0e9; parameter real step=5e6; parameter real kv=20e6;',
        'real code,dcnt,mcount,state,freq,phase,sinewave; integer logic_clk;', 'analog begin']
    va+=['code='+'+'.join(f'((V(c{i})>0.6)?{1<<i}:0)' for i in range(8))+';']
    va+=['@(timer(0,20n)) begin']
    for dest,prefix,n in [('dcnt','d',6),('mcount','m',14),('state','s',3)]:
        va+=[dest+'='+'+'.join(f'((V({prefix}{i})>0.6)?{1<<i}:0)' for i in range(n))+';']
    va+=['end']
    va+=['freq=(f0-step*code+kv*(V(preset)-0.6))/ratio;',
         'phase=idtmod(freq,0,1); sinewave=sin(2*`M_PI*phase);',
         '@(initial_step) logic_clk=0;',
         '@(cross(sinewave,0,1f,1u)) logic_clk=(sinewave>0);',
         'V(clk)<+transition(1.2*logic_clk,0,15p,15p); $bound_step(1.0/(12*freq));',
         'V(code_mon)<+transition(code,0,1n); V(dac_mon)<+transition(dcnt,0,1n); V(count_mon)<+transition(mcount,0,1n); V(state_mon)<+transition(state,0,1n); V(freq_mon)<+freq;', 'end','endmodule']
    (B/'fll_testplant.va').write_text('\n'.join(va)+'\n')
    lines=[head().replace('reltol=1e-5 vabstol=1e-7 iabstol=1e-13','reltol=1e-3 vabstol=1e-5 iabstol=1e-12'),extra,'ahdl_include "fll_testplant.va"','ahdl_include "supply_meter.va"',
        'VDD (vd 0) vsource dc=1.2','XM (vd vdd 0 pmw) supply_meter start=165u',
        'VC (refclk 0) vsource type=pulse val0=0 val1=1.2 delay=21n rise=50p fall=50p width=20.7833333333n period=41.6666666667n',
        'VR (reset 0) vsource type=pulse val0=1.2 val1=0 delay=100n rise=50p fall=50p width=1m period=2m']
    lines+=sources_bus('target_k',41,6)
    lines+=['XF ('+' '.join(ports)+' vdd 0) tx_fll_controller',
        'XC (outclk count_gate count_reset '+' '.join(f'counter{i}' for i in range(14))+' vdd 0) tx_fll_counter',
        'XSN (count_gate '+' '.join(f'counter{i}' for i in range(14))+' '+' '.join(f'measured{i}' for i in range(14))+' vdd 0) tx_fll_snapshot',
        'XD ('+' '.join(f'dac{i}' for i in range(6))+' enable preset vdd 0) tx_fll_dac',
        'XL (ctrl vc1 enable preset vdd 0) tx_loop_filter rlf=100k',
        'XP ('+' '.join([f'coarse{i}' for i in range(8)]+[f'dac{i}' for i in range(6)]+[f'measured{i}' for i in range(14)]+[f'state_out{i}' for i in range(3)]+['ctrl','outclk','code_mon','dac_mon','count_mon','state_mon','freq_mon'])+') fll_testplant',
        'tran tran stop=170u errpreset=moderate strobeperiod=20n strobeoutput=strobeonly',
        'save pmw preset ctrl vc1 count_gate count_reset enable range_error code_mon dac_mon count_mon state_mon freq_mon','saveOptions options save=selected']
    (HERE/'tb/tb_fll_acquire_tt.scs').write_text('\n'.join(lines)+'\n')
if __name__=='__main__':main()
