# 第71次噪声与抖动审阅

2026-10-05T21:32:16+08:00。发现并修复SSH重试导致的重复Spectre写入；受损结果已回收隔离，两项原条件验证已在新目录重新启动，全PLL抖动仍未知。

21:17核查发现原版pllmainsettledon01和RT4的pllrt4fineoff01各出现两个Spectre进程，共4项、28请求线程。同一运行的旧、新进程实际打开相同raw文件设备号及inode；本地同一runner日志各记录两次相同长命令，两个新进程约在服务器21:15:32启动。文件头被重写，旧进程继续在原偏移写入；因此两项在途结果均无效，不能分析为DUT故障或噪声指标。核对UID、工程路径、命令行及进程身份后，已停止对应两个本地runner、两条流水线和保护器，再对四个明确所属且无效的Spectre进程发SIGINT，随后实际工程进程数为0。

安装的桥接工具使用持久SSH shell；协议/连接异常后的重试会重新执行完整命令，没有确认前一远端进程已结束。普通subprocess路径也包含重试，因此仅关闭持久shell不足。重复提交与这条自动重试机制一致；最初导致两条连接同时异常的网络/会话原因未记录，不能进一步断言。修复仅在本项目：命令单次SSH执行，失败或超时不自动重放；Spectre目录使用原子mkdir永久launch claim，已有claim即拒绝执行且不覆盖日志。采用新的本地run ID和远端目录，不移除旧claim、不修改全局桥接安装。

两项全部26项输入均与服务器及本地launch哈希一致。受损raw分别1328687200和249782字节，终止日志14136和14701字节；原始输出和归档已回收到research/runs，传输前后远端哈希稳定且逐项匹配本地。result.json明确ok=false、integrity_valid=false、noise_measured=false、终态不可复用；混合日志的SIGINT终止摘要不作为单进程数值结论。原版已完成的pllmainsettledoff01及RT4已完成的pllprecisionstage01不受影响。

断线与超时故障注入均证明底层调用仅1次，未知Spectre启动格式拒绝派发；服务器无仿真的计数器实验中，两个并发重放返回0/73，完成后第三次重放返回73，计数器只写一次。新实际仿真的claim均已存在且无重复写入进程，全部远端输入哈希匹配。除run路径映射外，TB逐字相同，所有物理依赖、初态与门限均未变。

原版复用已经通过的无噪声基线，流水线重新检查完成、数值干净、状态、初态和稳态五项门限后，启动pllmainsettledon02；RT4启动pllrt4fineoff02，只有无噪声门限全部通过才派发pllrt4fineon02。当前真实服务器为2项任务、14请求线程：原版远端0a0a399d/PID145568，RT4远端092b5553/PID144705；新保护器和两条流水线均存活。此次启动不代表已完成，也不代表噪声已经开启：原版noise-on配置仍按1µs延迟开启。

原版V14与RT4/newbank保持独立，全部14功能模块仍为MOS/无源，使用获准Q5 RLC电感模型；电路没有改变。原版固定0.5ps quiet末1µs稳态通过，RT4中间15.9µs终态审计通过等既有证据保留；RT4恒定细精度仍待结果。当前配对仍仅计划1024边沿、约5.285–492MHz高偏移诊断，不能代替10kHz–fOUT/2、排除离散杂散、RMS<200fs的验收。完整PLL最终RMS未知；步长、容差、带宽、种子、记录长度、低偏移及PVT覆盖仍欠缺。功耗优化与后端继续后置，目标不变。

[事故与修复证据](results/duplicate_writer_repair_validation.json)；[防重放测试](results/single_launch_transport_validation.json)；[单次派发实现](single_launch_transport.py)。

本地复核入口：research/recover_duplicate_runs71.py、verify_single_launch71.py、audit_guarded_relaunch71.py。回收和派发脚本是一次性入口，不应重复运行；监控沿用现有保护器与流水线。

全部12项需求、14模块及六层状态见[完整汇报](../../../reports/2026-10-05T2132.yaml)。
