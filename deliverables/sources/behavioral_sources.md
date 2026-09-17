# 行为建模来源与自有推导

访问日期：2026-09-17 至 2026-09-18。

- [Gao 等，JSSC 2009 原文](https://ris.utwente.nl/ws/portalfiles/portal/6542938/A_Low_Noise_Sub-Sampling_PLL_in_Which_Divider_Noise_Is_Eliminated_and_PD-CP_Noise_Is_not_multiplied_by_N_2.pdf)，DOI 10.1109/JSSC.2009.2032723：用于确认 SSPLL 相位域中参考虚拟倍频、主反馈无 N 分频、采样带宽影响及脉冲增益控制。详细实验条件已记录在 `initial_sources.md`。本轮模型参数不是从该论文移植为本项目器件值。
- [SciPy 1.17.0：矩阵指数](https://docs.scipy.org/doc/scipy-1.17.0/reference/generated/scipy.linalg.expm.html)：用于精确传播线性 RC/VCO 状态及矩形脉冲，避免欧拉步长改变稳定性结论。
- [SciPy 1.17.0：离散 Lyapunov 方程](https://docs.scipy.org/doc/scipy-1.17.0/reference/generated/scipy.linalg.solve_discrete_lyapunov.html)：用于独立计算稳定采样系统的噪声协方差，并与谱积分、随机时域结果对照。

周期内脉冲重建、模拟噪声的反馈混叠表达式、等电容粗调分辨率和本轮数值预算均为项目自有推导，并通过保存的交叉检查验证；不声称这些推导原文出自上述论文。未下载或重新发布论文全文。
