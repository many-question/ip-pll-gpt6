# 第72次审阅：仿真迁移至本地SSD

2026-10-05T21:51:16+08:00。已按用户要求把完整PLL仿真迁至服务器本地SSD；实际进程cwd、TMPDIR及项目写入文件均核验通过，仍为2项任务共14线程。

此前并非14个任务，而是2个Spectre任务各7请求线程。核查realpath、df和/proc发现，旧输入与输出在/home/jielu/TSMC180/MP/IP-PLL-GPT6下的NFS，进程cwd也是/home/jielu。用户明确要求不要在家目录仿真，已据此修改后续计算位置并记录DEC-0009；初始三份kickstart文档未改。

新计算根目录为/server_local_ssd/jielu/IP-PLL-GPT6，实际设备/dev/mapper/simulation_data-server_local_ssd、XFS。派发器统一使用SSD路径保存输入、raw、日志和终态，并设置run目录cwd及run/tmp的TMPDIR。首次实际进程核查发现Cadence启动脚本会切回家目录，因此又将cd放到环境加载之后；模拟该行为的独立测试通过，随后核验真实Spectre进程。资源统计、保护器、停止和回收工具已支持SSD与只读历史路径；home启动路径被派发保护拒绝。旧历史脚本若仍硬编码home，执行前必须迁移。

单次SSH及永久原子claim继续保留。断线/超时不重放、同目录并发及完成后重放拒绝已有测试；新增csh切回home后再切SSD的测试，返回码0/73/73、计数器只写1次，cwd和TMPDIR正确，旧home派发拒绝。真实进程230088和228865的cwd分别为SSD下70a37f74和2d203756，TMPDIR为各自tmp子目录；全部项目写入文件描述符均指向SSD。Cadence许可/IPC锁文件仍按工具机制使用/var/tmp或/tmp，PDK与工具安装位置只读引用；这些不是项目仿真输出或家目录运行。两项各26个输入的远端/本地哈希匹配；相对迁移前，仅TB中的run及存储路径改变，物理依赖与完整初态逐字一致。

已核对身份并停止旧NFS任务pllmainsettledon02/pllrt4fineoff02，以及发现cwd回退后的第一轮SSD启动；本地流水线先停止，随后仅对对应仿真SIGINT，确认清空后再派发。四段已保存末时间分别166ns、132ns、44ns、36ns，均尚未开启噪声；没有Newton恢复、跳断点或LTE放宽。全部输入、部分raw及终止日志已回收并核对传输前后哈希。受控终止不等同于电路失败，也不提供完整稳态或抖动结果；未使用部分波形重建终态。

当前原版pllmainsettledonssd02复用已通过的完整quiet基线，noise配置仍在1µs后开启；RT4的pllrt4fineoffssd02先验证恒定细精度quiet，全部门限通过后由新流水线派发pllrt4fineonssd02。两条流水线与保护器均存活；服务器只见上述两项任务，无home下活动仿真，合计14请求线程。电路、0.5ps/reltol1e-6/vabstol1nV/iabstol1pA、2.2µs记录、初态及验收门限均不变。

14功能模块仍为晶体管/无源；原版V14与RT4/newbank候选分开，Q5 RLC电感近似保持。原版quiet稳态通过和RT4中间终态审计等已完成证据不受此次迁移影响。当前配对只用于约5.285–492MHz高偏移诊断；全PLL10kHz–fOUT/2、排除离散杂散、RMS<200fs仍未知。33点、完整PVT、低偏移、数值及统计收敛等缺口保持；功耗优化与后端继续后置，所有指标不变。

[实际进程与文件审计](results/ssd_storage_validation.json)；[csh目录切换测试](results/ssd_csh_launch_validation.json)；[用户决定](../../../reports/decisions/DEC-0009.md)。

运行输入和部分结果保存在research/runs/spectre_cmos_v14_full；回收与审计脚本为research/recover_ssd_migration72.py、recover_ssd_cwd_retry72.py和audit_ssd_launch72.py，哈希见证据。一次性派发脚本不得重复执行。

全部12项需求、14模块和六层状态见[完整汇报](../../../reports/2026-10-05T2151.yaml)。
