"""Build output-clock research summary from all completed cases."""
import json
from analyze import H
def main():
 rows=json.loads((H/'results/validation.json').read_text());noise=json.loads((H/'results/noise_validation.json').read_text())
 text='''# 实际 GHz 时钟接收与输出重定时链

2026-10-01。把实际晶体管 RF 接收器接到原 C2MOS 重定时器，和真实钳位分频器一起验证。**镜像负载接收器能通过 TT 翻转筛选，但器件噪声明显超标；直接AC四级链的单次噪声估算更差，两者都不能作为合格输出链。** 未冻结或采用新方案。

## 条件与功能范围

TT27、1.2 V、3.936 GHz 理想无噪声电压回放、÷4、984 MHz 输出、10 fF。RF 形状来自已有 `interface_v5/tank_waveform_v5.va`，单端约1.004–1.369 V，沿用其来源记录。理想电压源没有真实VCO阻抗、噪声或负载回注，因此还未代回真实LC主环路。器件使用同一TSMC180BCD模型和stat_noise；电容、电阻为原理图理想元件，IREF发生器仍理想。

全链供电积分同时包含分频器、RF接收器、重定时器和末级缓冲；支路VRX/VRT用于分解。缺VCO、主环路、FLL/监督和实际基准，不把不同TB功耗简单相加作整机验收。输出10 fF仍是临时工作假设。

功能协议在运行前记录：100 ns瞬态，末70–100 ns检查clk/data/out频率、最大周期误差及逻辑摆幅。高电平>1 V、低电平<0.2 V、平均频差<0.1%、最大周期误差<2%，输出沿数>20。[初始协议](results/protocol.json)及各轮协议保留，不用低摆幅或不翻转时的低功耗作为有效工作点。

分析器曾额外尝试在时钟下降沿后0.35个RF周期（约89 ps）读输出，但实际传播延迟可达数百ps，这不是有效的数据正确性判据。该诊断从未写入原协议；现仍保留读数并明确不用于验收。当前通过只代表频率/周期/摆幅，未证明任意数据重定时、setup/hold、亚稳态或全PVT。

## 电路试案与全部功能结果

原三反相器直流链在实际GHz负载下摆幅衰减；再生负载试案存在偏置或锁存问题。镜像负载差分输入级可产生摆幅，但直接串接的反相器偏置不合适。逐级交流耦合、阻性反馈自偏置的四级增益链随后通过TT波形筛选。根据器件噪声归因，再尝试取消电流镜前端、直接交流耦合RF到四级增益链。各版本与阴性结果均保留。

| 试案 | 功能筛选 | GHz时钟范围 V | 同台全链 mW | 接收器 mW | 重定时/缓冲 mW |
|---|---|---|---:|---:|---:|
'''
 for r in rows:
  if 'transient' not in r:continue
  w=r['transient'];p=w['power_mw'];lo,hi=w['signals']['clk']['range_v']
  text+=f"| {r['case']} | {'通过' if w['pass_function'] else '失败'} | {lo:.3f}–{hi:.3f} | {p['VDD:p']:.6f} | {p['VRX:p']:.6f} | {p['VRT:p']:.6f} |\n"
 text+='''
完整读数及几何时序距离见[功能结果](results/validation.json)。首轮镜像接收器使用NMOS输入对8 µm、PMOS镜像负载4 µm、40 µA理想参考/5倍尾电流镜，输入AC120 fF、50 kΩ偏置及10 pF共模去耦。四级小尺寸增益链每级NMOS2 µm/PMOS5 µm，AC200 fF及50 kΩ反馈，末驱动尺寸2倍。C2MOS scale=2，输出oscale=4、sp=2.5 µm。

## 器件噪声与数值检查

PSS基频984 MHz，检查1个输出/数据周期、4个GHz时钟周期、主谐波及保存电压端点误差<1 mV；随后按0.6 V输出上升沿作fullspectrum sampled pnoise，sampleratio=1，10 kHz–492 MHz。对照1 ps/63谐波/63边带和0.5 ps/127/127，积分变化<1%、最大谱差<0.1 dB才通过数值加密。maxsideband控制fullspectrum中的有色噪声项。

总out为V/√Hz，显式积分out²/边沿斜率²，并与Jee交叉核对。器件STRUCT内的total为PSD，单独读取并检查分项之和；不把平面解析器无法解析的NaN当成零。以器件总PSD积分形成各模块的方差贡献，不能把分项RMS线性相加。

| 噪声试案 | 周期及积分有效 | 抖动 fs | 同台全链 mW |
|---|---|---:|---:|
'''
 for r in noise['cases']:
  if 'numeric_jitter_fs' not in r:continue
  text+=f"| {r['case']} | {r['valid_noise']} | {r['numeric_jitter_fs']:.3f} | {r['periodic']['power_mw']['VDD:p']:.6f} |\n"
 text+='\n镜像小尺寸候选的联合加密结果：`'+json.dumps(noise['precision'],ensure_ascii=False)+'`。直接AC四级链若只有单点噪声，则只作探索结果，不能继承此数值加密。\n\n![镜像候选周期波形](figures/periodic_output.png)\n\n![输出采样噪声](figures/sampled_noise.png)\n'
 for r in noise['cases']:
  if not r.get('noise_budget_valid'):continue
  text+=f"\n{r['case']} 的模块等效RMS（均折到最终输出）："+'；'.join(f"{k} {v['jitter_fs']:.2f} fs，占方差{v['variance_fraction']*100:.5f}%" for k,v in r['noise_by_instance'].items())+'。\n'
 text+='''
镜像候选主要瓶颈在RF接收器；分频数据噪声的输出贡献较小，并不代表整条重定时链达标。该工作点重定时/缓冲本身仍约228 fs，已经高于200 fs；不能认为只消除接收器噪声就达标，也需要改善实际时钟斜率、相位和重定时尺寸/负载。直接AC大尺寸约30 ps，首级反相器和反馈电阻占主导，未得到降噪收益。它与镜像候选的增益级尺寸、相位均不同，不能作单变量归因。

这些是PSS工作点附近的线性化噪声估算。尤其30 ps已足以使小扰动假设值得怀疑，不把该数值当成真实大信号随机抖动测量；但它没有提供接近200 fs的证据，因此不继续将该候选代回VCO。接收器带宽/增益峰值、扰动稳定性与时钟相位还需先检查。旧理想满摆幅时钟驱动的约百fs重定时结果不能移植到此实际接收器。每个试案的器件排行、带宽、端点与频谱见[噪声结果](results/noise_validation.json)，原判据见[噪声协议](results/noise_protocol.json)。

## 复现与下一步

原始PSF、日志、不可覆盖输入快照和终态在项目 `research/runs/spectre_output_v8/`；[原始证据清单](results/raw_manifest.json)记录本地路径/哈希、实际结束状态和求解耗时。[源码清单](results/source_manifest.json)只包含项目自有网表和脚本，PDK未复制到交付区。

```text
python share/deliverables/integration/output_v8/run_spectre.py --run-id replay_output1 --cases mirror_gain4small_tt --mode ax --threads 1 --preset-override all
python share/deliverables/integration/output_v8/analyze.py
python share/deliverables/integration/output_v8/analyze_noise.py
python share/deliverables/integration/output_v8/summarize.py
python share/deliverables/integration/output_v8/package_evidence.py
```

按噪声归因缩短RF信号通路、检查直接AC限幅链及重定时的时钟相位/有效建立时间；先通过TT功能、器件噪声和同台功耗，再代回实际VCO重新检查负载、调谐和周期工作点。此后补频点与角落、FLL自动接管和完整功耗。当前<200 fs、≤4 mW、<0.3 mm²均未整机签核。完整项目状态以最新报告为准。
'''
 (H/'README.md').write_text(text,encoding='utf-8',newline='\n')
 (H/'results/summary.json').write_text(json.dumps(dict(functional_cases=len([r for r in rows if 'transient' in r]),functional_pass=[r['case'] for r in rows if r.get('transient',{}).get('pass_function')],noise=noise,scope='TT ideal-input fixture only; no full PLL signoff or candidate adoption.'),indent=2,allow_nan=False)+'\n')
 print('Wrote output-chain summary')
if __name__=='__main__':main()
