"""Retain initial mixed-option trials; use documented single-list semantics."""
import json,re,hashlib,datetime
from analyze import H,R
p=H/'results/gating_protocol.json';d=json.loads(p.read_text());assert 'option_correction' not in d
d['legacy_cases']={};proof=[]
for group in ['divider','master','slave','output','bias']:
 old='noise_gate_'+group+'_coarse';new=old.replace('_coarse','_only_coarse') if group in ['divider','master'] else old
 source=H/'tb'/f'{old}.scs';dest=H/'tb'/f'{new}.scs';s=source.read_text();patched=re.sub(r' noiseoff_inst=\[[^\]]*\]','',s)
 if new==old:assert not list(R.glob('*/'+old+'/inputs'))
 else:assert not dest.exists()
 dest.write_text(patched,encoding='utf-8',newline='\n')
 proof.append(dict(source=old,destination=new,original_sha256=hashlib.sha256(s.encode()).hexdigest(),corrected_sha256=hashlib.sha256(patched.encode()).hexdigest()))
 if new!=old:d['legacy_cases'][old]=d['cases'].pop(old);d['cases'][new]=d['legacy_cases'][old]
d['option_correction']=dict(time=datetime.datetime.now().astimezone().isoformat(),observed_warning='SPECTRE-16782: only one of noiseon_inst/noiseoff_inst may be specified; extra options ignored.',observed_results='Initial divider-only has exact zero contribution from XRT and499.141469fs; all-off0fs. Mixed-option divider/master retained but superseded by unambiguous single-option trials.',method='Only noiseon_inst for single-on/all-on. Only noiseoff_inst for all-off. The complementary off lists in cases are assertions for verification, not simultaneously emitted simulator options.',changes=proof)
d['method']='Only simulator noise-enable lists change; retain deterministic devices, loading and bias. Single-on uses noiseon_inst alone and verifies every complementary device contribution is zero.'
p.write_text(json.dumps(d,indent=2)+'\n')
print('Prepared clean single-option fixtures')
