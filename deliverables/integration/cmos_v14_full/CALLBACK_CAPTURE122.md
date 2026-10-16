# 第122次：callback版K41完整捕获通过，转入低RF端自主选码

callback110参数版首次完整K41 TT捕获已经自然完成，原runner回收后独立核验通过。没有重启或修改121。独立结果属于本参数版；原109旧几何的结果单独保留。

## 完成与证据

- rt4cbcapture121ssd01 / rt4_callback_capture121_tt，0–120µs共60001点，全部物理波形有限；units元数据排除。
- 退出码0、零错误、PSF END；输入/raw/日志/final.ic本地与远端哈希一致；两次独立终态间隔182.822462秒且一致。
- Spectre日志实际墙钟14小时5分22秒。TT27°C、1.2V、24MHz、K41/M4、10fF；AX8ps/1e-3、traponly、noise-off。
- 原复位/配置与10µV差分LC种子，供电预先建立；没有强制粗码/DAC、暖偏置初值、readic或状态绕过。

协议与全部20个EVAL回放一致：端点加八次粗SAR依次为0/128/64/32/16/8/4/6/5，对应计数1326/1046/1166/1239/1280/1302/1314/1308/1311；17.252µs进入粗6细调。六次细SAR的DAC32/48/40/44/42/43、计数5239/5259/5245/5250/5246/5247，随后按规则丢弃旧候选，从DAC32重新复测。

| 新复测 | DAC | 实际计数 | 相对5248误差 | 实际下一步 |
|---|---:|---:|---:|---|
| 1 | 32 | 5236 | −12 | DAC43 |
| 2 | 43 | 5246 | −2 | DAC48 |
| 3 | 48 | 5255 | +7 | DAC45 |
| 4 | 45 | 5249 | +1 | 同码再次计数 |
| 5 | 45 | 5249 | +1 | HANDOFF |

所有复测粗码均为6。五次消耗在原八次预算内，连续两次同粗/细码合格。86.420µs进入HANDOFF，采样的1.332µs时长与32ref=1.333333µs在2ns保存误差内一致；87.754µs acquired与enable同时拉高。一次粗码余量修正分支未触发，不能把本次通过归因于该分支修复成功，也不构成该分支的物理验证。

## 使能后的实际表现

- frequency_good从89.336µs持续为高；qualified从90.670µs持续到120µs。全记录没有range_error或restart。
- 使能后观察32.246µs，持续qualified29.330µs，均超过512ref/21.333µs监督时长。这解决本次记录是否覆盖一个监督窗口的问题，不等于长期稳定性签核。
- qualified窗口内部观察器平均输出984.000129MHz，最差测频偏差18.719406ppm。
- 末1µs平均输出983.999732MHz，平均偏差−0.272093ppm，最差6.720885ppm；qualified与frequency_good均为100%。原定功能快筛通过。
- 包含捕获瞬态的全部使能窗口最差387.805356ppm，应与持续qualified窗口区分。

2ns保存不能解析RF边沿；频率来自原内部参考间隔周期观察器。这里的ppm是测频偏差，不是抖动或相位噪声。

偏置与控制电压仍缓慢变化：末5µs时间加权ctrl均值.749742V、线性斜率−3.073154mV/µs；nfilt均值.739711586V、斜率−.110599mV/µs。末1µsctrl时间均值.743718603V、54.244956mVpp，nfilt时间均值.739493456V。不能把持续qualified等同于偏置渐近稳态，也不能拿这段noise-off波形宣称RMS<200fs。数据分段见results/rt4_callback_capture_detail122.json。

## 下一项仅检查低RF端启动

K41已经给出新版本自身的高端单点整环证据。callback低RF端此前只有外部固定码/暖偏置局部结果，尚无从复位的真实选码证据。因此只选择K28/M4（输出672MHz、RF2688MHz）一个20µs前段，保留相同分频模式以聚焦低RF端选码；停止固定码扫描。

rt4cblow122ssd01 / rt4_callback_low122_tt：20µs、4线程、TT AX8ps/1e-3/traponly/noise-off、2ns保存，预期10001点。相对121只改配置K41→K28的四个输入位、stop120→20µs和注释；callback几何/尺寸、模拟和控制器不变。无强制码、暖偏置、readic或状态加载。

粗试目标为K×32=896，细调/复测目标K×128=3584。冻结端点+八次粗试最长396ref，预计17.25µs进入细调，20µs可回答低端是否可自主选码；实际是否到达以波形为准。不是短版完整捕获，20µs仍未使能/qualified低不能据此报锁定失败。原八次预算未改。

独立协议results/rt4_callback_low122_protocol.json；输入manifest research/rt4_callback_low_implementation122.json；唯一pipeline research/rt4_callback_low122_pipeline.json。新解码器仅参数化目标计数，回放已完成121的20个EVAL与原分析完全一致，属于分析器验证而不是新物理结果。派发前核验同thu-xia/uid528、实际零任务，再唯一派发；以最新active和审计中的真实进程为准。

用research/audit_rt4_callback_low122.py UNIQUE.json及唯一poll_rt4_callback_low122.py协调。runner活着由其回收，消失才通过pipeline旁OS锁接续原SSD目录。禁止重启或重复派发。121已completed_reviewed_capture_pass/do_not_restart，不再执行其poll。

122终态需独立两次≥60秒稳定，退出0/零错误/PSF END、输入/raw/log/final.ic哈希、10001点0–20µs有限物理波形。审计须含final_state_sha256/completed_output_hashes。完成后review_rt4_callback_low122.py 审计A 审计B 新输出JSON，逐次核对896判据、真实下一粗码、细调入口、偏置、状态及错误，不预设选码成功。

原4.4基线、旧109、callback局部与整环证据分开，不拼接全频通过。75种尺寸callback及21,479个MOS尺寸不变，WPE默认off，CDF默认几何不是版图/PEX。最终10kHz至fOUT/2排除杂散RMS<200fs、杂散/全频/PVT等缺口保持；功耗与后端后置，不开始版图。
