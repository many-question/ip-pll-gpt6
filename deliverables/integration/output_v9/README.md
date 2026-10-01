# output_v9：差分重定时、时序敏感度与器件噪声

本轮从 output_v8 的实际 GHz 接收链噪声瓶颈出发，改为直接使用小摆幅差分 RF 驱动 CML 重定时，在 984 MHz 输出端恢复 CMOS 电平。所有候选均为研究电路，未获采用决定；完整 PLL 的 200 fs、4 mW 和面积目标仍未闭合。

**加密后的较好候选为原极性双级 CML、scale2：792.149 fs，已连接分频/CML/输出共 1.723996 mW，其中 CML/输出支路 1.007517 mW。** 与 1 ps/63 初轮相比，0.5 ps/127 联合加密的积分变化为 −0.1051%、最大谱差 0.00916 dB，均通过预定数值检查。与历史 output_v8 镜像接收链 8410.26 fs 相比有所改善，但两者拓扑与内部加载不同，不能归因为单个尺寸或极性改动。

本轮共 **43 组**记录：16 组实体功能试案（12 通过）、18 组数据回放诊断、9 组 PSS/噪声（1 组 PSS 失败，8 组测量有效；仅上述候选完成联合加密）。有效测量不代表满足 200 fs。

加密候选中，分频器折到最终输出的贡献为 498.624 fs；主锁存器 327.761 fs、从锁存器 366.692 fs、输出四级恢复 354.670 fs，其他重定时偏置/无源约 105.799 fs，按方差相加。约 85.97% 方差位于 100–492 MHz，单纯改善低频闪烁噪声不足以达标。锁存器时序敏感度亦未达内部目标，下一轮需同时改善数据稳定程度和附加宽带噪声。

## 条件与测量

TT27、1.2 V，理想无噪声 3.936 GHz 电压形状源，实际六档实体钳位分频器选择 /4，最终负载 10 fF。原始差分输出增加负端选择传输门并去掉原 CMOS 恢复链，因此改变了负载，旧 VCO 码表及分频 PVT 不自动继承。主环路、实际 VCO 源阻抗和噪声、FLL/监督及偏置发生器未纳入。

瞬态按预先保存的 [protocol](results/protocol.json) 检查频率、周期、摆幅及持续边沿；CML 时钟本来就是差分模拟输入，不要求其达到 CMOS 电源轨。通过这些检查不表示已抑制数据抖动。

噪声采用 984 MHz PSS、ratio1、输出 0.6 V 上升沿，显式积分 **10 kHz–492 MHz** 的 ASD²/slew²，并核对 Jee。每个 PSS 独立检查周期边沿数、主谐波、摆幅及端点一致性。粗网格为 1 ps/63 谐波/63 有色噪声边带，加密为 0.5 ps/127/127；预定门限为积分差 <1%、最大谱差 <0.1 dB。全频谱方法开启，不把有色噪声边带参数说成所有白噪声的硬截止。

使用安装版 Spectre 21.1.0.509.isr12，裸 `-preset_override`；以实际日志为准：reltol=1e−5、100 nV/100 fA、traponly、relref=sigglobal。日志仍显示 moderate 标签，不声称 conservative 标签被采用。器件 PSF STRUCT 的 total 是 PSD、out 是 ASD；只有器件贡献求和与 out² 吻合后才解释归因。

## 本轮实验与失败

1. 直接四级 AC 链的反馈电阻从 50 kΩ 降至 5/2/1 kΩ。50 kΩ 时钟摆幅约 0.071–1.109 V；较低三档均失去有效逻辑摆幅，所以没有继续噪声测量。低功耗失败电路不计为改善，也不能证明原低频噪声增益假设成立。
2. 导出原始差分分频信号后接单级/两级 CML。单级同相首轮 977.67 fs，单级反相 2558.30 fs；两级原极性、scale2 首轮 792.98 fs。原极性两级中分频器仍贡献约 499 fs，重定时及输出合计约 616 fs，均折到最终输出、按方差相加。
3. 用差分再生接收器替代最终四级 AC 链。小尺寸 a 输出锁在高电平，功能失败；b 瞬态功能通过但 PSS 30 次迭代未收敛；c 的首轮有效噪声约 1073.81 fs，没有优于四级输出链。
4. 对调两级 CML 的 RF 差分时钟极性，保持真实分频器不变，以检验数据稳定时间假设。普通四级输出链变为 1088.19 fs；再生 b/c 反相版本分别为 1363.69/1403.44 fs，均未改善。上述噪声是首轮探索测量；最新加密状态以 [noise_table](results/noise_table.md)、[noise_validation](results/noise_validation.json) 和 [summary](results/summary.json) 为准。

