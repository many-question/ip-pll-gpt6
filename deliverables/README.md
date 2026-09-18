# 交付物索引

2026-09-18：已进入 TSMC180 PDK 晶体管模块与逐级混合顶层验证。参考/输出缓冲、采样保持、滤波预充、重定时及跨导级已逐级代回；LC VCO、CML ÷2 有联合负载候选。尚未完成全晶体管 PLL；实际增益已暴露原抖动预算的风险，不能沿用行为候选 B 的估算宣称达标。

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
