本次快照：[第86次汇报](../reports/2026-10-10T0859.yaml)。RT4候选0.5ps seed29重跑正常完成并经独立复算，高偏移诊断为112.993992fs，RT4两步长×两种子矩阵补齐。原版100fA旧传输任务退出141、raw截断，已保留失败证据并派发输入完全相同的SSD隔离传输重跑。全带抖动仍未验收。

- [真实LC候选工作点](integration/cmos_v14_full/ACTUAL_LC_CANDIDATE_REVIEW.md)
- [参考负载隔离](integration/cmos_v14_full/REFERENCE_LOADING_DIAGNOSIS.md)
- [内部状态与PSS诊断](integration/cmos_v14_full/CORE_STATE_DIAGNOSIS.md)

本次快照：[第34次汇报](../reports/2026-10-04T0619.yaml)。局部4倍CMOS链暂定63.275 fs，自身六沿检查通过；真实LC发现约−28.8 dBc参考调制，固定控制隔离与MOS补偿候选已准备。完整PLL RMS仍未知，功耗优化暂缓。

- [噪声／抖动当前证据](integration/cmos_v14_full/NOISE_PROGRESS.md)
- [参考采样负载诊断](integration/cmos_v14_full/REFERENCE_LOADING_DIAGNOSIS.md)

本次快照：[第28次汇报](../reports/2026-10-04T0045.yaml)：噪声优先，PSS失败审计与恢复、CMOS输出链尺寸实验；功耗优化暂缓。

# 交付物索引

2026-10-03（第27份快照）：完整V14完成36µs终态保持，32µs控制周期总功耗5.667mW超限。SS已定位电平恢复和门控负载问题，独立候选继续验证；严格复位、完整噪声与频率范围尚未验收。

- [最新指标与模块状态](integration/cmos_v14_full/STATUS.md)
- [完整保持与功耗](integration/cmos_v14_full/REPAIR.md)
- [SS时序与电平诊断](integration/cmos_v14_full/SS_TIMING.md)
- [抖动验证进展](integration/cmos_v14_full/NOISE_PROGRESS.md)
- [第27份完整状态快照](../reports/2026-10-03T1826.yaml)

2026-10-03（第26份快照）：补SS实际接口与闭环抖动验证。新分频候选理想RF三角六档18例全通过，但MOS接收器下SS仍有三档失败，尚未代回PLL。核心PSS稳定段滑相，已保留负结果并补参考负载及实际粗调DFF驱动；整机抖动仍未知。严格捕获/周期功耗继续。

- [SS时序修复与实际RF回归](integration/cmos_v14_full/SS_TIMING.md)
- [抖动验证进展与前置问题](integration/cmos_v14_full/NOISE_PROGRESS.md)
- [第26份完整状态快照](../reports/2026-10-03T1456.yaml)

2026-10-03（第25份快照）：按用户要求梳理12条需求、14个模块及系统验证覆盖。电路已补齐，完整严格捕获、SS分频、低端范围、整机噪声与功耗/面积验收仍有缺口；本次没有新增性能通过结论。

- [指标与模块状态总览](integration/cmos_v14_full/STATUS.md)
- [第25份完整状态快照](../reports/2026-10-03T1308.yaml)

2026-10-03（第24份快照）：完整修复PLL在TT/K41、4ps精度下完成64µs独立复位捕获，qualified在56.502µs建立；末1µs全部供电5.623mW超限。严格精度切换诊断触发重启，尚无数值收敛证明，已启动全程1ps严格复位重跑。SS理想时钟隔离取得进展，实际器件修复仍未通过。

- [本轮结果、精度边界与后续仿真](integration/cmos_v14_full/REPAIR.md)
- [第24份完整状态快照](../reports/2026-10-03T1240.yaml)

2026-10-03（第23份快照）：新FLL／首次捕获监督已实现MOS并通过TT/SS/FF六组单位TB；完整17,644MOS修复版正在独立复位仿真。整机捕获尚待完成；SS时钟和状态传播已有定位，尚未整体修复。

- [捕获修复与验证边界](integration/cmos_v14_full/REPAIR.md)
- [第23份完整状态快照](../reports/2026-10-03T0020.yaml)

2026-10-02（第22份快照）：完整物理V14的复位、TT/SS近锁定及输出链细网格噪声结果已回收。自主复位筛选未通过，TT/SS近锁定及qualified建立通过；功耗和频率覆盖存在缺口，完整PLL抖动仍未验收。

