# CMOS 输出链与 CML 诊断单元

研究候选，详见 [集成与验证说明](../../integration/jitter_v11/README.md)。全部 MOS 使用既有 `cells.scs`/`retimer_scaled.scs` 的 PDK nch/pch，没有附带 PDK 模型。

| 文件 | 接口和用途 | 状态 |
|---|---|---|
| cmos_buffer_v11.scs | inp/out/vdd/vss；两级 CMOS，参数 s 同比缩放宽度 | s2/s4 在 TT 理想 10 ps 输入下完成噪声加密 |
| cmos_tspc_buffered_v11.scs | clk/q1/out/vdd/vss；3.936 GHz→1.968 GHz→984 MHz | 当前可继续的 ÷4 原型；无编程/复位/保持器 |
| cmos_cells_v11.scs | TG 主从锁存器和 ÷4 | s1/s2 未通过最高频率功能，保留负结果 |
| cmos_tspc_div_v11.scs | 无级间隔离的直接 TSPC ÷4 | 首级摆幅不足、失败 |
| cmos_c2mos_div_v11.scs | 动态时钟反相器构成 ÷4 | 最高频率失败 |
| restorer_v11.scs | 复用 noise_v10 的首级增大恢复器 | 仅用于独立输入摆幅/边沿诊断 |
| qp_replay_v11.va | 理想源回放先前物理 qp 电压 | 不保留源阻抗，未通过噪声等效资格 |

最终连接在集成目录的 `cmos_chain_direct.scs`/`cmos_chain_inv.scs` 及 `noise_cmos_chain_*` TB：真实 TSPC 分频、真实 C²MOS 重定时（scale=4、oscale=4、sp=2.5u）和真实输出缓冲。反相版本额外有 Wn=12 µm/Wp=30 µm 的 RF 时钟反相器。所有运行快照回收在本项目研究目录；这些电路未替换已交付的系统顶层，旧 CML 作为接口基线保留。
