# output_v9 来源与可用范围

访问与使用日期：2026-10-01。

1. 本项目 `transistor_v2/divider_v2.scs`、`cml_retimer_v2.scs`、`receiver.scs`、`limiter_chain.scs`，以及 `closure_v6/divider_bank_v6_clamp.scs`：复用项目自有 CML、MOS 接收与分频电路，派生出本轮原始差分接口和重定时试案。
2. 本项目 `interface_v5/tank_waveform_v5.va`：3.936 GHz、20 谐波的既有 VCO 电压形状。该源无噪声且无实际输出阻抗，不能代表 VCO 加载后的抖动/调谐/Q/功耗。
3. 指定服务器 PDK `c018bcd_gen2_v1d6.scs`；本轮再次核对顶层 SHA-256 为 `d44aa9da7ba670f0b4cfb0198b019dc73abf8bae21b15f45ce5a30c7cb5973ff`。TT、stat_noise、tt_bbmvar；不复制或发布 PDK。
4. 已安装 Spectre 21.1.0.509.isr12 帮助及 `accuracy_v7` 采样积分诊断：采用裸 `-preset_override`，逐例记录日志实际容差；输出周期 PSS 为 984 MHz，ratio1，显式积分 10 kHz–492 MHz，并对照 Jee。设备 STRUCT 的 total 是 PSD，顶层 out 是 ASD；逐器件求和与 out² 核验后才作贡献归因。
5. 本轮实际分频波形、有限 ±10 ps 数据移位和器件噪声计算：用于检验重定时时钟极性与数据稳定程度的假设。该假设和电路是本项目探索结果，不声称来自已发表的达标方案。回放先检验零移位与实体夹具的一致性，不合格试案不解释其敏感度。

电阻反馈降低的试案因 GHz 摆幅失败而停止，未由此推断低频噪声增益已经压低。没有增加外部文献 Q 或工艺电感模型证据；原 Q=5 暂定 RLC 及 Q=3 慢角失振风险保留。
