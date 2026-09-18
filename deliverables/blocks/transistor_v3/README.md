# 逻辑时序器件电路与电感初步模型

配套 [验证与复现说明](../../integration/transistor_v3/README.md)。本目录是 Spectre 器件网表，尚未建立 OA 原理图或版图。MOS 引用工程现有 PDK，未复制 PDK 模型。偏置和电流基准按 [DEC-0005](../../../reports/decisions/DEC-0005.md) 后置。

## 有源逻辑电路

| 文件 | 实现与接口 | 边界 |
|---|---|---|
| `cp_timing.scs` / `tx_cp_timing` | 24 级 MOS 延迟链、脉冲合成、低电平使能锁存及异步复位；`ref enable reset pulse vdd vss` | 延迟与脉宽由实际器件决定，没有 VA 定时器或理想延迟。R2 的使能锁存器在复位时清零，参考高电平期间释放复位不会重启残余脉冲。脉宽未校准，PVT 与电源敏感性必须计入环路。 |
| `pll_control.v` → `pll_config_mapped.json` → `pll_config.scs` | 241 个通用门映射为 MOS；同步配置请求、保持 6 位 K、译码到六档单热选择、非法码拒绝、切换时保持分频复位 | K=9…41 有效。选择位 0…5 对应 M=4/6/8/10/12/14。`apply` 经两级同步并检测上升沿；多位 K 必须从请求前保持稳定直到 `ready` 返回。不是任意异步多位总线的亚稳态签核。 |
| `pll_control.v` → `pll_supervisor_mapped.json` → `pll_supervisor.scs` | 205 个通用门映射为 MOS；捕获交接、连续有效资格判定、短异常过滤、重启请求、范围错误抑制 | 连续 32 个参考周期有效后 `qualified`；已取得资格后连续 4 个无效周期触发 8 周期 `restart`。这些是可调整工作参数，不是新增项目验收指标。 |
| `pll_control_frontend.scs` | 将配置、监督、既有 443 门 FLL 控制器、实际 14 位计数器/保持总线、DAC 和脉冲发生器相连 | 配置更换或重启会复位 FLL；DAC 的关断由捕获控制器控制。`phase_good`、`frequency_good` 是尚待真实检测电路提供的输入，不能把本模块资格输出当成已经验证的模拟锁相。 |
| `frequency_watchdog.v` → `frequency_watchdog.scs` | 264 个通用门映射为 MOS；每 256 个参考周期进行一次 32 周期测频，关门后等待 3 个参考周期再判断计数 | 输出域目标为 32×K，暂定接受 ±1 个计数；不是 ppm 精度要求。`active` 无效时清除结果，不能判断输入幅度或相位。 |
| `frequency_monitor.scs` | 将上述测频时序/比较器与实际计数器、保持总线连接 | 独立完整计数窗口及相邻谐波辨别的证据见验证目录；输入仍为 CMOS 时钟。 |
| `pll_control_monitored.scs` | 在控制前端中共享同一个计数器/保持总线，捕获完成后由测频监督接管；`frequency_good` 在该版本中为输出 | 需额外包含 `frequency_watchdog.scs`。接口位置与旧前端相同，但不得再外接驱动 `frequency_good`。相位/幅度检测仍未实现，完整捕获到监督的切换与重捕获仍待系统验证。 |

配置改变时先将 `ready` 拉低并复位分频，再更新 K；第八个等待周期才按合法性释放。工作频点切换意味着重新捕获，不承诺相位连续切换。

`phase_good` 的后续产生电路必须同时确认 RF 幅度有效。VCO 停振时采样差分误差也可能接近零，不能只用小相位误差判定锁定。这里定义接口要求，尚未实现该模拟检测电路。

依赖顺序：`transistor_v1/cells.scs`、`transistor_v2/digital_cells_v2.scs`，需要前端组合时另包含 `transistor_v2/fll_circuit.scs`，然后包含本目录对应子电路。标准单元的晶体管连接与尺寸继承已验证 v2 单元；未使用理想逻辑门替代。

## 电感及 VCO 模型

`inductor_pi.scs` 包括绕组串联 R/L、绕组间电容、两端氧化层电容，以及每端基底电阻和电容。`sub` 端接衬底地；当前两支路按独立电感建模，未包含互感和共用衬底耦合。

每支路暂取 L=2 nH、跨绕组 C=20 fF、每端 Cox=80 fF、Csub=50 fF、Rsub=300 Ω。在一端交流接地的实际 VCO 使用条件下，用完整输入阻抗 `Im(Z)/Re(Z)` 在 3.3 GHz 拟合 Q=3/5/8，对应绕组 Rs 约 11.859/6.822/3.955 Ω。必须使用完整网络计算 Q，不能再直接用 ωL/Rs 代表含衬底损耗后的 Q。

只有 Q≈5 具有 [文献参照](../../sources/transistor_v3_sources.md)；将其用于 3.3 GHz，以及具体寄生、电感值和两侧独立假设，均属初步研究选择。寄生乘 0.5/2 的敏感性实验保持 Rs 不变，因此 Q 也随之变化。模型含电阻热噪声，但没有完成趋肤效应、温度系数、几何、EM 或本 PDK 的标定。

`lc_core_rlc.scs`、`lc_vco_rlc.scs` 将该模型接入原实际 MOS 核心、MOS 电容阵列开关和 PDK 细调变容管；保留 1 MΩ/10 pF 偏置滤波。`series_r`、`cscale`、`core_w`、`ibias` 为诊断参数。核心加宽或电流增加试验不自动成为采用方案，结果见验证记录。真实偏置发生器、阵列/固定电容的工艺实现仍未完成。
