# 核心 PSS 的电源探针初态修复

2026-10-04。这是仿真初始化问题的已完成诊断，**不是完整 PLL 抖动通过，也尚未证明 PSS 收敛问题全部解决**。主 `pll_capture_v14.scs` 电路没有修改。

## 已观察到的问题

真实 LC／采样环／连续时钟分频候选的 `coretripsettle01` 瞬态没有保存三个支路电流。Spectre 消除了零伏探针连接的电源节点，因此终态文本不含 `XP.vco_vdd`、`XP.rx_vdd`、`XP.rt_vdd`。后续 PSS 为记录电流保留这些节点，但使用 `skipdc=yes` 读取同一份不完整初态，未列出的节点从 0 V 开始。

未修正的 `coretripnoise01` 最初出现总供电约 209.364 A 的数值尖峰，首轮 shooting 报告 `max dV(XP.rt_vdd)=1.2V`、范数 `5.52e6`。为隔离该问题，在首轮之后主动 SIGINT 停止。随后日志先报告 SPECTRE-25，再报告 SPECTRE-18；后者发生在停止之后。1.927 GB 稳定段已回收并记录 SHA。不能把这次主动停止写成已经证明电路不能收敛。

## 单变量 A/B 证据

两个 10 ns 测试使用相同电路、输入、求解器、保存节点和原始状态。修正组只新增三个电源电压初值 1.2 V，其值由零伏源连接约束确定；其余初态逐项相同。

| 观测 | 原初态 | 补齐三个节点 |
|---|---:|---:|
| 三个支路电源初始电压 | 0 V | 1.2 V |
| 最初 10 ps 总供电绝对峰值 | 209.364 A | 5.661 mA |
| 整段 10 ns 总供电绝对峰值 | 209.364 A | 22.001 mA |
| 100 ps 后总供电绝对峰值 | 21.953 mA | 22.001 mA |
| 重定时器内部 `qb` 最大电压 | 1.901 V | 1.352 V |

两个测试均完成且 0 error。结果确认异常初始化尖峰被去除，不能把原尖峰作为正常功耗或器件应力结论。这里的电流峰值用于定位初始化原因，不是功耗优化结果。

证据：[A/B 结果](results/core_seed_probe_validation.json)、[停止与回收审计](results/core_seed_cancellation_audit.json)。原始数据：`research/runs/spectre_cmos_v14_full/coreseedcheck01` 和 `coretripnoise01`；复现入口 `build_core_seed_probe_check.py`、`analyze_core_seed_probe_check.py`、`analyze_core_seed_cancellation.py`。

## 修正后正在验证的内容

`coretripsupply01/core_pulsetrip_supply_noise_tt` 仅更换初态文件，电路、保存量和求解器保持相同：TT27、1.2 V、Q5 RLC、K41/M4、10 fF，静态慢控制边界；4 MHz fresh PSS、250 ns 周期、1 µs 稳定段、1 ps／reltol1e-5、traponly。04:21 的只读进度检查确认最初 5 ns 总供电绝对峰值约 22.028 mA，没有重现 209 A 尖峰；这仍只是进度观测。

后续必须分别通过：PSS 实际残差收敛、各运行分频支路和参考的周期一致性、246 个输出上升沿、所有已保存电压端点及粗调寄存器保持、实际器件噪声求和。当前六个偏移频点只是可行性与归因探针，不能积分为 RMS。核心还采用原重定时器与 CF10，未合并 4 倍输出链或 CF40 候选。

使用 `analyze_closedloop_noise.py coretripnoise01 coretripsupply01 --output core_supply_noise_validation.json`。该分析器要求完成日志与 fresh PSS，通过周期及噪声门槛后才允许计算足够密的全带积分；失败结果保留但不产生 RMS。全频带、边沿、数值、逐模块 noise-on 及完整控制边界仍需补齐。

以后由瞬态生成 PSS 初态时，应保持相关电流探针的保存配置一致，并核查保留下来的理想电压约束节点有完整初值。补齐理想电源节点不授权猜测电容、锁存或电感等动态状态。

## 后续结果：初态尖峰与周期收敛须分开（04:49）

补齐三个电源初值后，coretripsupply01已去除初始化尖峰，但周期残差3.7e6→75.3k→340k→2.1e6，未收敛；在四个残差后主动停止并回收。最后250ns各运行分支沿数正确、已检查电压端点差最大0.429mV，仍不是有效周期解。仅收紧线性求解itres=1e-6的同电路对照coretriplinear01已启动，最终准确度要求保持。新对照依据本地Spectre21.1 PSS帮助中itres的定义；它收紧每次Newton线性方程解的残差，未改变物理电路或最终周期误差门槛。线性求解误差是否为原因仍是假设。

证据：[修正初态后仍未收敛的审计](results/core_supply_trial_audit.json)、[单参数线性求解对照](results/core_linear_precision_protocol.json)。停止后先出现SPECTRE-25再出现SPECTRE-18；周期状态无效，PNoise没有运行。

## 05:29 的后续结果

收紧itres仍未恢复迭代收缩，在四次范数后主动停止并完整回收。新四次为3.7M／75.3k／340k／1.23M，无PNoise。冻结输入证实单变量变化；本次没有停止后的SPECTRE-18。见[审计](results/core_linear_trial_audit.json)和[逐周期漂移](results/core_period_drift.json)。6线程已转入四组真实LC候选短时对照，尚未启动另一次PSS。


## 晚初态与边界对照（08:19）

晚初态PSS完整日志五次残差3.71M/127k/335k/3.19M/2.34M，仍未收敛。08:12主动SIGINT，随后SPECTRE18，1.975GB稳定段回收校验。此前日志尾部漏掉首次，127k首轮及29倍改善的说法已撤回；监视工具改为保存完整残差历史。

晚初态轨迹相邻周期保存电压最大差0.851mV，不等于有效周期状态。仅tstab1us→1.134023us的边界对照已启动，实际波形选择降低边界逻辑最大斜率25.937→9.844GV/s；周期/电路/容差不变，收敛尚未证明。见[完整审计](results/core_late_trial_audit.json)和[第38次审阅](NOISE_REVIEW_38.md)。


## 边界负结果与方法对照（第39次）

仅改变周期边界的PSS五轮残差7.68M/262k/335k/1.17M/4.87M，仍无周期解。09:05精确SIGINT后SPECTRE18，2.187GB稳定段已回收并校验；保留负结果，不证明无周期解。

四组20ns实际MOS数值对照完成：梯形1ps/0.5ps的RX电流高频峰由约505GHz移到997GHz；Gear2没有相应分量。按0.125ps重采样，RT电流100–1500GHz能量占比分别0.4933%、2.3397%、0.0008335%、0.0008134%。这是确定性数值振铃证据，不是器件噪声或抖动。 已准备并排定方法单变量PSS：只改tstab及shooting积分方法为gear2only，其他电路、实际初态、1ps及容差保持；接替RT4边界点的长槽位。当前状态：running。六点不能积分为RMS，收敛后仍须步长与器件PSD复核。见[方法诊断](CORE_METHOD_DIAGNOSIS.md)。