各试案具体器件尺寸、功耗、噪声贡献和失败记录均保留；没有删除失败 TB 或以收敛状态替代物理检查。

## 时序诊断

将真实分频器一整周期的差分数据拟合成 63 谐波理想回放源，分别移位 −10/0/+10 ps，实际重定时器和 RF 时钟不变。拟合误差需 <0.5 mV，零移位输出须与真实分频夹具相差 <2 ps，实际数据移位差需为 20±0.2 ps，才允许解释有限差分增益。

单级同相和反相的回放均合格，但输出/输入时移增益分别约 0.54/0.50 和 2.02/2.09（上升/下降），没有达到内部研究目标 |gain|<0.1。单级反相波形在接近零差分电压处延迟，频率正确不足以证明重定时有效。

双级 scale2 普通输出链原极性/反相回放也合格，增益分别约 0.44/0.41 与 0.55/0.54。相位调整没有得到足够的数据扰动抑制，这与输出中仍有明显分频器噪声贡献的观察一致；两项测试不等价，不以有限确定性扰动换算随机抖动。

再生 b 原极性及反相版本的零移位输出未与实体夹具吻合，因此它们的回放敏感度不具备解释资格。这可能涉及输出状态与微小负载/波形差异，但本轮未作单因素归因。所有诊断记录见 [timing_validation](results/timing_validation.json)。回放没有实际分频器阻抗、噪声和双向耦合，其功耗也不包含分频器，不能当作输出链功耗。

## 证据与复现

- [功能比较表](results/function_table.md)、[噪声比较表](results/noise_table.md)、[时序资格与敏感度表](results/timing_table.md)。
- [波形与功能检查](results/validation.json)、[噪声检查](results/noise_validation.json)、[时序检查](results/timing_validation.json)、[汇总](results/summary.json)。
- [电路说明](../../blocks/output_v9/README.md)、[来源和测量依据](../../sources/output_v9_sources.md)。
- [时序波形图](figures/cml_phase_waveforms.png)、[噪声谱图](figures/noise_comparison.png)。
- [联合加密对照图](figures/precision_comparison.png)、[PSS/瞬态相对 RF 边沿检查](results/orbit_comparison.json)。相位比较按一个 RF 周期取模，不证明绝对分频初相一致。
- [原始记录及 SHA-256](results/raw_manifest.json)、[源文件清单](results/source_manifest.json)。完整原始 PSF/日志/输入在项目 `research/runs/spectre_output_v9/<run>/<case>/`；远端在指定项目 `simulation/output_v9` 下；PDK 未复制入交付目录。

在项目根目录，已安装的 Python/virtuoso-bridge 环境下，例如：

```text
python share/deliverables/integration/output_v9/run_spectre.py --run-id reproduce01 --cases cml2_opp_s2_tt --mode ax --threads 1 --preset-override all --timeout 1800
python share/deliverables/integration/output_v9/analyze.py
python share/deliverables/integration/output_v9/analyze_noise.py
python share/deliverables/integration/output_v9/analyze_timing.py
python share/deliverables/integration/output_v9/compare_orbits.py
python share/deliverables/integration/output_v9/summarize.py
python share/deliverables/integration/output_v9/plot_results.py
python share/deliverables/integration/output_v9/package_evidence.py
```

新运行 ID 必须唯一；构建器拒绝覆盖同名 TB。精确复现实验时使用 raw_manifest 对应的不可变输入及 runner 的 `--snapshot-run`。分析默认需要本项目已回收数据；仅下载交付仓库没有大体积原始 PSF，需按清单重新运行。原始数据不能由服务器作为唯一保存位置。

下一步优先依据锁存器、输出恢复级和分频器的贡献改善数据稳定程度、输出斜率与附加噪声；达到有意义的模块预算后代回真实 VCO，核对加载、全带抖动和同台总功耗。旧 Q=3 慢角失振、FF K14 余量、完整 FLL、实际无源和面积风险保持开放。
