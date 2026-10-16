# 第123次：低RF端自主粗SAR通过，验证连续捕获

callback参数版K28/M4（输出672MHz、RF2688MHz）的20µs启动前段已经自然完成并独立核验，未重启或修改122。它回答了低端实际选码问题；完整捕获还没有结论。

## 122的实测轨迹

rt4cblow122ssd01 / rt4_callback_low122_tt：10001点0–20µs有限物理波形、退出0、零错误、PSF END、input/raw/log/final.ic本地远端哈希均通过。有效独立终态相隔88.900239秒；Spectre实际墙钟1小时54分43秒。早先A/B仅56.263073秒，review按原门槛拒绝且未生成结果；补充C后通过，未放宽断言或修改数据。

| 稳定EVAL粗码 | DAC | 实测计数 | 相对896误差 | 真实下一粗码 |
|---:|---:|---:|---:|---:|
| 0 | 11 | 1326 | +430 | 128 |
| 128 | 11 | 1046 | +150 | 192 |
| 192 | 11 | 955 | +59 | 224 |
| 224 | 11 | 917 | +21 | 240 |
| 240 | 11 | 899 | +3 | 248 |
| 248 | 11 | 890 | −6 | 244 |
| 244 | 11 | 895 | −1 | 242 |
| 242 | 11 | 898 | +2 | 243 |
| 243 | 11 | 897 | +1 | 245 |

端点与八次粗SAR全部符合冻结RTL；最后保留243后按原规则加2，在17.252µs进入粗245/DAC32细调。没有强制码、暖偏置、readic或状态绕过，也没有修改粗SAR判据。实际计数来自MOS快照。

19–20µs ctrl时间均值.591238812V；nfilt时间均值.729494958V、线性斜率+.351868mV/µs，nb均值.734062909V。内部参考间隔周期观察器的RF时间均值2686.183855MHz，不能代替FLL测频窗口或精确RF边沿计数。2ns保存不能解析RF沿。

enable/acquired/qualified/frequency_good全程未拉高，range_error与restart也未拉高。20µs仅到细调入口，尚无细调EVAL、新复测或交接；这不是完整捕获失败，也不是锁定通过。一次相邻粗码修正尚未在这段记录执行。

## 下一项必要性与预算

K41已有callback参数版自身的完整捕获证据；低RF端现在已有从原复位自主选码证据。剩余问题是K28连续细调、新复测的同码连续合格、实际交接，以及使能后是否持续qualified。继续增加固定粗/细码点不能回答这些问题，因此只安排一个K28完整控制器捕获。

新任务rt4cblowcap123ssd01 / rt4_callback_lowcapture123_tt：K28/M4、TT27°C、1.2V、24MHz、10fF、120µs/4线程、AX8ps/1e-3/traponly/noise-off、2ns保存，预期60001点。相对122只有注释与stop20→120µs变化，冻结callback110几何/尺寸/模拟参数和recenter109控制器。仍从原复位配置和10µV差分LC种子启动，供电预先1.2V；不加载final.ic，不是122状态续跑。

长度是按状态覆盖选择：粗试最多396ref、细SAR840ref、新复测最多1312ref、HANDOFF32ref，加约.75µs配置释放，最晚约108.25µs使能。60/80µs会截断部分合法搜索路径，之后又需从复位重跑。120µs保留原上限和八次预算；最晚路径仅留下11.75µs，短于512ref/21.333µs监督时长。必须报告真实enable/qualified区间及观察边界，不能预先宣称覆盖完整监督窗口。旧122前段耗时1h54m43s，K41完整记录14h5m22s；新任务12–16小时仅为规划量级，不保证ETA。

粗目标896、细/新复测目标3584。分析器沿用参数化解码器，回放122九个和121二十个EVAL分别与既有结果一致；测频偏差分母取本任务672MHz，另用既有984MHz记录回归。这些是分析器验证，不是新的物理结果。末1µs原功能快筛门限不变，还需全轨迹符合控制器、无error/restart；频偏不是抖动。

唯一协议results/rt4_callback_lowcapture123_protocol.json，输入manifest research/rt4_callback_lowcapture_implementation123.json，唯一pipeline research/rt4_callback_lowcapture123_pipeline.json。派发前核验既有thu-xia/uid528及真实零任务，再唯一派发；初始进程与SSD目录见active和实时审计，不按旧PID推断状态。

只运行research/audit_rt4_callback_lowcapture123.py UNIQUE.json和poll_rt4_callback_lowcapture123.py。原runner存活由其回收，消失才通过pipeline旁OS锁接续原SSD目录；没有常驻派发owner，禁止重启launcher/runner/仿真。122已completed_reviewed_diagnostic/do_not_restart，停止旧poll。所有旧任务保持完成或退役。

终态需两次独立≥60秒稳定、退出0/零错误/PSF END、input/raw/log/final.ic哈希和60001点0–120µs有限物理波形。units元数据NaN排除。独立审计须含final_state_sha256/completed_output_hashes；下载未完时稍候新审计。完成后review_rt4_callback_lowcapture123.py 审计A 审计B 新输出JSON，检查896/3584目标、实际下一码、八次预算、相邻粗修正方向/优先级/次数、同码连续合格、32ref交接、enable/acquired/qualified/frequency_good/error/restart。

原109旧几何与callback K41/K28、局部/完整证据分别保留，不能拼接全频通过。K41在90.670–120µs持续qualified、最差18.719ppm，但ctrl/nfilt仍漂移。callback噪声未测；最终10kHz至fOUT/2排除杂散RMS<200fs保持。WPE默认off，CDF默认几何不是版图/PEX；尺寸变化需重新callback。功耗和后端后置，不开始版图。
