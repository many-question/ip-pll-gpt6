# 模块 Verilog-A 行为模型

模型按主反馈路径拆分，便于后续逐块替换晶体管实现。全部源码是本项目新建的行为代码，不含 PDK。

| 文件 | 功能及测试 |
|---|---|
| `reference_buffer.va` | 门限整形和有限转换时间；参考输入延迟测试 |
| `lc_vco.va` | 等电容粗调、线性细调及频率积分生成差分正弦和时钟；振荡边沿与解析频率交叉验证 |
| `subsampling_detector.va` | 在真实参考边沿采样 VCO 差分波形，生成延迟脉冲；采样值、脉宽与延迟测试 |
| `charge_pump.va` | 采样电压变为限幅电流；符号和每脉冲电荷测试 |
| `loop_filter.va` | 真实连续时间 R/C 微分方程、双电容预充和控制限幅；与 Spectre 原生 R/C 网络对照 |
| `auxiliary_fll.va` | 整数边沿计数、二分粗调、交接、频率确认和周期监视；独立计数测试与闭环顶层测试 |
| `even_divider.va` | 对称半周期计数，支持 ÷4/6/8/10/12/14；六种比值独立测试 |
| `output_retimer.va` | VCO 下降沿重定时、setup/hold 违例计数；名义和故意失败测试 |
| `output_buffer.va` | 延迟与 50 Ω 输出电阻，驱动临时 10 fF 负载；输出频率与摆幅测试 |
| `bias_control.va` | 由 1.2 V 产生 0.6 V 行为参考，为 VCO/FLL 提供中点；参考值测试 |
| `pll_monitor.va` | 仅用于 TB，独立测量实际输出边沿频率、占空比、相位采样及控制范围，不参与控制 |

`code`、`target`、`ratio`、`status`、`measured`、`freqmon` 和监视端口采用 electrical 类型传递整数或标度实数，不是物理电压总线：码/整数比为 1 V/单位，频率为 1 V/GHz。真实时钟及 enable/locked 为 0/1.2 V。

主环反馈为 `vp/vn → sample → charge_pump → ctrl → lc_vco`。FLL 只读取 VCO 时钟边沿数；输出来自该 VCO 的计数分频与重定时，不存在绕过反馈的目标频率输出源。

所有延迟、输出电阻、10 fF 负载、0.4 V 差分幅度和粗调范围均是明确的工作假设。模型含有限转换时间、10 Ω 预充和软限幅，用于验证行为连接和事件顺序。setup/hold 监视只报告违例，不模拟亚稳态概率与解析过程。VA 未注入随机噪声；不能由本轮瞬态波形证明 200 fs、杂散、功耗或面积。bias 模型也不提供真实供电电流。

顶层 TB、运行脚本和测量脚本见 `../../integration/va_v1/`。证据等级保持 `behavioral_sim`，即使这些模型由 Spectre 电路仿真器求解。
