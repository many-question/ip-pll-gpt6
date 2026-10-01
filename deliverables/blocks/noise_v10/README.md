# noise_v10 单模块改版

这些网表是针对已确认噪声源的独立研究候选，未冻结。基线为 `output_v9` 的实体六档分频器、scale2 主从 CML 重定时及四级 AC 恢复加末级输出。每个试案只替换下表中的一个模块，结果与条件见 [验证说明](../../integration/noise_v10/README.md)。

| 文件 | 唯一物理改动 | 关注的代价 |
|---|---|---|
| `divider_v10_last2.scs` | 仅 /4 末级从锁存器 `XS2_1` 的 scale 从 1 增为 2 | 上一级驱动负载和功耗增加；其余分频档没有优化 |
| `cml_v10_master2.scs` | 仅主锁存器 scale 从 2 增为 4 | 分频输出和 RF 时钟负载增加 |
| `cml_v10_slave2.scs` | 仅从锁存器 scale 从 2 增为 4 | 主锁存器和 RF 时钟负载增加 |
| `cml_v10_bias1p.scs` | 现有镜管栅节点 `nb` 新增 1 pF 去耦 | 电容面积、启动和实际工艺模型；没有实现新的基准发生器 |
| `cml_v10_outfirst2.scs` | 仅输出恢复链第一级 CMOS 反相器 W 增大两倍 | 从锁存器负载增加；其余级尺寸、R/C 不变 |
| `cml_v10_out2stage.scs` | 四级 AC 恢复改为两级 AC 恢复，末级驱动保持原尺寸 | 输出摆幅/边沿和总增益；只在 984 MHz/TT 做本轮筛选 |
| `divider_v10_divlasthalf.scs` | 仅 /4 末级从锁存器 scale 改为 0.5 | 功能失败：约 656 MHz，未进行噪声仿真 |
| `divider_v10_divtg4.scs` | 仅 /4 的差分输出选择传输门 W 增大四倍 | 功能失败：约 656 MHz，未进行噪声仿真 |

锁存器的 scale 同时缩放全部 MOS 宽度和 R 负载，L 不变；scale 翻倍时 R 减半、镜像设计电流翻倍，实际电流和功耗由仿真测量。输出首级改版只改变该反相器 MOS 宽度。

晶体管使用项目指定 TSMC180 BCD Gen2 模型；R/C 为集中元件。共用单元仍从 `transistor_v1/v2` 等既有目录引用，由运行器连同各次 TB 冻结至输入快照并核对哈希。未复制或发布 PDK。噪声关闭只作用于噪声源，电路功能、偏置和加载均保留。

结果入口：

- [逐模块开关与方差闭合](../../integration/noise_v10/results/gating_validation.json)
- [单模块改动的噪声与功耗](../../integration/noise_v10/results/optimization_validation.json)
- [全部候选和精度资格](../../integration/noise_v10/results/summary.json)

仅开启一个模块所得的输出附加抖动是该模块贡献，不能代表整链或完整 PLL 的抖动。该输出夹具仍用理想无噪声 RF 电压形状源，真实 LC 加载、时序抑制、全频/PVT、面积及完整 PLL 功耗均须后续验证。
