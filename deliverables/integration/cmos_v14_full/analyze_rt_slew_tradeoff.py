"""Separate measured edge-slope conversion from equivalent output voltage noise.

This is an algebraic decomposition of the sampled edge PSD, not an independent
experiment holding slope or transistor noise fixed. Local-chain limits remain.
"""
from pathlib import Path
import hashlib,json,math
H=Path(__file__).resolve().parent
basefile=H/'results/chain_noise_validation.json';scalefile=H/'results/rt_noise_scaling_validation.json'
b=next(x for x in json.loads(basefile.read_text())['cases'] if x['case']=='chain_noise_fine_tt' and x.get('single_case_valid'))
s=json.loads(scalefile.read_text());rows=[]
for factor,jitter,slew in [(1,b['jitter_fs'],b['slew_v_per_s'])]+[(x['factor'],x['provisional_jitter_fs'],x['slew_v_per_s']) for x in s['cases'] if x['periodic_passed'] and x['noise_consistent']]:
    row=dict(factor=factor,provisional_jitter_fs=jitter,edge_slew_gv_per_s=slew/1e9,
             equivalent_edge_voltage_rms_mv=jitter*1e-15*slew*1e3)
    if factor>1:
        precision=json.loads((H/f'results/rt{factor}_precision_validation.json').read_text())
        assert precision['passed']
        vratio=row['equivalent_edge_voltage_rms_mv']/rows[0]['equivalent_edge_voltage_rms_mv']
        slope_ratio=slew/b['slew_v_per_s'];tratio=jitter/b['jitter_fs']
        row.update(precision_max_delta_db=precision['max_absolute_delta_db'],
            voltage_variance_change_db=20*math.log10(vratio),
            inverse_slope_squared_change_db=-20*math.log10(slope_ratio),
            timing_variance_change_db=20*math.log10(tratio))
    rows.append(row)
out=dict(scope=__doc__,cases=rows,band_hz=[1e4,492e6],
    condition='TT27/1.2V/984MHz/10fF,noiselessmeasuredRFreplay. SameactualRX/fullbank/quietload,onlyFFandtwooutputstagewidthsscaled.',
    equation='integral(S_t df)=integral(S_v df)/slope^2; equivalent sigma_v=sigma_t*slope at the chosen edge.',
    evidence_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [basefile,scalefile]},
    observation='Equivalent sampled edge voltage noise rises slightly while edge slope rises substantially; timing noise falls.',
    interpretation='In this edge measurement, improvement is explained by the larger slope denominator, not by a reduction of integrated output voltage PSD. Width changes affect both regeneration/loading and noise transfer, so this is not an isolated causal experiment.',
    limitations=['Baselinefullband0.5ps/767;candidatefullband1ps/383. Ownmatchedsixpointprecisionchecks<.02dBbutnotfullbandconvergenceproof.',
                 'Equivalent edge voltage RMS is a sampled-noise normalization, not broadband voltage RMS at arbitrary time.',
                 'Otheredges,independentnoiseon,harmonicneighborhoods,actualLC,PVTandfullPLLremain.'],
    full_pll_acceptance=False)
(H/'results/rt_slew_tradeoff.json').write_text(json.dumps(out,indent=2)+'\n')
lines=['# CMOS 输出链：尺寸与边沿斜率的实测关系','',
       '2026-10-04。以下来自已有器件噪声结果的代数分解，不是新的完整 PLL 仿真。条件：TT27、1.2 V、984 MHz、10 fF、外部无噪声实测 RF 重放，积分 10 kHz–492 MHz。','',
       '| FF及两级输出尺寸 | 暂定抖动 | 采样沿斜率 | 等效边沿电压噪声 RMS |',
       '|---|---:|---:|---:|']
for row in rows:
    lines.append(f'| {row["factor"]}倍 | {row["provisional_jitter_fs"]:.3f} fs | {row["edge_slew_gv_per_s"]:.3f} GV/s | {row["equivalent_edge_voltage_rms_mv"]:.3f} mV |')
four=next(x for x in rows if x['factor']==4)
lines += ['',
    '`S_t = S_v / slew²`。在这个采样边沿定义下，尺寸增大后等效电压噪声略增，而边沿斜率显著增加，因此时间噪声降低。',
    f'4倍相对基线的积分电压噪声方差变化 {four["voltage_variance_change_db"]:+.3f} dB，斜率平方分母贡献 {four["inverse_slope_squared_change_db"]:+.3f} dB，两者合计时间噪声方差变化 {four["timing_variance_change_db"]:+.3f} dB。','',
    '这支持继续改善重定时再生与输出转换速度。尺寸、驱动、负载和噪声传递同时变化，不能把该分解当成“单独改变边沿、保持其余完全不变”的因果实验，也不能用它预测无限加宽的收益。等效电压 RMS 只用于边沿噪声归一化，不是任意时刻节点的宽带电压 RMS。','',
    '基线全带采用0.5ps/767，候选全带采用1ps/383；2倍、4倍各自的匹配六频点精度变化分别仅0.01275/0.01455dB。六点精度、代数分解和局部积分均不替代完整频带、其他边沿、独立noise-on、真实LC负载反馈及PVT。当前实际LC四组对照已准备，尚未运行。','',
    '证据：[分解数据](results/rt_slew_tradeoff.json)、[原始尺寸对照](results/rt_noise_scaling_validation.json)、[2倍精度](results/rt2_precision_validation.json)、[4倍精度](results/rt4_precision_validation.json)。复现：`analyze_rt_slew_tradeoff.py`。']
(H/'NOISE_SLEW_DIAGNOSIS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(rows,indent=2))
