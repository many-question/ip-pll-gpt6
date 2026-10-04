"""Archive partial APS log and compare effective tstab/PSS options with AX.

No simulator state is changed. Normalized Newton norms are not a physical
error comparison when effective solver defaults differ.
"""
from pathlib import Path
import base64,datetime,hashlib,json,re,subprocess

H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def blocks(text):
    result={}
    for name in ['tstab integration','pss iteration']:
        m=re.search(r'Important parameter values in '+name+r':\n(.*?)(?:\n\s*\n)',text,re.S);assert m,name
        result[name]=dict(re.findall(r'^\s+([^=\n]+?)\s*=\s*(.*?)\s*$',m[1],re.M))
    return result

def main():
    src=R/'coredacnoise01/core_dac_discharge_noise_tt';dst=R/'coredacaps01/core_dac_discharge_noise_tt/live_settings'
    assert not dst.exists();remote='/home/jielu/TSMC180/MP/IP-PLL-GPT6/simulation/cmos_v14_full/aa0d11ed/spectre.out'
    code="import base64,hashlib,json\ns=open(%r,'rb').read()\nprint(json.dumps(dict(sha256=hashlib.sha256(s).hexdigest(),bytes=len(s),data=base64.b64encode(s))))"%remote
    enc=base64.b64encode(code.encode()).decode()
    ssh=['C:/Windows/System32/OpenSSH/ssh.exe','-F',str(Path.home()/'.virtuoso-bridge/ssh_config_ipv6'),'-o','BatchMode=yes','thu-xia-v6']
    value=json.loads(subprocess.check_output(ssh+['/usr/bin/python -c "import base64;exec(base64.b64decode(\''+enc+'\'))"'],timeout=30))
    data=base64.b64decode(value.pop('data'));assert len(data)==value['bytes'] and hashlib.sha256(data).hexdigest()==value['sha256']
    now=datetime.datetime.now().astimezone().isoformat();a=blocks((src/'spectre.out').read_text());b=blocks(data.decode())
    dst.mkdir();log=dst/'spectre.out';log.write_bytes(data)
    meta=dict(remote=remote,time=now,partial_log=True,**value);(dst/'snapshot.json').write_text(json.dumps(meta,indent=2)+'\n')
    diffs={name:{k:dict(ax=a[name].get(k),aps=b[name].get(k)) for k in set(a[name])|set(b[name]) if a[name].get(k)!=b[name].get(k)} for name in a}
    out=dict(scope=__doc__,time=now,ax_log=(src/'spectre.out').relative_to(ROOT).as_posix(),ax_log_sha256=sha(src/'spectre.out'),
        aps_log=log.relative_to(ROOT).as_posix(),aps_log_sha256=sha(log),aps_snapshot_sha256=sha(dst/'snapshot.json'),
        source_protocol_sha256=sha(H/'results/core_dac_aps_noise_protocol.json'),effective_options=dict(ax=a,aps=b),differences=diffs,
        same_explicit_netlist_inputs=True,effective_pss_settings_identical=not bool(diffs['pss iteration']),
        raw_newton_norms_directly_comparable=False,full_pll_acceptance=False,
        interpretation='Retain this as an engine-and-effective-defaults diagnostic. Compare physical residuals and accepted solutions, not the normalized norm alone. No PSS/noise acceptance from a partial log.')
    protocol=json.loads((H/'results/core_dac_aps_noise_protocol.json').read_text())
    correct=(src/'result.json').relative_to(ROOT).as_posix();digest=sha(src/'result.json')
    assert digest==protocol['source_result_sha256']
    if protocol['source_result']!=correct:
        out['predecessor_reference_correction']=dict(original_protocol_preserved=True,
            original_mislabeled_source_result=protocol['source_result'],source_result=correct,source_result_sha256=digest,
            meaning='The APS protocol copied the seed-producer path but updated its hash to the AX predecessor. This supplement pairs the AX hash with its correct path; physical dependency/seed checks are unchanged.')
    pp=H/'results/core_mode_settings_validation.json';assert not pp.exists();pp.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(differences=diffs,effective_pss_settings_identical=out['effective_pss_settings_identical']),indent=2))

if __name__=='__main__':main()
