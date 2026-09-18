"""Render the measured R2 repair summary; refuse incomplete channel evidence."""
from analyze import H
import json

def read(name):return json.loads((H/'results'/name).read_text())

def main():
    d=read('final_validation.json');assert d['all_pass'] and d['passed_points']==99
    p=read('precision_validation.json');assert p['all_pass']
    f=read('fine_curve_validation.json');assert f['all_pass']
    a=read('auxiliary_validation.json');assert a['public_defaults']['pass_check']
    dyn=[x for x in read('dynamic_validation.json') if x['revision']=='r2'];assert len(dyn)==3 and all(x['pass_check'] for x in dyn)
    ac=[x for x in read('startup_admittance.json') if x['case'].startswith('r2_')];assert len(ac)==6 and all(x['linear_startup'] for x in ac)
    noise=read('noise_summary.json');loaded=next(x for x in noise if x['case']=='r2_noise_divider')
    precision=max(abs(v) for x in p['cases'] for v in x['frequency_change_hz'])/1e6
    selected=d['selected'];vco=d['vco_power_range_mw'];branch=d['measured_branch_power_range_mw']
    pn=[]
    for c,label in [('tt','TT / 27°C'),('ss','SS / 60°C'),('ff','FF / 0°C')]:
        for code in [6,243]:
            r=next(x for x in noise if x['case']==f'r2_noise_{c}_c{code}')
            pn.append(f'| {label} | {code} | {r["frequency_hz"]/1e9:.6f} | {r["phase_noise_dbc_hz"]["1000000.0"]:.3f} | {r["vco_power_mw"]:.4f} |')
    noise_table='\n'.join(pn)
    kv=[]
    for r in f['cases']:
        slopes=r['interval_kvco_hz_per_v'];kv.append(f'| {r["corner"].upper()}，K={r["k"]}，码 {r["code"]} | '+ ' / '.join(f'{x/1e6:.3f}' for x in slopes)+' |')
    kv_table='\n'.join(kv)
    nprecision='\n'.join(f'- `{x["refinement"]}`：相噪最大变化 {x["maximum_absolute_change_db"]:.5f} dB，载频变化 {x["carrier_frequency_change_hz"]/1e3:.3f} kHz；内部数值一致性检查 {"通过" if x["pass_check"] else "未通过"}。' for x in a['noise_precision'])
    counts=read('raw_manifest.json')
    text=f'''# VCO 电路修复 R2：起振和所需频点覆盖恢复

在 **1.2 V、暂定电感 Q=5（3.3 GHz）** 下，修复版完成 **TT/27°C、SS/60°C、FF/0°C × 33 个输出频点，共 99 个加载检查**。各点的实际 VCO 细调区间包含目标频率，两个细调端点的真实 MOS 分频器都正常分频。最小端点裕量为 **{d['minimum_margin_hz']/1e6:.3f} MHz**，最小差分振荡峰峰值为 **{d['minimum_diff_pp_v']:.3f} V**。

这解决了上一版在同一 Q=5 模型下的低频失振和高频覆盖不足。电感 Q 未调高，仍不是 PDK/EM 电感；本轮也不是完整 PLL 捕获或 <200 fs 抖动签核。**Q=3 时慢角低频端仍失振**，不能把 Q=5 的通过结果外推到更差电感。

推荐入口：[电路参数与接口](../../blocks/vco_v4/README.md)、[lc_vco_repaired.scs](../../blocks/vco_v4/lc_vco_repaired.scs)。核心改为 120 µm NMOS，缩小并偏置粗调阵列的关断底板，按粗调码分段增加尾电流；再将部分固定电容转为细调电容，解决粗调进位处重叠不足。IREF 发生器按已有约定继续后置。

## 频率和真实负载验证

输出目标为 K×24 MHz，K=9…41；按既有 M=4/6/8/10/12/14 映射，所需 VCO 频点位于 2.688–3.936 GHz。每个角、每个频点独立选择粗调码，记录在 [99 点码表](results/channel_map.csv)；全部原始判据及不通过的搜索尝试见 [final_validation.json](results/final_validation.json)。码表是仿真台搜索结果，不是芯片 FLL 已经正确捕获的证明，也不是未经测量的全 256 码连续覆盖结论。

![99 点加载覆盖](figures/channel_coverage.png)

连接真实分频器及其未选中支路、交流偏置、采样器、CP、24 MHz 参考缓冲和 MOS 脉冲时序；分频输出负载暂取 10 fF。CP 输出钳位 0.6 V，VCO 细调由 TB 从 0.2 V 切至 1.0 V。仿真 280 ns，测量窗分别为 110–150 ns、240–280 ns；在 DC 偏置已建立时，从 10 µV 初始差分种子启动，未使用行为振荡源。这不含真实电源爬升和偏置发生器的冷启动。

验收同时检查实际 VCO 波形与分频输出，避免把失振时分频器自身边沿误认作成功：

- 差分峰峰值 >50 mV；平均分频比误差 <0.1%，逐周期最大误差 <2%。
- 目标 VCO 频率位于实测细调端点之间，距两端均 >2 MHz。2 MHz 是本轮内部数值/设计留量，不是新的人类需求或供电、失配裕量保证。
- 本地输入与远端输入 SHA-256 一致，最终 Spectre 日志为 0 errors。

主扫描使用 Spectre X AX、2 线程、**显式 `-preset_override=maxstep`、实际 maxstep=2 ps、trap、reltol=1e-3**。三个关键点额外用 1 ps 复核，其中 SS 高端使用 APS conservative；最大频率变化 **{precision:.3f} MHz**，仍满足 2 MHz 留量和逐周期分频检查。见 [精度复核](results/precision_validation.json)。

## 起振、粗调切换与细调曲线

独立小信号 AC 在每侧 140 fF 代理负载下提取差分输入导纳，主动核心电流包含漏极和交叉栅极端口。三个角的高、低端共六点均为负净电导；最差为 SS 低端，主动负电导与损耗电导比 **{min(x['startup_gain_ratio'] for x in ac):.3f}**。该指标是静态小信号起振证据，不等于实际周期负载下的大信号幅度。见 [起振导纳](results/startup_admittance.json)。

三角均完成粗调序列 `0,7,8,15,16,31,32,63,64,103,104,127,128,247,248,255,0,255`。每段 80 ns，后 30 ns 测量；已测进位频率方向正确，返回相同码的频率差最大 **{max(abs(x[k]) for x in dyn for k in ['return_zero_fraction','return_255_fraction'])*100:.4f}%**，最小代理负载差分峰峰值 **{min(y['diff_pp_v'] for x in dyn for y in x['points']):.3f} V**。这是所列转换检查，不是任意位偏斜、全码和失配签核。见 [动态验证](results/dynamic_validation.json)。

三个关键加载工作点额外测量 0.2/0.4/0.6/0.8/1.0 V，频率随控制电压单调增加，每点均正常分频。Kvco 明显非线性，以下是相邻测量点间的平均斜率，不能继续沿用旧模型的固定增益。

| 工作点 | 四个区间的 Kvco（MHz/V，按控制电压递增） |
|---|---|
{kv_table}

![关键点细调曲线](figures/fine_tuning.png)

公开入口的默认参数还单独与显式 R2 参数实例比较，载频差 **{a['public_defaults']['frequency_difference_hz']:.3f} Hz**，避免交付入口与实际仿真参数不一致。见 [辅助验证](results/auxiliary_validation.json)。

## 实际器件噪声与功耗

下面是固定控制 0.6 V、每侧 140 fF 代理负载的自主 PSS/Pnoise。实际 PDK MOS、nmoscap 和电感 RLC 电阻均参与器件噪声；IREF 电流源仍理想。使用差分载波和 PM noise 计算 SSB 相噪，逐项源 PSD 求和与总量核对一致。

| 配对角 | 粗调码 | 实测载频（GHz） | 1 MHz 相噪（dBc/Hz） | VCO 功耗（mW） |
|---|---:|---:|---:|---:|
{noise_table}

![相位噪声](figures/phase_noise.png)

另将实际 ÷4 分频和采样输入接入，参考固定低电平，使采样器保持**跟踪状态**，CP 输出钳位。自主 PSS 以分频输出为基频，VCO 选第 4 谐波：载频 **{loaded['frequency_hz']/1e9:.6f} GHz**，1 MHz 相噪 **{loaded['phase_noise_dbc_hz']['1000000.0']:.3f} dBc/Hz**。这是固定跟踪状态的加载诊断，既不是周期采样噪声，也不是 PLL 抖动；不能把它直接当作 984 MHz 锁定系统结果。

在该加载工作点，1 MHz 噪声贡献约为：交叉耦合核心 {loaded['fractions_1mhz']['cross_coupled_core']*100:.1f}%，电感 RLC {loaded['fractions_1mhz']['inductor_RLC']*100:.1f}%，分频器含其输入偏置 {loaded['fractions_1mhz']['divider']*100:.1f}%，采样输入偏置网络 {loaded['fractions_1mhz']['sampler_bias_network']*100:.1f}%，采样开关 {loaded['fractions_1mhz']['sampler']*100:.1f}%。因此下一步必须研究接口对振荡器的反向噪声影响。

噪声数值复核：

{nprecision}

完整数据、贡献项和频带见 [noise_summary.json](results/noise_summary.json)、[noise_spectra.npz](results/noise_spectra.npz)。不将自由振荡器近载波噪声直接积分并宣称满足 10 kHz–fout/2 的整机 <200 fs 要求。

在 99 点两端实测窗口内，VCO 支路功耗范围 **{vco[0]:.3f}–{vco[1]:.3f} mW**；全部已连接测量支路为 **{branch[0]:.3f}–{branch[1]:.3f} mW**，已包含理想 IREF 从电源汲取的功率。后者没有重定时输出链、GHz 时钟接收、完整控制和实际基准发生器，不能当作 ≤4 mW 的完整 PLL 功耗。启动峰值、版图面积亦未签核。

![功耗范围](figures/power.png)

## 失败、数值陷阱与适用边界

- 原 v3 在 Q=5 下的失振记录保留；单纯增流或加入互补核心不足以同时满足摆幅、覆盖与供电余量。实验入口留在 blocks/vco_v4，推荐使用公开 R2 入口。
- R1 初步恢复振荡，但 FF 的粗调交界重叠过窄；R2 将固定电容从 20 fF 降为 10 fF、细调 nmoscap 宽度从 3 µm 增至 4.5 µm。旧 R1 频点不能冒充 R2 证据。
- 默认 Spectre X AX 会覆盖 maxstep。此前 SS 高端试验与严格 APS 差约数十 MHz；加 maxstep override 后匹配。未把默认 AX 的结果用于验收。
- 短窗口中的分频暂态未通过后，延长实际仿真及测量等待时间；没有放宽逐周期判据。所有失败搜索均保留。
- Q=3 的 SS 码 243 差分峰峰值约 2 µV，无法维持可用振荡；Q=8 又改变频率与摆幅。这是电感不确定性的敏感度试验，R2 仅在约定的 Q=5 假设下完成本轮验证。
- 部分桥接返回值含 `convergence failure` 字样，来自已恢复的初始 DC 尝试；通过与否另外检查最终日志、波形和输入哈希。历史 R1 加载噪声作业曾发生采集超时，远端随后完成；其原超时记录与恢复记录均保留，未重新标成 R2。
- 测试仅覆盖 TT27/SS60/FF0 配对角与 1.2 V，未覆盖完整工艺×温度×供电、失配、布线、器件端电压可靠性和面积。固定/阵列电容仍理想；电感没有 PDK/EM 几何保证，见 [来源和假设](../../sources/vco_v4_sources.md)。

## 复现与后续接口

所有输入快照、完整 Spectre 日志、PSF 与压缩波形位于项目 `research/runs/spectre_vco_v4/`。本轮索引收录 **{counts['total_records']}** 个运行记录，包括失败、取消和历史候选；运行数量不是通过数量。SHA-256 与最终错误数见 [原始证据清单](results/raw_manifest.json)，源码清单见 [source_manifest.json](results/source_manifest.json)。受限 PDK 模型没有复制到交付目录。

已有服务器环境下可用独立 run-id 复现，例如：

```text
python share/deliverables/integration/vco_v4/run_spectre.py --run-id replay_public --mode aps --cases r2_public_defaults
python share/deliverables/integration/vco_v4/run_spectre.py --run-id replay_low --mode ax --threads 2 --preset-override maxstep --cases r2_tt_k14_c243
python share/deliverables/integration/vco_v4/analyze.py --runs replay_public replay_low
```

`run_spectre.py --snapshot-run <原 run-id>` 可使用本地原始快照精确回放；它拒绝覆盖已有 run-id。`calibrate_channels.py` 是仿真台寻码，默认研究旧 R1；重跑 R2 须显式给 `--r2 --settled --guard-mhz 2` 并采用新的 tag。`summarize_final.py` 从原始波形重新验收本轮 99 点，`plot_results.py` 重建图表。

下一步先把实际摆幅和非线性 Kvco 回填到采样器/CP 工作点与环路模型，处理输入偏置/分频对 VCO 的噪声回注，再逐级接入现有 FLL/PLL 验证捕获和交接。偏置/基准发生器仍按既有约定后置；<200 fs、≤4 mW、<0.3 mm² 均保持未闭合状态。
'''
    (H/'README.md').write_text(text,encoding='utf-8',newline='\n')
    print('Rendered verified R2 README')

if __name__=='__main__':main()
