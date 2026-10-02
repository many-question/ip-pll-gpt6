# V14 捕获修复验证

本轮按已确认顺序推进：先处理 FLL 交接与首次捕获，再处理 SS 分频和低端调谐覆盖，之后评估功耗及整机噪声。历史完整系统结果保留在 [首轮基线](BASELINE.md)，不作为修复版的新结果。

修复版 [pll_capture_v14.scs](../../blocks/cmos_v14_full/pll_capture_v14.scs) 已接入以下实际 MOS 控制电路：

- FLL 粗调仍计 32 个参考周期，粗调结束采用 floor+2 留出细调余量。细调改为 128 周期，对应 0.75 MHz RF 计数量化；记录实际测过的最小绝对计数误差及对应 DAC 码，误差相同取较低码，取消末步无条件加一码。
- 首次交接后连续 512 个参考周期仍未 qualified，则产生 8 周期重启脉冲。512 周期约为 21.33 µs，是当前设计参数，并非新增的用户验收指标。原 32 次连续有效采样建立 qualified、4 次连续失效重启的规则保留。

结构审计展开 **17,644 MOS、2 个 PDK 变容、41 R、39 C、2 L 和 3 个零伏电流探针**。相比旧版增加 4,250 MOS，尚未优化这部分面积和功耗。内部无功能 VA 或理想电流基准；电感仍为获准的暂定 Q5 π 型 RLC。见 [结构](results/boundary_pll_capture_v14.json) 和 [验证协议](results/capture_repair_protocol.json)。

## 已完成的验证

| 层次 | 条件 | 结果与边界 |
|---|---|---|
| 门级图与线性 VCO | 33 个 K、每个 8 个连续 RF 初相位；另有 24 个端点／越界例 | 264+24 例通过；有效 RF 残差 −1.100…+0.175 MHz。模型采用线性调谐，不证明真实 VCO 捕获。 |
| FLL 晶体管 TB | TT27、SS60、FF0；1.2 V、24 MHz、50 ps 理想参考边沿、20 fF 输出负载 | 三角均通过；每角完整核对 1,268 个参考边沿后的所有输出位。测频总线由理想刺激提供，尚未验证真实计数器、DAC 和 VCO 的联合交接。 |
| 监督晶体管 TB | 同上三个角；含初始超时、资格建立、短暂失效、失锁、故障与重新配置 | 三角均通过；每角核对 838 个参考边沿。期限同周期资格建立优先于超时，另有门图定向验证。 |

晶体管单位测试使用 maxstep=500 ps、reltol=1e−4、1 ns 输出采样；每个参考边沿后 10 ns 检查，高电平须 >1.0 V，低电平须 <0.2 V。FLL 因原单次时限而采用原生断点接续，电路、刺激和精度保持一致；检查包含断点之前和之后的完整轨迹。原始停止片段保留为停止记录，未当作电路失败或独立通过结果。

证据：[门图检查](results/capture_repair_logic.json)、[6 组 MOS 检查](results/capture_repair_units.json)、[单位 TB 与完整 DUT 一致性及原始数据 hash](results/capture_repair_consistency.json)。

## 完整 PLL 复位仿真

`repaircold01/repair_capture_tt` 已启动，尚无完成或锁定结论。该测试为 TT27、1.2 V、24 MHz、K41/M4、10 fF、Q5 RLC，计划运行 64 µs；maxstep=4 ps、reltol=1e−4。供电从开始即为 DC 1.2 V；实际执行复位和配置，仅用初始 10 µV 差分扰动启动确定性振荡。没有读取旧电路的原生状态，也没有构造近锁定初态。这不是供电爬升验收。

先判断真实 FLL 最终码、交接前 RF 余差、qualified 与外部相位／频率稳定性是否一致。首次交接预计约 53 µs；若首次捕获失败，64 µs 不足以覆盖 21.33 µs 超时，须以同一电路的原生状态继续观察。4 ps 功能筛选通过后再作严格数值复核和长时间保持检查。

```powershell
python share/deliverables/integration/cmos_v14_full/monitor_jobs.py repaircold01
# 等最终结果及 hash 回收完成后运行：
python share/deliverables/integration/cmos_v14_full/analyze_capture.py repaircold01 --case repair_capture_tt --fine-window 128
```

本版整机功耗、抖动与启动能量尚无有效最终结果。旧版 5.616 mW 和局部链 141.281 fs 保留原条件，不移植为修复版指标。用户确认的全部 PLL 功耗边界、10 kHz–输出频率一半的抖动频带、33 个频点及全部 REQ 均保持。

## SS 分频定位

独立诊断使用旧版相同分频树和重定时器，1.2 V、SS60、20 ps 理想 RF、10 fF。已回收的波形显示：

- ÷6（RF 3.888 GHz）：内部 ck 最大只有约 0.634 V，互补时钟 ckb 维持高电平。
- ÷10/÷14（RF 3.120/3.024 GHz）：复位期间循环寄存器状态正确，释放后状态丢失，最终全零。
- 两组仅改变时钟缓冲尺寸的对照均未恢复三个失败档位；恢复摆幅不足以证明时序问题已解决。
- 单相 CMOS 存储对照使 ÷14 的独立测试达到约 216 MHz，但 ÷10 输出约 156 MHz（目标 312 MHz），÷6 周期仍不正确。不能将该候选接入正式顶层或宣称 SS 已修复。
- 进一步反转采样相位、延长预充电区间的三个对照均未通过；保留为负结果。这也不能证明预充电是唯一根因。

![SS 时钟与状态波形](results/figures/ss_clock_diagnosis.png)

这些观察把下一步定位到预充电、采样窗口和数据传播时间，而不是继续无差别放大器件。独立候选未改动完整捕获修复版。所有已完成对照和失败记录见 [SS 诊断结果](results/ss_clock_repair.json)，原始输入和波形留在本项目 `research/runs/spectre_cmos_v14_full/`。
