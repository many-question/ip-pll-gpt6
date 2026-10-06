"""Bounded-memory reader for single-sweep real Spectre PSF ASCII transients."""
from array import array
import re
import numpy as np


def read_real_transient(path):
    names = []; in_trace = False; in_values = False; duplicates = 0
    buffers = {}; record = {}; last_time = -np.inf

    def flush():
        nonlocal last_time
        if not record:
            return
        if set(record) != set(buffers):
            raise ValueError('Incomplete transient record at '+str(record.get(b'"time"')))
        if record[b'"time"'] <= last_time:
            raise ValueError('Non-monotonic transient time')
        last_time = record[b'"time"']
        for k,b in buffers.items():
            b.append(record[k])

    with path.open('rb') as f:
        for line in f:
            stripped = line.strip()
            if not in_values:
                if stripped == b'TRACE':
                    in_trace = True
                elif stripped == b'VALUE':
                    if not names:
                        raise ValueError('No supported real traces')
                    buffers = {k:array('d') for k in [b'"time"']+names}
                    in_values = True
                elif in_trace:
                    m = re.fullmatch(rb'("[^"]+") "([^"]+)"(?: PROP\()?$',stripped)
                    if m and m[1] != b'"units"':
                        if m[2] not in (b'V',b'I',b'Real'):
                            raise ValueError('Unsupported trace type '+str(m[2]))
                        if m[1] in names:
                            raise ValueError('Duplicate trace declaration')
                        names.append(m[1])
                continue
            if stripped in (b'',b'END'):
                continue
            fields = stripped.split()
            if len(fields) != 2 or fields[0] not in buffers:
                raise ValueError('Unsupported value record '+repr(stripped[:120]))
            key = fields[0]
            if key == b'"time"':
                flush(); record = {}
            elif key in record:
                duplicates += 1
            record[key] = float(fields[1])
    flush()
    if not in_values or not buffers or not buffers[b'"time"']:
        raise ValueError('Empty transient')
    data = {k.strip(b'"').decode('ascii'):np.frombuffer(b,dtype=np.float64) for k,b in buffers.items()}
    if not all(np.isfinite(a).all() for a in data.values()):
        raise ValueError('Non-finite transient values')
    return data, dict(samples=len(data['time']),signals=len(data)-1,duplicate_records=duplicates)


def parse_project_directory(path):
    """Optimize only a pure large transient directory; retain bridge fallback."""
    from virtuoso_bridge.spectre.parsers import parse_psf_ascii_directory
    raw = path/'tran.tran.tran'
    files = [p for p in path.rglob('*') if p.is_file() and p.name not in ('logFile','logStatus')] if path.exists() else []
    if files == [raw] and raw.stat().st_size > 64*1024*1024:
        data, audit = read_real_transient(raw)
        if audit['duplicate_records']:
            raise ValueError('Repeated transient records require explicit review')
        print('Project streaming transient parser: '+str(audit),flush=True)
        return data
    return parse_psf_ascii_directory(path)
