# 逻辑时序与电感初步模型来源

核对日期：2026-09-18。

1. [Gao 等，JSSC 2009 原文](https://ris.utwente.nl/ws/portalfiles/portal/6542938/A_Low_Noise_Sub-Sampling_PLL_in_Which_Divider_Noise_Is_Eliminated_and_PD-CP_Noise_Is_not_multiplied_by_N_2.pdf)，DOI 10.1109/JSSC.2009.2032723，p.3260（PDF 第 8 页），电路实现部分报告电感 Q 约 5。该器件用于 2.21 GHz、0.18 µm、1.8 V PLL；不能认定为本项目 BCD 工艺的 Q，更不能据此给出寄生或版图尺寸。本项目将 Q=5 转为 3.3 GHz 的初步研究锚点，并取 Q=3、8 作敏感性扫描，后两者不是该文报告的数值。
2. 当前项目配置的 TSMC180BCD 器件/模型库，读取接口与文件清单，未发现电感模型。人类确认其确实暂缺，见 DEC-0005。模型正文未复制或发布。MOS 和细调 nmoscap 继续采用已有 PDK。
3. 已安装 Yosys 0.69 的本地帮助和项目 v2 流程，用于 `proc / techmap / dffunmap`，将自有控制 RTL 映射成自有 CMOS 门网表。统计与综合日志留存在本项目；逻辑功能正确性不以综合成功代替。

电感的 pi 拓扑、工作频点 Q 拟合、AC 阻抗交叉检查以及具体 RC 参数均为项目自有初步模型。没有借用第三方受限模型，也没有宣称完成 EM、几何缩放、趋肤效应拟合或衬底互耦提取。
