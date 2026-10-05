# 第66次噪声与抖动审阅

2026-10-05T14:14:36+08:00。原版严格无噪声基线完成但末窗漂移略超门限；已量化衰减并启动同精度、相位连续的延长稳定验证。

原版完整晶体管PLL的0.5ps无噪声基线pllmainstrictoff01已完成2.2µs，Spectre终止摘要0errors；Newton恢复、跳断点、LTE放宽和最小步长警告均为0。19个可比较电压初态差为0，测量窗qualified、acquired及其他状态保持。原始波形2461065286字节已回收并与服务器SHA256一致；日志、输入、终态和缓存也有哈希。

末1µs实测输出983.999370MHz、RF相位峰峰0.014317rad、漂移−0.012804rad/µs。漂移超过原门限|drift|<0.01rad/µs，其余稳态门限通过；原配对流水线正确停在needs_review，pllmainstricton01从未派发。没有把短窗或平均频率正常当成完整稳态通过。

同一条已完成轨迹分窗：1.0–1.5µs漂移−0.024445rad/µs，1.5–2.0µs为−0.010676rad/µs，1.7–2.2µs为−0.004585rad/µs；慢滤波节点斜率也逐步减小。证据支持继续衰减的稳定过程，尚不证明更长窗口或全带噪声已收敛。

已启动pllmainsettledoff01：从这条0.5ps轨迹自身2.2µs终态继续，同样0.5ps/reltol1e−6/vabstol1nV/iabstol1pA，再运行2.2µs；终态文件逐字节复制。参考下一上升沿延迟调整到9.3333333333351ns以保持原物理相位，电路与监督门限不变。新匹配noise-on仅在新quiet的完成、日志、初始化、状态和完整末1µs稳态全部通过后派发；现有流水线负责，避免重复。

两条quiet均是暖启动工作点验证，不是独立冷启动或随机噪声结果。RT4渐进精度与200ns噪声开启试验继续运行，仍无完成判定。全PLL的10kHz–fOUT/2、不含离散杂散的RMS<200fs仍未知；功耗和后端优化后置，全部指标不变。

[稳态分窗数据](results/full_pll_main_strict_settling_diagnosis.json)；[原始回收审计](results/full_pll_main_strict_recovery_audit.json)；[新实验协议](results/full_pll_main_settled_pair_protocol.json)。

全部12项需求、14模块及六层状态见[完整汇报](../../../reports/2026-10-05T1414.yaml)。
