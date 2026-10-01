# 交付物索引

2026-10-02（第14份快照）：CMOS低摆幅单级接收器＋TSPC输出链加密 **181.186fs**，独立noise-on闭合。实际LC提高偏置参考至100µA后TT正确÷4，码21调谐端点包围3.936GHz，测试电路约 **3.21mW**；SS60接收器仍失效，完整PLL噪声/功耗未签核。

- [CMOS接口、实际LC加载与噪声证据](integration/cmos_v12/README.md)
- [新增CMOS电路及边界](blocks/cmos_v12/README.md)
- [第14份完整状态快照](../reports/2026-10-02T0237.yaml)
- [DEC-0006：继续推进CMOS方向](../reports/decisions/DEC-0006.md)

2026-10-02（第13份快照）：明确优先 CMOS。单元缓冲85.247fs、重定时加缓冲87.002fs；实体CMOS /4＋重定时/缓冲加密130.272fs/1.150115mW，反相时钟102.681fs/2.081006mW。直接链独立noise-on闭合；理想全摆幅RF前提，真实LC接口与完整PLL仍未签核。

- [内部边沿、CML工作点与CMOS输出链证据](integration/jitter_v11/README.md)
- [CMOS单元及失败试案](blocks/jitter_v11/README.md)
- [第13份完整状态快照](../reports/2026-10-02T0145.yaml)

2026-10-02（第12份快照）：逐模块noise-on确认输出链五分区贡献，独立方差闭合通过。仅输出恢复首级MOS宽度加倍，整链加密结果 621.903 fs、1.760363 mW；相对原细网格 792.149 fs 降低 21.49%。完整PLL、200fs和功耗/面积未签核。

- [独立噪声开关、单模块优化和完整证据](integration/noise_v10/README.md)
- [单模块电路改版](blocks/noise_v10/README.md)
- [第12份完整状态快照](../reports/2026-10-02T0101.yaml)

2026-10-01（第11份快照）：实现差分分频接口与CML重定时/984MHz输出恢复电路。两级CML原极性scale2输出链 792.149 fs；已连接分频/重定时/输出 1.723996 mW；联合加密积分变化 -0.1051%，最大谱差 0.00916 dB，判据通过。200fs与时序抑制仍未达标，尚未代回真实VCO；完整PLL功耗/噪声/面积未签核。

- [CML电路、时序扰动与器件噪声证据](integration/output_v9/README.md)
- [新增电路与接口说明](blocks/output_v9/README.md)
- [第11份完整状态快照](../reports/2026-10-01T2203.yaml)

2026-10-01（第10份快照）：真实LC固定码核心通过1ps/0.5ps接续精度，并获得有效PSS与长瞬态交叉核验。已把实际GHz接收器接到物理输出链；器件噪声暴露接收器瓶颈，候选尚不满足200fs。完整PLL功耗、噪声与面积未签核。

- [核心数值精度、周期点与采样积分校验](integration/accuracy_v7/README.md)
- [实际GHz接收/重定时电路及噪声证据](integration/output_v8/README.md)
- [接收器网表与适用边界](blocks/output_v8/README.md)
- [第10份完整状态快照](../reports/2026-10-01T1413.yaml)


2026-10-01：新增分频关断输入 MOS 钳位，六档规划频率静态分频 6/6 通过；真实 LC 严格容差闭环的 1 ps 功能精度复核未通过。五组完整终态启动的 PSS 尝试均未取得通过独立波形检查的真实 LC 闭环周期解。新接口仍为研究候选，完整 PLL 抖动、功耗和面积尚未签核。

- [严格容差闭环、DC、分频与周期证据](integration/closure_v6/README.md)
- [新增 MOS 钳位电路与边界](blocks/closure_v6/README.md)
- [第 9 份完整项目状态快照](../reports/2026-10-01T1205.yaml)

2026-09-30：完成 VCO 接口噪声对照和平均鉴相增益重提；四个真实 LC 闭环瞬态试案尚未通过本轮全部稳态筛选；恢复尝试后仍未取得通过独立波形筛选的闭环周期解。低阻接口单次降噪约 0.73 dB，但加密复核未收敛，FF 低端余量仍不足，暂不采用该候选；完整 PLL 尚未闭合。

