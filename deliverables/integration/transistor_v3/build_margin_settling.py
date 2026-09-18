from pathlib import Path
H=Path(__file__).resolve().parent
def main():
    for code in [160,176,192]:
        s=(H/'tb'/f'tb_rlc_loaded_c{code}_mid.scs').read_text()
        s=s.replace('ic vp=1.20001 vn=1.2','ic vp=1.21 vn=1.2').replace('stop=300n','stop=1u')
        (H/'tb'/f'tb_rlc_loaded_c{code}_settled.scs').write_text(s,newline='\n')
if __name__=='__main__':main()
