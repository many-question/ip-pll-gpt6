"""Small PSF helpers shared by the noise recovery experiments."""
import re
import numpy as np
from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii

def parse(p):
    return {k:np.asarray(v) for k,v in parse_spectre_psf_ascii(p).data.items() if k!='units'}

def cross(t,y,threshold=.6):
    i=np.flatnonzero((y[:-1]<threshold)&(y[1:]>=threshold))
    return t[i]+(threshold-y[i])/(y[i+1]-y[i])*(t[i+1]-t[i])

def header(p,key):
    return float(re.search('"'+re.escape(key)+'"\\s+([0-9.eE+\\-]+)',p.read_text())[1])

def devices(p,n):
    s=p.read_text();types={}
    for name,body in re.findall(r'"([^\"]+)" STRUCT\((.*?)\) PROP\(',s,re.S):
        fields=re.findall(r'^"([^\"]+)" FLOAT DOUBLE PROP\(',body,re.M)
        if 'total' in fields:types[name]=(len(fields),fields.index('total'))
    names=dict(re.findall(r'^"([^\"]+)" "([^\"]+)"$',s.split('\nTRACE\n',1)[1].split('\nVALUE\n',1)[0],re.M));cols={}
    for name,body in re.findall(r'^"([^\"]+)" \(\n(.*?)\n\)',s.split('\nVALUE\n',1)[1],re.M|re.S):
        length,idx=types[names[name]];a=np.fromstring(body,sep=' ');assert len(a)==length
        cols.setdefault(name,[]).append(a[idx])
    for k,v in cols.items():assert len(v)==n and np.all(np.isfinite(v)) and min(v)>=0,k
    return {k:np.asarray(v) for k,v in cols.items()}

def stream_selected(p,keys):
    """Read tstab records, coalescing repeated values at a segment boundary.

    Spectre can repeat the signal block at tstab end without another time line.
    Appending each column independently would then misalign time and voltages.
    """
    data={k:[] for k in ['time']+keys};record={};active=False;duplicates=0
    def flush():
        if not record:return
        assert set(data)<=set(record),('incomplete record',record.get('time'))
        for k in data:data[k].append(record[k])
    with p.open() as f:
        for line in f:
            if not active:
                if line.strip()=='VALUE':active=True
                continue
            z=line.split()
            if len(z)!=2:continue
            name=z[0].strip('"')
            if name not in data:continue
            if name=='time':flush();record={}
            elif name in record:duplicates+=1
            record[name]=float(z[1])
    flush()
    arrays={k:np.asarray(v) for k,v in data.items()}
    assert np.all(np.diff(arrays['time'])>0)
    return arrays,duplicates
