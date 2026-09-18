# 晶体管模块 v1

本目录包含项目自有 Spectre 网表，使用服务器配置的 TSMC180 BCD Gen2 `nch/pch` 核心模型，供电 1.2 V。没有创建 OA schematic/layout；当前设计权威输入是网表和运行快照。

| 文件/单元 | 当前用途 | 实现边界 |
|---|---|---|
| `cells.scs` / `tx_reference_buffer` | 四级参考缓冲 | PDK MOS，独立三角和混合系统验证 |
| `cells.scs` / `tx_output_buffer` | 10 fF 输出缓冲 | PDK MOS，984 MHz 三角验证 |
| `cells.scs` / `tx_sampler` | 两侧 40 fF 采样保持 | MOS 开关 + 理想 C；已测真实 CP 加载后的相位/电荷曲线 |
| `cells.scs` / `tx_loop_filter` | R/C 与预充开关 | MOS 开关 + 理想 R/C；默认 22.222 kΩ，S7 用参数 `rlf=100k`；preset DAC 仍由行为控制提供 |
| `cells.scs` / `tx_bias_mid` | 0.6 V 中点分压 | 2×100 kΩ +1 pF；不是完整偏置发生器 |
| `cells.scs` / `tx_retimer_c2mos` | 当前重定时候选 | 动态 C²MOS，三角序列检查和 6 µs 混合闭环通过 |
| `cells.scs` / `tx_output_retimer`、`pll_tspc_inv` | 历史比较候选 | 慢角失败保留，不是当前重定时实现 |
| `lc_vco_candidate.scs` | 合并的 LC/粗调/细调候选 | 真正 MOS 振荡核心与开关、PDK nmoscap；L/R/固定和阵列 C 假设、理想偏置参考 |
| `cp_experiment.scs` | 跨导级候选 | 差分对、镜像、门控均为 MOS；S7 固定码闭环通过；偏置参考仍理想，噪声与完整启动未验证 |
| `cml_prescaler_experiment.scs` | CML ÷2 前端 | AC 耦合、共模分压、MOS 锁存；理想偏置参考，尚无 CMOS 电平转换或完整可编程分频 |
| `cml_to_cmos_experiment.scs` | CMOS 转换探索版本 | TT/FF 可获得有效输出；SS 摆幅未通过，尚不能用于完整分频链 |
| `sampler_interface.va` | 混合层级适配 | 电压差读出、CP 脉冲定时、FLL 有效样本保存仍为 VA |
| `supply_meter.va` | TB 仪表 | 连续供电能量积分，不属于设计电路 |
| `loop_observer.va` | TB 仪表 | 同参考相位采样控制电压，区分收敛趋势与周期内纹波 |

LC 合并候选接口为 `vp vn ctrl b0…b7 vdd vss`，粗调位是 0/1.2 V 电平。它尚未替换原顶层的电压编码 `code`、理想 VCO 时钟接口；需要真实控制位与时钟整形后再集成。

LC 默认固定电容为 190 fF；实际加载试验使用额外参数 `fixed_c=150f` 重新分配端点，必须结合相应 TB 判断。LC 输出共模接近 1.2 V，采样器工作共模接近 0.6 V；`tb_vco_loaded_*` 显式加入 120 fF/侧交流耦合和 100 kΩ 偏置，不能直接把两组节点短接。

具体条件、负例和复现入口见 [晶体管与混合验证记录](../../integration/transistor_v1/README.md)。未验证版图、DRC/LVS/PEX、失配、器件完整噪声和供电上电过程，不将理想无源件面积当作版图结果。
