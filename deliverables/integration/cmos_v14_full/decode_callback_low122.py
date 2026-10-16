"""Replay observed EVAL transitions, without fitting a VCO or forcing a lock code."""
import numpy as np

def intervals(t,y):
    mask=np.asarray(y)>.6
    starts=np.flatnonzero(mask & ~np.r_[False,mask[:-1]])
    ends=np.flatnonzero(mask & ~np.r_[mask[1:],False])
    return [dict(start_s=float(t[i]),end_s=float(t[min(j+1,len(t)-1)]),duration_s=float(t[min(j+1,len(t)-1)]-t[i]),reaches_record_end=bool(j==len(t)-1)) for i,j in zip(starts,ends)]

def decode(t,d,coarse_target=896,fresh_target=3584):
    bits=lambda pref,n:sum((d[pref+str(i)]>.6).astype(np.int64)*(1<<i) for i in range(n))
    state=bits('XP.XC.state',3);coarse=bits('XP.b',8);dac=bits('XP.XC.d',6);count=bits('XP.XC.m',14)
    resets=intervals(t,d['XP.restart']);reset_starts=[x['start_s'] for x in resets]
    current_epoch=None;rows=[];warnings=[]
    for i in np.flatnonzero((state[1:]==3)&(state[:-1]!=3))+1:
        k=int(np.searchsorted(t,t[i]+20e-9))
        if k>=len(t):warnings.append('EVAL clipped at end');continue
        if state[k]!=3:
            warnings.append('Brief EVAL at %.12g; retained as decoder limitation, not silently accepted'%t[i]);continue
        remain=np.flatnonzero(state[k:]!=3)
        if not len(remain):warnings.append('EVAL has no observed transition');continue
        end=k+int(remain[0]);after=int(np.searchsorted(t,t[end]+20e-9))
        if after>=len(t):warnings.append('EVAL next state clipped');continue
        epoch=sum(x<=t[k] for x in reset_starts)
        if epoch!=current_epoch:
            current_epoch=epoch;stage='endpoint';mask=128;cc=0;dd=11;low=11;high=53;checks=0;good=False;recentered=False
        actual=(int(coarse[k]),int(dac[k]));m=int(count[k]);target=coarse_target if stage in ['endpoint','coarse'] else fresh_target
        row=dict(epoch=epoch,time_s=float(t[k]),transition_time_s=float(t[end]),stage=stage,coarse=actual[0],dac=actual[1],measured_count=m,count_error=m-target,
          expected_current_coarse=cc,expected_current_dac=dd,current_code_matches=actual==(cc,dd),nfilt_V=float(d['XP.XV.XL.nfilt'][k]),ctrl_V=float(d['XP.ctrl'][k]))
        # Evaluate the frozen algorithm using observed inputs/codes; discrepancies
        # remain explicit, rather than being hidden by a divergent guessed state.
        cc,dd=actual;expected_state=0;expect_error=False
        if stage=='endpoint':
            if m>target:cc=128;stage='coarse';mask=128
            else:cc=0;dd=32;mask=32;stage='fine_sar'
        elif stage=='coarse':
            keep=cc if m>target else cc&~mask
            if mask==1:cc=min(255,keep+2);dd=32;mask=32;stage='fine_sar'
            else:mask>>=1;cc=keep|mask
        elif stage=='fine_sar':
            keep=dd&~mask if m>=target else dd
            if mask==1:dd=32;low=11;high=53;checks=0;good=False;stage='fresh'
            else:mask>>=1;dd=keep|mask
        elif stage=='fresh':
            checks+=1;need_slower=dd<=15 and m>target;need_faster=dd>=49 and m<target
            row.update(fresh_check=checks,previous_same_code_good=good,lower_bound=low,upper_bound=high,need_slower=need_slower,need_faster=need_faster)
            if need_slower or need_faster:
                good=False
                if recentered or checks==8 or (need_slower and cc==255) or (need_faster and cc==0):expected_state=5;expect_error=True
                else:
                    cc+=1 if need_slower else -1;dd=32;low=11;high=53;recentered=True;row['coarse_correction_expected']=True
            elif abs(m-target)<=1 and good:expected_state=4;row['two_same_code_good_expected']=True
            elif checks==8:expected_state=5;expect_error=True
            elif abs(m-target)<=1:good=True
            else:
                good=False
                if m>target:
                    if dd<=low:expected_state=5;expect_error=True
                    else:high=dd-1;dd=(low+dd-1)//2
                else:
                    if dd>=high:expected_state=5;expect_error=True
                    else:low=dd+1;dd=(dd+1+high)//2
            if expected_state in [4,5]:stage='terminal'
        else:
            warnings.append('Unexpected EVAL after terminal state without observed restart');expected_state=-1
        row.update(next_coarse=int(coarse[after]),next_dac=int(dac[after]),next_state=int(state[after]),expected_next_coarse=cc,expected_next_dac=dd,
            expected_next_state=expected_state,expected_range_error=expect_error,observed_range_error=bool(d['range_error'][after]>.6))
        row['transition_matches']=bool((cc,dd,expected_state)==(int(coarse[after]),int(dac[after]),int(state[after])) and expect_error==bool(d['range_error'][after]>.6))
        rows.append(row)
    handoffs=intervals(t,(state==4).astype(float))
    for h in handoffs:
        h['duration_matches_32ref']=abs(h['duration_s']-32/24e6)<=4e-9
    return dict(eval_snapshots=rows,decoder_warnings=warnings,restart_intervals=resets,handoff_intervals=handoffs,
        all_observed_transitions_match=bool(rows) and not warnings and all(x['current_code_matches'] and x['transition_matches'] for x in rows),
        fresh_budget_respected=all(x.get('fresh_check',0)<=8 for x in rows),
        physical_coarse_corrections=[x for x in rows if x.get('coarse_correction_expected') and x['transition_matches']],
        handoff_qualified_by_observed_counts=[x for x in rows if x.get('two_same_code_good_expected') and x['transition_matches']])
