"""Share the real count/snapshot hardware between acquisition and watchdog."""
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/transistor_v3'
def main():
    s=(B/'pll_control_frontend.scs').read_text().replace('tx_pll_control_frontend','tx_pll_control_monitored')
    lines=s.splitlines()
    lines=[x.replace('count_gate count_reset acquired','fll_gate fll_count_reset acquired') if x.startswith('XF ') else x for x in lines]
    extra=['// Acquired switches only while both gate sources are low and reset high.',
      'XWG (fll_gate watch_gate acquired count_gate vdd vss) tx_mux',
      'XWR (fll_count_reset watch_reset acquired count_reset vdd vss) tx_mux',
      'XW (refclk fll_reset acquired '+' '.join(f'ak{i}' for i in range(6))+' '+' '.join(f'm{i}' for i in range(14))+' watch_gate watch_reset frequency_good watchdog_valid vdd vss) tx_frequency_watchdog']
    lines[-1:-1]=extra
    s='\n'.join(lines)+'\n'
    s=s.replace('// Physical control assembly. phase_good/frequency_good are sensing interfaces;\n// their detector circuits are not implemented by this digital wrapper.',
        '// Shared-counter control assembly. phase_good remains a sensing input.\n// frequency_good is an OUTPUT from the physical counter/watchdog.\n// Include frequency_watchdog.scs in addition to the base dependencies.')
    (B/'pll_control_monitored.scs').write_text(s,newline='\n')
    t=(H/'tb/tb_control_frontend_tt.scs').read_text().replace('include "pll_control_frontend.scs"','include "frequency_watchdog.scs"\ninclude "pll_control_monitored.scs"')
    t=t.replace('tx_pll_control_frontend','tx_pll_control_monitored').replace('outclk 0 0 b0','outclk 0 frequency_good b0')
    t=t.replace('save outclk','save frequency_good outclk')
    (H/'tb/tb_monitored_frontend_tt.scs').write_text(t,newline='\n')
if __name__=='__main__':main()
