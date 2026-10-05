# 第70次噪声与抖动审阅

2026-10-05T20:34:15+08:00。RT4中间精度整环仿真正常完成，完整终态和公共前缀审计通过；已启动独立恒定细精度检查，全带抖动仍未知。

pllprecisionstage01已实际完成15.9µs，0errors/1warning/29notices，12232493个接受步，墙钟4h14m4s。唯一警告为AHDL环境变量提示；Newton恢复、跳断点、LTE放宽与最小步长警告均为0。条件为完整RT4/newbank晶体管PLL、TT27/1.2V/24MHz/K41/M4/10fF/Q5RLC/CF10，外部供电与参考理想。0–14µs逐步将maxstep由4ps降至0.5ps；15–15.9µs保持0.5ps/reltol1e-5/vabstol100nV/iabstol1pA，始终noise-off。

7951个2ns采样点、23条已保存信号与旧pllprecisionramp01的有效前缀逐点完全一致；第二套流式解析的时间及7个节点也与缓存完全一致、无重复记录。19个可比较电压初态差为0。qualified最低1.199996V、acquired最低1.188871V、phase_held最低1.199996V、frequency_good最低1.199982V；采样点中未见重捕获，不能由稀疏记录断言连续RF稳态。26项输入以及6289916字节原始波形、16106字节终止日志、280233字节完整终态均已本地回收并逐项核对远端SHA256。writefinal含7863项状态；源状态中reset/apply两项因各自理想0V直流源被合并到地，其余状态名全部保留，未从稀疏波形重建终态。

20:30:38启动pllrt4fineoff01，远端53e3ca81/PID450212、7线程。完整终态字节不变，参考下次上升沿平移为17.6666666666794ns，维持原参考物理相位。恒定0.5ps/reltol1e-6/vabstol1nV/iabstol1pA/traponly，stop2.2µs，1µs以后保存密集RF/输出。24个物理依赖文件与已审计中间态一致，全部26项远端输入与本地launch哈希一致。rt4_fine_noise_pipeline复用已有分析和派发逻辑，仅在实际完成、数值干净、初始化、逻辑保持与稳态门限全部通过后派发pllrt4fineon01；目前noise-on尚未派发。

原版V14仍与RT4分开：先前固定细精度quiet末1µs全部门限通过，输出984.000020347MHz、相位峰峰0.005202582rad、漂移−0.001909413rad/µs。原版pllmainsettledon01已在1µs实际开启器件噪声，本次核查至1.202003µs，尚未结束；当前日志无Newton恢复、跳断点或LTE放宽。流水线继续持有该任务，未重复派发，尚无可验收RMS。

原RT4动态容差切换在16.0002µs触发LTE恢复的失败证据仍保留。中间态完成只验证了有效前缀重放和终态获取，不能证明旧故障原因已完全定位，也不证明后续恒定细精度或RT4噪声通过。文本IC不恢复隐藏积分历史，后续必须重新检查初始化。两个配对任务均为1024边沿、约5.285–492MHz的高偏移诊断；全PLL10kHz–fOUT/2、排除离散杂散、RMS<200fs仍未知。步长、电流容差、噪声带宽、种子、记录长度与低偏移覆盖尚需验证。

核查实际2项长任务、14请求线程：原版匹配noise-on和RT4恒定细精度quiet。只替换了核实身份的本地保护进程，新增对RT4配对的监测，未停止任何Spectre仿真。保护器及两个流水线均在运行；旧quiet失败流水线保持needs_review。

[中间态审计](results/full_pll_precision_stage_validation.json)；[固定细精度配对协议](results/full_pll_rt4_fine_pair_protocol.json)。

原始输入输出保存在`research/runs/spectre_cmos_v14_full/pllprecisionstage01/full_pll_rt4_precision_stage_tt/`，哈希见审计；使用`analyze_rt4_precision_stage.py`复核，远端审计快照为`research/rt4_precision_stage_remote_audit.json`。

全部12项需求、14模块及六层状态见[完整汇报](../../../reports/2026-10-05T2034.yaml)。
