# 本轮依据与证据边界

2026-10-01。使用本项目第 8 份报告、已交付 VCO R2、MOS 分频与采样/CP/滤波电路，以及服务器实际安装的 Spectre 文档和运行结果。未进行新的文献检索，未改变 Q=5 暂定 RLC、抖动频带、功耗、面积或其他需求。

- [模型与环境核查](../integration/closure_v6/results/environment.json)：PDK 入口哈希与前轮一致；不复制 PDK 模型。
- Spectre `-h tran`、`-h pss`、`-h dc` 原文保存在项目 `research/spectre_help/`。依据其中 `writefinal`、`readic`、`skipdc` 的定义保存并复用完整电路状态。
- 实际数值选项从各日志的分析参数表读取。`errpreset` 标签不作为容差已生效的证据；分别记录 reltol、maxstep、method 和 steadyratio。
- 关断输入节点的电导敏感性为本项目 DC 实验观察；钳位改善这些节点偏置的结论不等价于解决完整闭环求解、噪声或所有内部高阻状态。
- 分频隔离测试使用前轮实际波形的理想回放源，消除了实际 VCO 源阻抗与反向耦合，不能当作真实闭环或 VCO 噪声结果。压力切换测试固定 3.936 GHz，部分分频档超出规划最高输入频率；规划频率验证独立留存。
- 所有实际 LC 环路使用原 Q=5 VCO R2。VA 观察器只计数和采样边沿，不生成 VCO 时钟或参与控制。
- 新增原版/钳位分频器的 sampled Pnoise/Jee 对照，沿用本项目已验证的 Spectre 上升沿语法和独立谱积分方法；无噪声理想 RF 输入下的器件附加噪声不能替代实际 VCO 回注或整机输出噪声。
- `itres` 与 `writepss` 的作用按已安装 PSS 帮助记录；后者会在射击法收敛后触发有限差分细化。`gear2only` 对照来自本轮失败 PSS 的最终诊断建议，仍需验证波形和数值精度。

原始输入、状态文件、PSF、日志及失败记录回收到项目 `research/runs/spectre_closure_v6/`。交付目录仅保留工程网表、可执行分析入口、摘要和哈希；服务器不是唯一状态源。
