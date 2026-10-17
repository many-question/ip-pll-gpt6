# 第125次：K9/÷14自主前段通过，验证完整交接

callback版K9/M14（目标输出216MHz、RF3024MHz）20µs自主前段124已自然完成。真实配置、输出分频和全部粗SAR转移符合预定检查；17.252µs进入粗155/DAC32细调。此结果只覆盖启动前段，尚无K9完整捕获结论。

## 124完整性与实际结果

rt4cbdiv14124ssd01 / rt4_callback_div14_124_tt：20µs/10001有限物理点、退出0/零错误/PSF END，input/raw/log/final.ic哈希一致；units元数据NaN排除。原runner自然完成回收，未重启。Spectre实际1小时55分15秒。首份终态审计A发生在final.ic下载完成前，保留但未用于review；完整B/C审计相隔86.191651秒，满足原60秒门槛。结果见results/rt4_callback_div14_124_review125.json及rt4_callback_div14_124_detail125.json。

捕获计数通路是RF/4，粗目标1008=K×M×8，细/新复测目标4032；使能后的最终输出监督使用K=9。这与输出÷14属于不同阶段，不能套M4的K×32公式。

| 粗码 | DAC | 实测计数 | 相对1008误差 | 实际下一粗码/DAC |
|---:|---:|---:|---:|---|
| 0 | 11 | 1326 | +318 | 128/11 |
| 128 | 11 | 1046 | +38 | 192/11 |
| 192 | 11 | 955 | -53 | 160/11 |
| 160 | 11 | 998 | -10 | 144/11 |
| 144 | 11 | 1022 | +14 | 152/11 |
| 152 | 11 | 1010 | +2 | 156/11 |
| 156 | 11 | 1005 | -3 | 154/11 |
| 154 | 11 | 1008 | +0 | 153/11 |
| 153 | 11 | 1009 | +1 | 155/32 |

九次稳定EVAL全部符合冻结RTL，最后153→155/DAC32为实际自主转移。没有强制绝对码、暖nfilt、readic或状态绕过。20µs尚未完成细调、新复测、粗修正或HANDOFF；enable/acquired/qualified/frequency_good均低，无range_error/restart。前段低qualified不是捕获失败。

1µs后active K始终9，仅s5高（选择向量32），cfg_ready始终高；cfg_invalid/divider_reset峰值8.168/8.244mV。末1µs有24个有效参考间隔观察器更新：RF均值3023.068548MHz、输出均值215.933490MHz，比值13.999998535，满足14±0.5%的分频功能筛查。2ns保存不能直接计RF沿或精确占空比，观察器均值不是FLL计数窗，也不是锁定验收。

末1µs ctrl时间均值.591494227V、28.729835mVpp、斜率−.773242mV/µs；nfilt均值.732294169V、2.762346mVpp、斜率+.034189mV/µs；nb均值.734064555V。存在纹波和窗口相关性，不证明渐近稳态或噪声。观察器RF时间均值3023.068542MHz与上述更新均值的统计方法分开保留。

## 首次K9/M14完整捕获125

K41/M4与K28/M4已分别完成捕获；124补上最大分频模式的配置及自主选码证据。剩余缺口是连续细SAR/新复测、同码连续合格、物理交接，以及从RF/4捕获切换到最终输出÷14监督后能否持续qualified。固定码夹具不能回答这个问题，因此不追加固定粗/细码扫描，只安排一个从原复位启动的K9/M14完整记录。

rt4cbdiv14cap125ssd01 / rt4_callback_div14capture125_tt：TT27°C、1.2V、24MHz理想10ps参考、10fF，120µs/4线程AX8ps/1e-3/traponly/noise-off，2ns保存60001点。相对124仅注释和stop20→120µs改变，额外配置节点保存保留。callback110尺寸/几何/模拟、recenter109控制器和八次预算均冻结；原复位配置及10µV差分LC种子、预先1.2V供电，没有强制码、nfilt暖初值、readic或状态绕过，不是124状态续跑。

记录长度按冻结时序审查：396ref粗试+840ref细SAR+最多1312ref新复测+32ref交接，加约.75µs配置，最晚约108.25µs使能。60/80µs会截断合法搜索路径并要求另一次复位试验；120µs保持原上限。最晚路径仅余11.75µs，小于512ref/21.333µs监督时长，必须报告实际使能/qualified持续区间和观察边界，不预设成功或覆盖完整监督窗口。机器时间12–16小时只是规划量级。

125分析器保持1008/4032目标、216MHz频偏分母，增加全记录配置与末1µs÷14观察器检查；在已完成124九个、123十八个、121二十个EVAL回放一致，配置/分频分析回放124一致。此为分析器验证，不是125物理结果。

协议results/rt4_callback_div14capture125_protocol.json；输入manifest research/rt4_callback_div14capture_implementation125.json；唯一pipeline research/rt4_callback_div14capture125_pipeline.json；交接manifest research/rt4_callback_div14capture_handoff125.json。派发前核验同thu-xia/uid528及实际零任务。原SSD计算输入、cwd、raw、日志、final/tmp均在/server_local_ssd/jielu/IP-PLL-GPT6，初始真实身份和进度见active及审计。

只运行research/audit_rt4_callback_div14capture125.py UNIQUE.json（basename）及poll_rt4_callback_div14capture125.py。原runner活着由其回收；消失只经pipeline旁OS锁接续原SSD目录，不重启runner/launcher/仿真。124已completed_reviewed_diagnostic/do_not_restart，123/121与全部旧任务保持完成，禁止再poll或重复回收。

终态仍需两次独立≥60秒稳定、退出0/零错误/PSF END、input/raw/log/final.ic哈希和60001点0–120µs有限物理波形；完整审计需final_state_sha256/completed_output_hashes。随后review_rt4_callback_div14capture125.py 审计A 审计B 新输出JSON，逐次核查新计数、实际转移、粗修正优先级/方向/次数、八次总预算、连续同码合格、32ref HANDOFF、使能与全部状态/error/restart、配置和分频。

末1µs功能快筛门限保留平均频偏与跨度各≤.5%、qualified/frequency_good各≥99%、range_error<.2V，并要求完整控制轨迹吻合且无error/restart；最差ppm单列。冷复位/FLL期间qualified低正常，2ns观察器频偏不是抖动。

原109、callback121 K41/M4、123 K28/M4和124前段分别保留，不拼接全频。121/123的相邻粗码修正未触发，仍缺该分支物理验证。callback噪声未测，旧115.2fs及旧三个低端/6.821ppm不可移植；最终10kHz至fOUT/2排除杂散RMS<200fs不变。WPE默认off，CDF默认几何不是版图/PEX，尺寸修改须重新callback。功耗及后端后置，不开始版图。
