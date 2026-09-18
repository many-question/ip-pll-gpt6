# 交付物索引

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
