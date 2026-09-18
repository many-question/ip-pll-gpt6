# 分频、FLL 与器件噪声改进候选

本目录是电路研究候选，配套测试、结果和适用条件见 [验证说明](../../integration/transistor_v2/README.md)。MOS 引用项目实际配置的 TSMC180 BCD Gen2 模型；没有打包 PDK。电阻、电容、电感仍有理想模型，电流基准仍未器件化，不属于完整工艺实现或签核网表。

## 当前电路

| 文件 / 子电路 | 接口与实现 | 使用约束 |
|---|---|---|
| `bank_divider_v2.scs` / `tx_divider_bank` | `cp cn reset s2…s7 out vdd vss`；六个固定 Johnson 环，选通一组，实现 ÷4/6/8/10/12/14；CML 后接四级交流偏置限幅器 | `s2…s7` 对应 2…7 级环，必须单热；配置在复位时改变；未验证运行中切换。R3 的输入时钟 TG 为 4/16 µm，输入共模 1.0 V |
| `bank_divider_light.scs` / `tx_divider_bank_light` | R4：输入时钟 TG 改为 4/8 µm，减少 LC 负载，其他连接与 R3 一致 | 独立保留 R3，结果不可混用；最终覆盖见验证 JSON |
| `divider_v2.scs`、`limiter_chain.scs` | CML 主从锁存单元及电平恢复 | 环尺寸随分频档变化；参考电流 15 µA 为理想源，计入对应电源功耗 |
| `fll_controller.v` → `fll_mapped.json` → `fll_circuit.scs` | 自有 RTL，经 Yosys 443 个通用单元映射到 `digital_cells_v2.scs` 的实际 MOS 门、锁存器和触发器 | R3 补码 0 边界检查，并在范围错误时禁止交接；输入 24 MHz、6 位目标 K、14 位计数；输出 8 位粗调、6 位 DAC、门控、复位、交接和范围错误 |
| `tx_fll_counter` | 14 位异步进位计数器；输入时钟先经低电平透明锁存式门控，再进入计数链 | 计数关闭后控制器等待三个参考周期，给进位和总线稳定留时间；亚稳态统计验证尚未完成 |
| `tx_fll_snapshot` | 测量期间保持比较总线，关窗后打开 | 防止 GHz 计数进位持续激励控制器比较网络；不能省略冻结/等待步骤 |
| `tx_fll_dac` | 6 位 5 kΩ/10 kΩ R-2R，MOS 驱动，交接后关断 DAC 电源；驱动已有滤波器预充开关 | 电阻几何、失配、RC 角和关断漏电仍待工艺实现 |
| `retimer_scaled.scs` / `tx_retimer_scaled` | `data clk out vdd vss`；C²MOS 重定时和两级输出缓冲 | 噪声优选实例参数 `scale=4 oscale=4 sp=2.5u`；默认 `sp=1.06u` 仅保留旧候选对照。输入 VCO 时钟仍为理想全摆幅；未包含输出静音逻辑 |
| `reference_low_noise.scs` | 加大前两级参考缓冲，降低慢输入边沿导致的时间噪声 | 对输入负载和电源功耗有代价；当前改进噪声结果仅 TT |
| `lc_vco_filtered.scs`、`lc_core_filtered.scs` | VCO 偏置增加 200 kΩ/5 pF 滤波 | 保留原 VCO 作为比较；仅验证独立 VCO 周期噪声 |
| `lc_vco_filtered_slow.scs`、`lc_core_filtered_slow.scs` | 同结构，偏置滤波改为 1 MΩ/10 pF | 启动、实际加载和工艺 RC 面积尚未验证；不能直接作为顶层已采用方案 |

FLL 每次测量 256 个参考周期。R3 先测码 0；若其频率仍高于目标，再做 8 次粗调 SAR，然后做 6 次细调 SAR，最后等待 32 个参考周期。名义完整路径为 15 个窗口，直接使用码 0 时为 7 个窗口。范围错误时 `enable` 保持低；成功时表示频率捕获流程完成，**不是已经相位锁定**。本版不含后台失锁监测、自动重捕获或完整频点译码；这些仍需接入系统控制。

## 行为测试模型及历史探索

`fll_testplant.va` 只提供可控频率的 VCO 测试激励。`fll_window_meter.va` 是控制器长时间仿真使用的有限窗口计数宏模型；含它的结果不能称为全晶体管 FLL 仿真。

`receiver.scs`、`diff_receiver_v2.scs`、`johnson_direct_trial.scs`、`cmos_divider_v2.scs`、`cml_retimer_v2.scs` 与 R1 归档保留了不采用或仅部分通过的探索。其存在不表示被当前顶层使用。各次运行的 `inputs/` 才是对应结果的准确版本，不能拿当前源文件反推早期失败原因。

`cap_bank_biased.scs`、`lc_vco_off_biased.scs` 是未采用的关断底板弱偏置实验：每个底板经 1 MΩ 连到电阻中点。它减少了关断开关的近端噪声贡献，但引入偏置/电阻噪声并改变载波频率、摆幅，1 MHz 总相噪反而恶化；不得用它替代当前电容阵列。

## 生成与复现

`map_fll.py` 使用已有 `fll_mapped.json` 生成 MOS 电路，`verify_fll_logic.py` 在映射门图上检查 33 个频道的搜索路径。通用门综合输入为本目录 RTL；不使用任何未经授权的标准单元库。

运行只需交付的网表、TB、已有 PDK 与正常 Spectre 环境；不需要重跑 `research/` 中探索性生成脚本。那些脚本可能重建早期候选，不作为最终源代码生成入口。