- [完整电路首轮结果与逐项指标](integration/cmos_v14_full/BASELINE.md)
- [第22份完整状态快照](../reports/2026-10-02T2233.yaml)

2026-10-02（第21份快照）：完整物理V14的复位、TT/SS近锁定及输出链粗网格噪声结果已回收。自主复位筛选未通过，TT/SS近锁定及qualified建立通过；功耗和频率覆盖存在缺口，完整PLL抖动仍未验收。

- [完整电路首轮结果与逐项指标](integration/cmos_v14_full/BASELINE.md)
- [第21份完整状态快照](../reports/2026-10-02T2127.yaml)

2026-10-02（第20份阶段快照）：完整V14的TT **1ps严格近锁定主环通过**，静默监督窗口整机功耗 **5.616mW**。本版输出链首个上升沿10kHz–492MHz实际器件噪声 **141.222fs**，数值加密未完且不代表整机抖动。独立复位捕获、SS完整电路和新监督初态TT测试仍在进行。

- [完整电路与验证边界](integration/cmos_v14_full/README.md)
- [局部输出链噪声曲线](integration/cmos_v14_full/results/figures/chain_noise_spectrum.png)
- [第20份完整状态快照](../reports/2026-10-02T1938.yaml)

2026-10-02（第19份阶段快照）：完整可编程 V14 在 TT、984 MHz 的 8 µs 近锁定轨迹末段通过功能稳定性筛选，整机窗口功耗 **5.794 mW** 超标。新偏置 12 个加载端点完成，最低端点 **2.734–2.758 GHz** 未包围 2.688 GHz；SS低端÷14失败。独立复位捕获、严格精度与本版输出链噪声继续验证，尚未完成整机验收。

- [本版完整电路、近锁定结果与限制](integration/cmos_v14_full/README.md)
- [近锁定完整轨迹](integration/cmos_v14_full/results/figures/complete_warm_joined.png)
- [第19份完整状态快照](../reports/2026-10-02T1808.yaml)

2026-10-02（第18份阶段快照）：补齐真实偏置、物理相位／振幅检测、六档 CMOS 分频和 RF÷4 FLL，建立 **13,394 MOS 的完整可编程 PLL 顶层**。TT 六档分频＋重定时通过，SS 三档仍失败。完整单通道近锁定测试有锁定指示但残余相位漂移未通过筛选，静默监督窗口功耗 **5.105565 mW**；可编程整机冷启动和长接管测试仍在运行。结构完成不等于整机验收完成。

- [完整晶体管集成、实验结果与限制](integration/cmos_v14_full/README.md)
- [完整可编程网表](blocks/cmos_v14_full/pll_complete_v14.scs)
- [完整周期与噪声测量边界](integration/cmos_v14_full/results/noise_period_boundary.md)
- [第18份完整状态快照](../reports/2026-10-02T1639.yaml)

2026-10-02（第17份快照）：完成**当前最佳候选、逐模块TB/PVT与整机指标审计**，未新增仿真。明确v14跨角功能、v13数字链噪声和旧真实LC主环属于不同版本；当前没有统一版本的完整PLL达标证据，功耗已超预算，相位/振幅检测及真实基准仍未完成。

- [逐模块状态、整机连接范围和REQ-01…12逐条对照](verification/status_audit_2026-10-02.md)
- [第17份完整状态快照](../reports/2026-10-02T1344.yaml)

2026-10-02（第16份快照）：实际LC驱动下 **SS60恢复正确÷4**；较轻候选180µA输出约983.85MHz，测试电路 **4.3946mW，仍超4mW预算**。0.5ps、1µs反向微扰与TT27/FF0定点功能通过；v14噪声未验证，旧126.892fs不可沿用。

- [SS故障机制、修复及实际LC证据](integration/cmos_v14/README.md)
- [候选电路与试案边界](blocks/cmos_v14/README.md)
- [第16份完整状态快照](../reports/2026-10-02T1330.yaml)

2026-10-02（第15份快照）：局部CMOS优化将TT数字链抖动由181.186降至 **126.892fs（−29.97%）**，加密和独立noise-on通过。实际LC接回后TT正确÷4、测试电路约 **3.24mW**；真实LC慢角100/120µA仍漏计，未作完整PLL/PVT签核。

- [电路改动、受控降噪与慢角故障证据](integration/cmos_v13/README.md)
- [当前候选和保留试案](blocks/cmos_v13/README.md)
- [第15份完整状态快照](../reports/2026-10-02T0414.yaml)

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
