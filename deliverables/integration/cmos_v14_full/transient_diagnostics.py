"""Read effective transient settings and numerical-recovery evidence from logs."""
import re
from decimal import Decimal

def effective(log):
    # Global options printed before restore can disagree with these analysis
    # settings. Only use indented analysis-value lines, not the global preamble.
    units={'s':1.,'V':1.,'A':1.,'Hz':1.,'fs':1e-15,'ps':1e-12,'ns':1e-9,'us':1e-6,
           'nV':1e-9,'uV':1e-6,'mV':1e-3,'fA':1e-15,'pA':1e-12,'nA':1e-9,
           'kHz':1e3,'MHz':1e6,'GHz':1e9}
    out={}
    for key in ['reltol','abstol(V)','abstol(I)','method','maxstep','noisefmax','noisefmin','trannoisemethod']:
        rows=re.findall(r'^    '+re.escape(key)+r' = ([^\n,]+)',log,re.M)
        if not rows:continue
        val=rows[-1].strip();parts=val.split()
        try:
            float(parts[0])
            out[key]=float(Decimal(parts[0])*Decimal(str(units[parts[1]] if len(parts)>1 else 1.)))
        except (ValueError,KeyError):out[key]=val
    return out

def recovery(log):
    matches={'newton_failures_reported':'Newton iteration fails to converge',
             'skipped_breakpoints_reported':'SPECTRE-17087',
             'lte_relaxations_reported':'SPECTRE-16780',
             'minimum_step_warnings_reported':'SPECTRE-16191'}
    counts={k:log.count(v) for k,v in matches.items()}
    return dict(counts,numerically_clean=not any(counts.values()),
                counts_may_be_suppressed='Further occurrences of this' in log)
