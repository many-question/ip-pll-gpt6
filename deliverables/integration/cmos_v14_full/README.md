# V14 完整晶体管 PLL 集成工作区

这是当前进行中的集成分支，尚未完成完整 PLL 验收。旧 V14、V13 与更早的混合模型结果保留原边界，不作为本分支整机结果。

## 目标与边界

先补齐真实偏置、可编程 CMOS 分频、物理振幅／相位检测，再让同一份 DUT 完成配置、FLL 捕获、主环交接与锁定监督，随后测量实际指标。所有内部功能应由 PDK MOS 与电阻、电容、电感实现。外部电源、24 MHz 参考、配置与复位允许理想激励；经用户认可，电感继续使用暂定 Q5 的 π 型 RLC。`lc_loop_observer.va` 只用于 TB 观测，不驱动或控制 DUT。

当前完整可编程候选为 `pll_complete_v14.scs`，含 **13,394 个项目层展开的 MOS、2 个 PDK 变容器件、41 个电阻、39 个电容、2 个电感和三个 0 V 电流探针**。结构审计没有发现 DUT 内部功能 VA 或理想电流源。外部功耗测量器 `supply_energy_observer.va` 仅作 0 V 串联电流测量并积分能量，不提供控制或替代内部功能。原 `pll_complete_k41_v14.scs` 和 `pll_complete_k41_sampled_v14.scs` 是固定 ÷4 的早期单通道诊断版本，分别保留证据。结构审计入口：

```powershell
python share/deliverables/integration/cmos_v14_full/audit_boundary.py pll_complete_v14
```

## 已发现的问题与当前证据

- 旧 180 µA 理想 IREF 将 VCO 镜像基准节点推到 TT 1.369 V、SS 1.482 V、FF 1.271 V，高于 1.2 V 电源。本分支用电阻馈电的 MOS 基准替换，不能照搬旧偏置下的结果。当前简单电阻基准并非带隙或稳定的 PVT 基准。
- VCO 基准／尾管宽度放大十倍、RREF=2.5 kΩ 后，基准电压约 SS 0.753 V、TT 0.726 V、FF 0.698 V。固定码 24、控制 0.2 V 的加载振荡器 TB 功耗约 SS 4.716 mW、TT 5.006 mW、FF 5.234 mW，尚未包含完整 FLL／监督逻辑，已经高于整机 4 mW 目标。这里不做功耗达标声明，也不启动独立功耗优化。
- 静态相位窗口／振幅检测 TB 在 TT27、SS60、FF0 通过六个输入场景。实际采样 TB 揭示：参考上升沿前的原始比较器输出可能错误保持高，不能直接拿来认定相位有效。当前控制在参考下降沿采入结果。8 个相位点的动态检查中，TT 有 7 个明确通过、1 个临界点不作结论；FF 8 个通过；SS 有 2 个失败、2 个临界点，不能宣称检测器全 PVT 已通过。
- 分级 CMOS 分频树已经实现六档：RF÷2 支路用独立模三计数器和五／七级寄存器环实现 ÷6、÷10、÷14；RF÷4 支路实现 ÷4、÷8、÷12。原并行静态环、C2MOS 环和统一高速寄存器环的负结果均保留。当前树在 TT 的六档独立 TB 以及六档＋重定时 TB 均通过；SS 的 ÷6、÷10、÷14 仍失败。这不是 33 点或实际 LC 全频验证。
- FLL、配置、监督、计数器和 DAC 均为物理 MOS 电路。当前 FLL 在启动时计固定 RF÷4，32 参考周期的 RF 计数量化步长为 3 MHz；锁定后切换为最终输出的频率监督。目标为 K×M×8，782 个通用逻辑单元映射为 MOS。33 点、码零边界及两种越界情形的门级验证通过，最大有效 RF 残差 3.325 MHz。这仍是数字逻辑证据，完整模拟捕获另行验证。
- 第一份完整单通道近锁定 TB（`fullwarm/full_warm_tt`）在 2.919 µs 给出 qualified；4 µs 结束时各状态正常。但末 1 µs 相位漂移 0.02748 rad/µs、相位峰峰值 0.02877 rad，未通过当前稳定性筛选；输出约 984.001155 MHz。该 TB 使用构造并记录的近锁定初始状态，不能当作冷启动证据。
- 上述同一单通道完整电路末 1 µs 的总供电功耗为 **5.105565 mW**，已高于 4 mW。测量来自仿真内部时间步上的供电能量积分；该窗口处于监督计数静默段，仍未证明长期锁定平均值。测量器独立 1.2 V／1 kΩ 验证得到 1.44 mW 和 100 ns 内 0.144 nJ。
- 可编程完整 DUT 的 `completecold01` 冷启动与 `completewarm01` 近锁定连续运行均已启动，只有完成并回收后才写入正式验收结果；不能把 live snapshot 当作通过。
- 更粗的 10 ps／reltol=1e-3 仿真产生了足以影响 FLL 交接的 VCO 频率偏差，保留为负面的数值精度证据，不用于锁定验收。

## 可复现输入与证据

运行器为 `run_spectre.py`，仿真前冻结所有实际依赖文件，验证服务器输入 SHA256，回收原始结果与最终状态。当前原始数据在项目根目录的 `research/runs/spectre_cmos_v14_full/`，服务器只作为计算环境。运行示例（使用新的 run-id，不能覆盖既有实验）：

```powershell
python share/deliverables/integration/cmos_v14_full/run_spectre.py --run-id newtrial --mode ax --threads 1 --preset-override all --cases detector_tt
python share/deliverables/integration/cmos_v14_full/analyze.py
```

`results/validation.json` 只读取已经回收并核验输入的完整运行；`research/v14_full_progress.jsonl` 是未完成仿真的进度，禁止当作验收证据。桥接器可能把成功日志中的 DC 收敛回退提示误分类为 `convergence failure`；分析同时检查实际 Spectre 完成状态和 ERROR 行。

当前噪声求解边界见 [完整周期分析](results/noise_period_boundary.md)：K41 正常监督模式的完整状态周期至少 32 µs，不能沿用 24 MHz 局部周期解作为整机噪声证据。暂未取得同一可编程完整 DUT 的冷启动通过、长期锁定平均功耗、10 kHz–fout/2 噪声积分、33 频点、全 PVT、负载范围、供电敏感性、重配置／失锁恢复和 Monte Carlo 结果。版图、面积、PEX、器件端电压可靠性均未签核。所有最终汇报继续覆盖 kickstart 中 REQ-01…REQ-12；杂散保留指标，但按用户要求暂缓优化与验收。

当前数字输出的占空比在 TT 约 41.6%–74.6%，不同分频路径不相同。按用户指示暂不专门优化占空比，但不能把“有正确频率和完整摆幅”写成已验证 50% 对称输出。

已完成结果、输入与原始文件 hash 分别见 `results/validation.json`、`results/raw_manifest.json`。原始数据留在当前项目 `research/runs/spectre_cmos_v14_full/`；所有试验使用唯一 run-id 和不可变输入快照。
