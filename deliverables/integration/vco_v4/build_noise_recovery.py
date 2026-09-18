from build import H
s=(H/'tb/noise_divider_tt_c8.scs').read_text()
s=s.replace('temp=27','temp=27 gmin=1n')
s=s.replace('tstab=200n','tstab=800n method=traponly')
(H/'tb/noise_divider_recovery.scs').write_text(s)
