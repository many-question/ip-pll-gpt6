# 第68次噪声与抖动审阅

2026-10-05T16:12:34+08:00。RT4渐进精度在16µs容差切换处触发LTE恢复；已启动分阶段终态生成试验，原版PLL稳态基线继续。

pllprecisionramp01在16µs同时把reltol1e-5收紧为1e-6、vabstol100nV收紧为1nV；约16.0002µs报告一次SPECTRE-16780，定位到XP.XV.XBN.MP5:int_s，即负端电容阵列bit5的PMOS钳位器件内部源极。保护脚本确认任务归属后仅停止该进程。实际终止约16.0057µs，摘要1error/2warnings/97notices；SPECTRE-25来自保护性SIGINT，不是第二个独立电路故障。没有完整终态文件。

已回收26项输入、6331025字节原始波形和18311字节终止日志，远端与本地SHA256一致。独立解析对8003个2ns采样点的时间及7个节点逐点比较，差为0；原始失败结果保留。此前没有报告Newton恢复或跳断点，保存的qualified、acquired、phase_held及frequency_good保持高。数据是稀疏采样，只能说明未观察到重新捕获，不能证明连续锁定或边沿抖动。

故障与最后容差切换紧邻，支持优先检查动态切换及积分历史的影响，尚不能确认为器件缺陷或单一容差的原因。原版PLL固定细精度试验与本RT4动态精度试验的电路和初始化不同，不能用前者证明RT4已通过。

已启动pllprecisionstage01：复用此前同一RT4/newbank电路、初态、参考源和0–15µs精度序列，仅删除16µs切换并在15.9µs停止，以取得完整、无数值恢复的中间器件终态。25项物理依赖/初态输入与失败运行逐项哈希一致。末段为0.5ps/reltol1e-5/vabstol100nV/iabstol1pA；该结果仍只用于初始化。随后另起固定0.5ps/reltol1e-6/vabstol1nV/iabstol1pA密集验证，保持参考物理相位，重新检查初始化、状态及原稳态门限。未改变器件、扩大门限或从稀疏观测拼装不完整初态。

截至2026-10-05T16:10:35.207686+08:00，原版pllmainsettledoff01约1.994µs/2.2µs，无数值恢复、缓存状态保持；新RT4中间态试验已在服务器运行。main_settled_noise_pipeline仍拥有原版noise-on派发权，必须通过完成、初始化、日志、状态及完整末1µs稳态门限，禁止重复派发。

完整PLL的10kHz–fOUT/2、排除离散杂散的RMS<200fs仍未知。此前150ns全器件噪声开启试验通过方法检查，但请求1MHz被提高到5MHz，严格协议仍不通过；它不能代替稳态和全带抖动。功耗及后端优化后置，33频点、完整PVT/MC、杂散、供电爬升、负载及PEX缺口不变。原版V14与RT4候选、局部结果与全PLL验证分开。

[失败证据与哈希](results/full_pll_precision_ramp_failure.json)；[新阶段协议](results/full_pll_precision_stage_protocol.json)。

全部12项需求、14模块及六层状态见[完整汇报](../../../reports/2026-10-05T1612.yaml)。