- [接口器件噪声、增益与真实 LC 闭环证据](integration/interface_v5/README.md)
- [实验电路与参数边界](blocks/interface_v5/README.md)
- [第 8 份完整项目状态快照](../reports/2026-09-30T1055.yaml)


2026-09-19：VCO R2 在暂定 Q=5 电感 RLC、1.2 V 下恢复起振和所需频点覆盖，TT27/SS60/FF0 × 33 个目标共 99/99 个真实加载检查通过。已完成粗调切换、非线性细调和器件噪声复核；接口噪声回注、完整 PLL 抖动/功耗/面积仍未闭合，Q=3 慢角低端仍失振。偏置/基准继续后置。

- [VCO 修复、99 点码表、噪声与复现证据](integration/vco_v4/README.md)
- [VCO R2 参数与推荐网表入口](blocks/vco_v4/README.md)
- [本轮来源、数值设置和假设](sources/vco_v4_sources.md)
- [第 7 份完整项目状态快照](../reports/2026-09-19T0101.yaml)

上一阶段逻辑时序和电感模型：原 VCO 在 Q=5 下失振/覆盖不足的历史证据保留；本轮修复结果见上。

- [逻辑时序、混合闭环与电感 RLC 影响的本轮证据](integration/transistor_v3/README.md)
- [新增控制电路与电感模型的接口及边界](blocks/transistor_v3/README.md)
- [文献 Q、PDK 检查与综合来源](sources/transistor_v3_sources.md)
- [DEC-0005：逻辑时序优先，允许初步电感 RLC 建模](../reports/decisions/DEC-0005.md)

上一阶段分频、FLL 与器件噪声：

- [分频、FLL、器件噪声与逐级代回的本轮证据](integration/transistor_v2/README.md)
- [新增晶体管电路、接口和使用边界](blocks/transistor_v2/README.md)
- [实际使用的模型、Spectre 帮助与综合工具依据](sources/transistor_v2_sources.md)
- [DEC-0004：10 kHz–输出频率一半的抖动验收频带](../reports/decisions/DEC-0004.md)

上一阶段器件与混合系统基线：

- [晶体管实现、混合系统结果、失败记录和复现入口](integration/transistor_v1/README.md)
- [晶体管模块网表及接口边界](blocks/transistor_v1/README.md)
- [器件模型与电路依据](sources/transistor_v1_sources.md)
- [DEC-0003：占空比无需专门优化](../reports/decisions/DEC-0003.md)

行为模型基线：

- [Spectre 顶层、模块 TB、结果和复现入口](integration/va_v1/README.md)
- [十个功能模块的 Verilog-A](blocks/behavioral_va/README.md)
- [Python v2：有限计数 FLL、粗调、交接和重捕获](architecture/behavioral_v2/README.md)
- [本轮语言和工具依据](sources/va_model_sources.md)

- [系统指标拆解与工作预算 B](spec/system_budget_v1.md)
- [Python 行为模型、结果、验证及复现入口](architecture/behavioral_v1/README.md)
- [DEC-0002：先研究随机抖动与 Python 行为模型](../reports/decisions/DEC-0002.md)
- [本轮建模来源与自有推导](sources/behavioral_sources.md)

初始研究资料：

- [启动状态、目标和待澄清项](spec/startup_status.md)
- [首轮频率、LC 与抖动预算计算](architecture/initial_screen/README.md)：含输入、Python 脚本、CSV/JSON 结果和 SHA-256。
- [近期实验与验证计划](verification/initial_plan.md)
- [实际使用的一手来源](sources/initial_sources.md)
- [DEC-0001：已确认功耗/面积边界](../reports/decisions/DEC-0001.md)
- 完整状态快照位于 `reports/`，覆盖 REQ-01…REQ-12；已交付快照不再修改。

项目内部环境取证保存在 `research/startup/`，未将受限工艺模型或初始化脚本放入交付面。
