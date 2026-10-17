# 第124次：callback低RF端完整捕获通过，检查最大分频模式

K28/M4（输出672MHz、RF2688MHz）首次完整捕获123已自然完成，独立核验通过。这是callback110参数与recenter109完整硬件自身从原复位启动的证据；与已通过的K41/M4单点分别保留，不拼接为全频验收。

## 123完成证据

rt4cblowcap123ssd01 / rt4_callback_lowcapture123_tt：120µs、60001个有限物理点，退出0、零错误、PSF END，input/raw/log/final.ic哈希全部一致。两份完整独立审计相隔85.212435秒，Spectre实际耗时11小时3分13秒。原local runner消失原因未确认；按唯一pipeline旁OS锁接续原SSD目录回收，未重启仿真，也未使用final.ic续跑。units元数据NaN单独排除。

端点/粗SAR目标896，细SAR/新复测目标3584。全部18个EVAL的当前码和实际下一码符合冻结RTL，无解码警告。自主粗245，细SAR后按原规则丢弃旧最小值并回到DAC32新复测。

| 阶段 | 粗码 | DAC | 新计数 | 相对目标误差 | 下一粗码/DAC |
|---|---:|---:|---:|---:|---|
| endpoint | 0 | 11 | 1326 | +430 | 128/11 |
| coarse | 128 | 11 | 1046 | +150 | 192/11 |
| coarse | 192 | 11 | 955 | +59 | 224/11 |
| coarse | 224 | 11 | 917 | +21 | 240/11 |
| coarse | 240 | 11 | 899 | +3 | 248/11 |
| coarse | 248 | 11 | 890 | -6 | 244/11 |
| coarse | 244 | 11 | 895 | -1 | 242/11 |
| coarse | 242 | 11 | 898 | +2 | 243/11 |
| coarse | 243 | 11 | 897 | +1 | 245/32 |
| fine_sar | 245 | 32 | 3582 | -2 | 245/48 |
| fine_sar | 245 | 48 | 3589 | +5 | 245/40 |
| fine_sar | 245 | 40 | 3584 | +0 | 245/36 |
| fine_sar | 245 | 36 | 3583 | -1 | 245/38 |
| fine_sar | 245 | 38 | 3583 | -1 | 245/39 |
| fine_sar | 245 | 39 | 3584 | +0 | 245/32 |
| fresh | 245 | 32 | 3581 | -3 | 245/43 |
| fresh | 245 | 43 | 3585 | +1 | 245/43 |
| fresh | 245 | 43 | 3585 | +1 | 245/43 |

新复测仅3次，误差−3/+1/+1；粗245/DAC43连续两次合格后进入HANDOFF。72.752–74.086µs的交接长度1.334µs与32ref一致（2ns采样误差内）；acquired在74.086µs、enable在74.088µs拉高。frequency_good从75.670µs持续到120µs，qualified从84.170µs持续到120µs；range_error/restart从未拉高。使能45.912µs、持续qualified35.830µs均超过512ref/21.333µs监督时长。相邻粗码修正分支未触发，不能将成功归功于该分支或声称其已被物理验证。

qualified区间内部参考间隔周期观察器最差频偏9.804929ppm。末1µs平均672.000150332MHz，平均偏差+.223708ppm、最差5.175115ppm、跨度10.252474ppm；qualified/frequency_good占比均100%，末1µsrange_error峰值1.178mV，满足原功能快筛门限。使能区间包含交接瞬态，最差633.411ppm应与qualified区间分开。2ns保存不能直接计RF沿；观察器值不能替代FLL测频窗，频偏不是抖动。

末5µs ctrl时间均值.721136250V、拟合斜率−.005582858mV/µs；nfilt均值.734570565V、斜率−.001310360mV/µs。末1µs对应均值.721235856/.734569359V、斜率+.012497743/−.014409845mV/µs，存在周期纹波及窗口相关性。有限窗口斜率较小不能证明渐近稳态或噪声合格。相位观察器末5µs均值.830757577rad、斜率−.000436173rad/µs，同样仅是此窗口的统计量。

## 唯一后续：K9/M14自主启动前段

callback已有K41/M4与K28/M4两个独立捕获点，最低输出216MHz和最大分频÷14尚无本版本完整硬件证据。选择一个K9/M14、RF3024MHz的20µs自主前段，观察实际配置、最大分频路径和粗SAR选码；此时不追加固定粗/细码点或直接复制120µs记录。

rt4cbdiv14124ssd01 / rt4_callback_div14_124_tt：TT27°C、1.2V、24MHz理想10ps参考、10fF，20µs/4线程AX8ps/1e-3/traponly/noise-off，2ns保存10001点。相对123只改变K28→K9的VK0/VK2/VK4三位、stop120→20µs、注释和额外保存14个配置节点。callback110几何/尺寸/模拟、recenter109控制器和原复位配置/10µV差分LC种子均不变，供电预先1.2V。无强制粗码/DAC、nfilt暖初值、readic或状态绕过；不是123状态续跑。

捕获时计数路径固定为RF/4，与最终输出÷14分开。冻结RTL的粗目标K×M×8=1008，细调/新复测目标4032；使能后监督才以最终输出K=9计数。不能把K×32=288误用为本任务粗目标。新增保存XP.s0..s5、XP.XC.ak0..ak5、cfg_invalid、divider_reset；预定核查1µs后K9、仅s5高、ready高、invalid/reset低。末1µs参考间隔观察器RF/输出均值比按14和0.5%相对误差作分频功能筛查，它不是精确RF边沿计数或锁定验收。

396ref粗试预计17.25µs进入细调，实际选码以新波形为准。20µs不覆盖完整复测/交接；未使能或qualified低是前段边界，不按捕获失败处理。参数化解码器已在123全部18个EVAL及121全部20个EVAL回放一致，这是分析器验证，不是K9物理结果。120µs上限和八次复测预算不变。

协议results/rt4_callback_div14_124_protocol.json，输入manifest research/rt4_callback_div14_implementation124.json，唯一pipeline research/rt4_callback_div14_124_pipeline.json。核验既有thu-xia/uid528和实时零任务后唯一派发；计算cwd/input/raw/log/final/tmp全部在/server_local_ssd/jielu/IP-PLL-GPT6。实时进程、SSD目录和初始保存进度见active及审计，不按历史PID判断存活。

仅运行research/audit_rt4_callback_div14_124.py UNIQUE.json（basename）与poll_rt4_callback_div14_124.py。runner存活由其回收；消失只通过pipeline旁OS锁接续原目录，无常驻派发owner，不重启launcher/runner/仿真。123已completed_reviewed_capture_pass/do_not_restart，停止123和所有旧任务的poll。

终态两次独立≥60秒稳定、退出0/零错误/PSF END、input/raw/log/final.ic哈希及10001点0–20µs有限物理波形；审计需有final_state_sha256/completed_output_hashes，下载未完稍候另存新审计。然后review_rt4_callback_div14_124.py 审计A 审计B 新输出JSON，核对1008/4032目标、实际转移/细调入口、配置/分频观察器、偏置、状态/error/restart。根据真实结果继续最少必要TT，不预设成功，不扩33点/PVT/种子/方法矩阵。

原109旧几何K41、callback121 K41、123 K28及局部诊断分别保留；全部旧任务完成禁止重启/重复回收。callback噪声仍未测，旧115.2fs不可移植；最终10kHz至fOUT/2排除杂散RMS<200fs不变。WPE默认off，CDF默认几何不是版图/PEX，尺寸修改须重新callback。功耗和后端后置，不开始版图。
