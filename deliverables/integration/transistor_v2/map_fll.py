"""Map Yosys generic gates to project-owned CMOS cells; no PDK IP is copied."""
import json,collections
from pathlib import Path
HERE=Path(__file__).resolve().parent
B=HERE.parents[1]/'blocks/transistor_v2'
def main():
    s='''simulator lang=spectre
subckt tx_and (a b y vdd vss)
XN (a b n vdd vss) pll_nand2
XI (n y vdd vss) pll_inv wn=500n wp=1.25u
ends tx_and
subckt tx_or (a b y vdd vss)
XN (a b n vdd vss) pll_nor2
XI (n y vdd vss) pll_inv wn=500n wp=1.25u
ends tx_or
subckt tx_mux (a b s y vdd vss)
XI (s sb vdd vss) pll_inv wn=500n wp=1.25u
XT0 (a z sb s vdd vss) pll_tg wn=500n wp=1u
XT1 (b z s sb vdd vss) pll_tg wn=500n wp=1u
XB0 (z zb vdd vss) pll_inv wn=500n wp=1.25u
XB1 (zb y vdd vss) pll_inv wn=500n wp=1.25u
ends tx_mux
subckt tx_xor (a b y vdd vss)
XI (a ab vdd vss) pll_inv wn=500n wp=1.25u
XM (a ab b y vdd vss) tx_mux
ends tx_xor
subckt tx_xnor (a b y vdd vss)
XX (a b n vdd vss) tx_xor
XI (n y vdd vss) pll_inv wn=500n wp=1.25u
ends tx_xnor
subckt tx_latch_r (d gate gateb resetb q vdd vss)
XT (d x gate gateb vdd vss) pll_tg wn=800n wp=1.6u
XN (x resetb qb vdd vss) pll_nand2 wn=1u wp=1.25u
XO (qb q vdd vss) pll_inv wn=800n wp=2u
XF (q x gateb gate vdd vss) pll_tg wn=400n wp=800n
ends tx_latch_r
subckt tx_dff_r0 (d clk reset q vdd vss)
XC (clk clkb vdd vss) pll_inv wn=2u wp=5u
XR (reset resetb vdd vss) pll_inv wn=1u wp=2.5u
XM (d clkb clk resetb qm vdd vss) tx_latch_r
XS (qm clk clkb resetb q vdd vss) tx_latch_r
ends tx_dff_r0
subckt tx_dff_r1 (d clk reset q vdd vss)
XI (d db vdd vss) pll_inv wn=500n wp=1.25u
XF (db clk reset qb vdd vss) tx_dff_r0
XO (qb q vdd vss) pll_inv wn=800n wp=2u
ends tx_dff_r1
subckt tx_tff (clk reset q qb vdd vss)
XF (qb clk reset q vdd vss) tx_dff_r0
XI (q qb vdd vss) pll_inv wn=1u wp=2.5u
ends tx_tff
'''
    (B/'digital_cells_v2.scs').write_text(s)
    mod=json.loads((B/'fll_mapped.json').read_text())['modules']['fll_controller']
    names={}; ports=[]
    for p,info in mod['ports'].items():
        for i,bit in enumerate(info['bits']):
            name=p if len(info['bits'])==1 else f'{p}{i}'
            names[bit]=name;ports.append(name)
    def node(bit):return {'0':'vss','1':'vdd'}.get(bit,names.get(bit,f'n{bit}'))
    lines=['simulator lang=spectre','// Generated from fll_controller.v through Yosys generic gates.',
           'subckt tx_fll_controller ('+' '.join(ports)+' vdd vss)']
    mapping={'$_AND_':('tx_and','ABY'),'$_OR_':('tx_or','ABY'),'$_NOT_':('pll_inv','AY'),
             '$_XOR_':('tx_xor','ABY'),'$_XNOR_':('tx_xnor','ABY'),'$_MUX_':('tx_mux','ABSY'),
             '$_DFF_PP0_':('tx_dff_r0','DCRQ'),'$_DFF_PP1_':('tx_dff_r1','DCRQ')}
    for i,(name,c) in enumerate(sorted(mod['cells'].items())):
        sub,order=mapping[c['type']]
        nets=' '.join(node(c['connections'][x][0]) for x in order)
        lines.append(f'X{i} ({nets} vdd vss) {sub}')
    lines+=['ends tx_fll_controller','subckt tx_fll_counter (clk gate reset '+' '.join(f'q{i}' for i in range(14))+' vdd vss)',
            '// Latch the enable while clock is low, then deliver complete pulses.',
            'XCI (clk clkb vdd vss) pll_inv wn=2u wp=5u',
            'XGE (gate clkb clk safe_gate vdd vss) pll_latch',
            'XG (clk safe_gate gclk vdd vss) tx_and']
    for i in range(14):
        clk='gclk' if i==0 else f'qb{i-1}'
        lines.append(f'XF{i} ({clk} reset q{i} qb{i} vdd vss) tx_tff')
    lines+=['ends tx_fll_counter','subckt tx_fll_snapshot (gate '+' '.join(f'd{i}' for i in range(14))+' '+' '.join(f'q{i}' for i in range(14))+' vdd vss)',
            '// Hold the comparison bus during measurement; open after clock gate closes.',
            'XI (gate openb vdd vss) pll_inv wn=8u wp=20u',
            'XB (openb hold vdd vss) pll_inv wn=8u wp=20u']
    for i in range(14):lines.append(f'XL{i} (d{i} openb hold q{i} vdd vss) pll_latch')
    lines+=['ends tx_fll_snapshot','subckt tx_fll_dac ('+' '.join(f'd{i}' for i in range(6))+' enable out vdd vss)',
            '// Ideal resistor geometry; device output stages and their supply are physical.',
            'MP (vd enable vdd vdd) pch w=20u l=180n ad=4.8p as=4.8p pd=40.48u ps=40.48u']
    for i in range(6):
        n='out' if i==5 else f'r{i}'
        lines += [f'XI{i} (d{i} b{i} vd vss) pll_inv wn=2u wp=5u',
                  f'XO{i} (b{i} v{i} vd vss) pll_inv wn=5u wp=12.5u',f'RB{i} (v{i} {n}) resistor r=10k']
        if i:lines.append(f'RS{i} (r{i-1} {n}) resistor r=5k')
    lines+=['RT (r0 vss) resistor r=10k','ends tx_fll_dac']
    (B/'fll_circuit.scs').write_text('\n'.join(lines)+'\n')
    (HERE/'results/fll_gate_count.json').write_text(json.dumps(dict(collections.Counter(c['type'] for c in mod['cells'].values())),indent=2)+'\n')
    print(len(mod['cells']),'mapped cells')
if __name__=='__main__':main()
