# 噪声验证电路与实际LC候选的对应关系

2026-10-04。**局部尺寸优化已验证的是旧分频器负载；采用修复后的分频器之前，须重新测量相应噪声。** 两份电路并非只换了文件名：`bank_pulsetrip_v14`连续驱动部分支路时钟，使用单相环寄存器，并改变PB1尺寸比例，内部活动与RF时钟负载均不同。

| 验证对象 | 分频器 | 输出链 | 振荡源／环路 | 当前证据 |
|---|---|---|---|---|
| 当前完整`pll_capture_v14` | `cmos_even_bank_acq_v14` | 原尺寸 | 实际LC＋完整控制 | 4ps TT单点捕获／保持；1ps捕获仍运行 |
| 既有局部尺寸与noise-on | `cmos_even_bank_acq_v14` | 原／RT2／RT4 | 无噪声零阻抗RF波形重放 | 暂定141.281／90.867／63.275fs；不是完整PLL |
| 实际LC四组对照 | `bank_pulsetrip_v14` | 原／RT4，CF10／40 | 实际LC采样环，慢控制静态 | 基线通过；RT4及组合滑相；CF40漂移超筛选 |
| 新局部噪声对照 | `bank_pulsetrip_v14` | RT2／RT4 | 同一无噪声RF重放 | 两例六频点fresh PSS运行中，未得结果 |

新局部测试从各自已经验证的0.5ps／767边带／maxacfreq504GHz输入生成，只替换分频器include与实例类型；接收器、重定时器、输出缓冲、静默计数器负载、1.2V、TT27及10fF均保持。分析将核对除该分频器外的物理依赖SHA完全相同，再检查周期、支路频率、输出沿、端点、器件PSD总和及对应频点变化。

先前RT2的五组fresh noise-on与六沿三点全部通过；五个独立PSD之和与全噪声最大相对差4.44e-16。RT4已通过触发器／缓冲／接收器三组，其余继续。**这些是旧分频器电路的归因证据，不能自动标成新电路的归因验证。** 三点或六点谱比较也不产生全带RMS。

两例新测试占用RT2审计释放的同一个单线程长任务槽位，不增加并发。协议同时保留新电路全带测试台，但必须先审阅六点结果，尚无自动全带接续。先前准备的旧分频器全带加密测试暂缓，避免继续把旧负载结果当作新候选的结果。

即使新局部链改善保持，仍须修复RT4代回实际LC的工作点，并取得实际噪声LC闭环结果。主PLL尚未采用这些候选，旧数据保留原条件。

证据及复现：[对应协议](results/rt_pulsetrip_noise_protocol.json)、[新结果](results/rt_pulsetrip_noise_validation.json)、[RT2 noise-on](results/rt2_fine_audit_validation.json)、[构建入口](build_rt_pulsetrip_noise.py)、[分析入口](analyze_rt_pulsetrip_noise.py)。本项目实时接续记录为`research/rt_pulsetrip_noise_pipeline.json`。
