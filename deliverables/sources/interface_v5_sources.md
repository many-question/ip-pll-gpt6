# 本轮依据与证据边界

2026-09-30：沿用项目已确认的需求、`DEC-0001` 功耗/面积口径、`DEC-0004` 抖动频带和 `DEC-0005` 暂定电感 RLC 约定；未引入新的电感 Q 或改变要求。

本轮直接依据为项目先前交付的 VCO R2、实际 MOS 分频/采样/CP/时序网表、本地已有 Python 环路模型，以及本项目服务器实际运行的 Spectre 日志、PSF 和输入哈希。未进行新的文献检索，未引用其他项目参数。

- 环境和模型哈希：[environment.json](../integration/interface_v5/results/environment.json)。与前轮的受限 PDK 模型入口 SHA-256 一致；模型本体未进入交付目录。
- 电感来源和假设继续见 [vco_v4_sources.md](vco_v4_sources.md) 与 [transistor_v3_sources.md](transistor_v3_sources.md)。本轮没有工艺电感、EM、互感或温度数据。
- 1 MΩ 采样偏置电阻降低噪声的初始想法是待验证假设；本轮器件噪声已否定其整体收益，失败及反例均保留。
- 真实 LC 闭环仅使用 VA 边沿观察器；鉴相器测试中的理想 RF 波形回放另行标注，不与真实 LC 结果混用。
- 噪声沿用自主 PSS 最低基频为分频输出、VCO 第 4 谐波、差分 PM 噪声除以载波功率的 SSB 定义；每个结果检查各源 PSD 之和。固定跟踪加载噪声不是周期采样 PLL 输出抖动。
- Spectre X 瞬态显式设置 `-preset_override=maxstep`；用于噪声/增益对照时还请求覆盖 reltol、method、errpreset。以日志中的实际值为准：[求解设置审计](../integration/interface_v5/results/solver_settings.json) 显示四组闭环瞬态实际 reltol=1e-3，驱动 PSS 实际 reltol=1e-5，但 errpreset 标签仍为 moderate。不能只凭网表或命令宣称所有保守设置生效。APS 与 X 的命令、最终错误数及求解失败均保留，数值发散不等于电路失振。
- 状态恢复依据服务器已安装 Spectre 的 `-h pss` / `-h tran`，文本保存在项目 `research/spectre_help/`。PSS `recover` 从保存状态续算，`writefinal` 保存最终瞬态状态；恢复后的周期解仍单独检查。首次 PSS 的提前中断与后续评估修正见 [恢复来源记录](../integration/interface_v5/results/pss_recovery_provenance.json)，未改写原始日志。

原始证据位于本项目 `research/runs/spectre_interface_v5/`。输入快照、远端与本地输入 hash、完整日志和原始 PSF 均在本地保存；服务器不是唯一状态源。最初两组作业因复制 runner 的输出目录常量留在 v4 目录，完成后原样迁移至 v5，迁移记录保存在各 run 根目录，未重写原始结果或输入内容。
