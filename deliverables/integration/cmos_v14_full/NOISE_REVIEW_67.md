# 第67次噪声与抖动审阅

2026-10-05T15:17:38+08:00。完整原版PLL已跑通150ns原生器件噪声开启试验；全带抖动仍待稳态配对及数值、统计覆盖。

pllnoiseactivation01实际运行至200ns，50ns开启全器件噪声；Spectre终止摘要0errors/1warning/16notices，1094660个接受步，墙钟3h15m28s。TT27/1.2V/24MHz/K41/M4/10fF/Q5RLC/CF10、原版输出链，0.5ps/reltol1e-6/vabstol1nV/iabstol1pA/traponly、seed11、noisefmax160GHz；外部参考与供电理想。没有功能VA或控制钳位，Newton恢复/跳断点/LTE放宽/最小步长警告均为0。

19个可比较电压初态差为0；噪声段qualified最低1.197489V、acquired最低1.190656V、phase_held最低1.189798V，frequency_good/amp_good/enable均保持高；restart最大绝对值3.077mV、range_error最大绝对值2.882mV。本段没有重新捕获，记录147个输出上升沿；不将其周期范围当成随机抖动。

请求noisefmin1MHz被Spectre按1/stop提高到5MHz，原协议未改，严格协议pass仍为false。实际带宽已解释且其他检查通过，因此单独的activation_method_passed=true。150ns噪声记录、仍在调整的模拟工作点，以及尚未覆盖完整慢监督周期，均限制此结果；既不证明稳态噪声，也不提供10kHz低偏移覆盖。

原客户端3600s等待超时结果逐字节保留，completed_result.json另记实际完成。762894697字节原始波形、终止日志、终态和26项输入已回收并校验哈希；第二套流式解析对965026个时间点及7个节点逐点比较，最大差为0。已修复分析器NumPy布尔值无法写JSON的问题，重跑通过；监控器也修复了回收途中把旧超时manifest误标为collected的问题，两项状态回归通过，并仅重启本地保护脚本。原始仿真、失败记录和门限均保留。

pllmainsettledoff01与pllprecisionramp01仍在运行，最新缓存进度约1.086µs/2.2µs及14.928µs/20µs，状态保持且无数值恢复。main_settled_noise_pipeline继续拥有后续noise-on派发权，须等待完整quiet门限通过；旧pllmainstricton01不会派发。

完整PLL的10kHz–fOUT/2、排除离散杂散的RMS<200fs仍未知。原版与RT4候选、局部结果与完整PLL验收分别记录。功耗和后端优化后置；33频点、完整PVT/MC、杂散、供电爬升、负载及PEX缺口不变。

[噪声开启验证](results/full_pll_noise_activation_probe_validation.json)；[原始回收与解析审计](results/full_pll_noise_activation_recovery_audit.json)。

全部12项需求、14模块及六层状态见[完整汇报](../../../reports/2026-10-05T1517.yaml)。
