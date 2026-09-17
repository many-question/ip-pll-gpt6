# 启动研究实际使用的公开来源

访问日期：2026-09-17。以下均为作者所在大学托管的论文原文。仅保存链接与必要摘要，不将论文全文重新发布。表内是文献实测，不能填作本项目实测。

| 来源 | 核实条件与结果 | 对本项目的作用和限制 |
|---|---|---|
| Gao 等，JSSC 2009，44(12), 3253–3263，DOI 10.1109/JSSC.2009.2032723，[原文](https://ris.utwente.nl/ws/portalfiles/portal/6542938/A_Low_Noise_Sub-Sampling_PLL_in_Which_Divider_Noise_Is_Eliminated_and_PD-CP_Noise_Is_not_multiplied_by_N_2.pdf) | 0.18 µm；1.8 V；2.21 GHz；55.25 MHz 参考；150 fs（10 kHz–40 MHz）；约 7.6 mW；有源面积 0.18 mm²；参考杂散 −46 dBc。核心功耗不含 50 Ω 测量缓冲，FLL 锁定后关闭。见 pp.3260–3262。 | 支持 SSPLL 主环、辅助捕获环及噪声建模路线；参考相位噪声仍随倍频转换。电压、参考条件和功耗不匹配本项目。 |
| Gao 等，VLSI Circuits 2010，*A 2.2GHz Sub-Sampling PLL with 0.16psrms Jitter and −125dBc/Hz In-band Phase Noise at 700µW Loop-Components Power*，[原文](https://ris.utwente.nl/ws/portalfiles/portal/5503287/Gao_VLSI_2010.pdf) | 0.18 µm；1.8 V；2.21 GHz；55.25 MHz 参考；160 fs（10 kHz–100 MHz）；总 PLL 2.5 mW，其中环路 0.7 mW、VCO 1.8 mW；有源面积 0.20 mm²；20 颗芯片、改变参考占空比时最差参考杂散 −56 dBc。见 p.2 实验及 Fig.5。 | 支持低功耗直接采样/参考缓冲研究。700 µW 不是总 PLL 功耗；也没有验证本项目的输出链、调谐范围、1.2 V 或隔离面积口径。 |
| Gao 等，JSSC 2010，45(9), 1809–1821，DOI 10.1109/JSSC.2010.2053094，[原文](https://ris.utwente.nl/ws/files/6782511/Gao_IEEE_JSSC_sept_2010.pdf) | 0.18 µm；1.8 V；2.21 GHz；55.25 MHz 参考；300 fs（10 kHz–100 MHz）；3.8 mW 核心、不含 50 Ω 缓冲；有源面积 0.20 mm²。论文报告参考杂散约 −80 dBc，2 倍参考偏移的最差杂散约 −76 dBc。见 pp.1817–1819。 | 采样负载扰动、开关注入/电荷分享和隔离是必须检验的杂散来源；不能只查参考基频偏移。这一低杂散实现不满足本项目 200 fs 目标，不能混用上一行抖动数据。 |

## 我们的推断

这些实测分别支持低抖动/低功耗和低杂散的工程可能性，没有给出本项目全部条件同时达成的证据。优先在本项目条件下验证 VCO 与采样接口，再比较直接采样、dummy 补偿及有限隔离缓冲的代价。是否增加 DLL 等辅助模块待实验后讨论，当前不改变架构基线。
