# 第40次噪声与抖动审阅

2026-10-04T10:20:28+08:00。CF40候选的实际LC暖启动慢漂移已收敛；RT4工作点通过真实粗调下移，继续细调。新输出链全带噪声、六沿/逐模块noise-on和长周期积分校准正在进行；实际LC PSS仍未通过，整机随机RMS未知，功耗优化暂缓。

## 已完成的实际电路进展

CF40实际LC使用自身3us终态追加6us、1ps/TT27/1.2V/Q5/原RT/10fF完成0error。第2至6个1us窗口均通过原稳态门限；末窗输出983.999999038MHz、相位峰峰6.160883e-05rad、漂移7.406821e-06rad/us，解决此暖启动工况的慢漂移。不是冷上电、PSS或整环噪声验收。

首个窗口的周期计数包含观察器初始零值，原始统计保留为失败；944.4MHz统计均值不是电路真实掉频。第2至6窗口不含该无效区间，最后窗口验收门限没有放宽。偏置nfilt末1us线性漂移约−0.755uV/us，不能替代长期平衡或冷启动。见[CF40结果](results/core_cf40_settle_validation.json)。

RT4实际MOS粗调D接口码23/24对照均完成：RF3944.573458/3933.489792MHz。同码23接口对照相对原夹具仅−9.533kHz、摆幅−0.000634%，通过250kHz/0.5%门限；粗码24可继续向上细调。0.75V单点已接替释放的短槽启动，不外推或改写动态储能。 条件为TT27、1.2V、Q5、CF10、RT4、修复分频器、10fF和0.657998867V控制钳位，750ns/1ps，末500ns密集保存。两个粗调码均由实际MOS触发器时钟写入，没有篡改存储状态。码23到24的实测RF变化为−11.083666MHz；不能把离散粗码作连续插值。见[粗调结果](results/rt4_coarse_program_validation.json)、[下一个细调点](results/rt4_code24_tuning_protocol.json)。

## 实际LC周期解的诊断

Gear2实际LC初始化快照已校验2,529,026,048字节及SHA。末两250ns输出各246沿，但共同提前0.867613ps，C1同相位终值增加0.739400mV，显示残余确定性漂移；不是随机抖动。当前完整残差历史：Conv norm = 7.77e+06, max dI(XP.XV.XL.XP.LW:1) = 15.5452 mA, took 2.93894 ks.；Conv norm = 611e+03, max dV(XP.XR.ob) = -182.96 mV, took 1.84923 ks.尚无有效周期解。

识别到运行中PSF末记录被缓存截断：稳定文件哈希不代表记录完整。保留原始文件，舍弃唯一不完整记录，截止最后完整点4.384022182742564us，仍比较整两个250ns。用既有完整原始文件回归，全部原测量行和时间窗完全一致。 相邻窗口内参考各6沿、输出各246沿。所选保存电压最大轨迹差约37.13mV，输出最大差约12.95mV；这些属于方法改变后未完全稳定的确定性轨迹。没有测量随机噪声，也没有证明全部隐藏状态或PSS失败根因。正在运行的Newton迭代结果与初始化轨迹分别记录，不能混为一组数据。见[周期对比](results/core_gear_initial_period_drift.json)、[传输及尾记录审计](results/core_gear_live_tstab_audit.json)、[完整文件回归](results/core_period_drift_parser_control.json)。

## 噪声检查与未完成项

修复后分频器RT4全带10kHz–492MHz及25个谐波邻近点仍在PNoise，尚无新RMS。已启动对应新电路六个输出沿和FF/缓冲/RX/分频/辅助五组独立noise-on，每例fresh PSS；旧电路验证不直接转移。

独立RC的4MHz PSS已收敛，但dec20 PNoise约15分钟仅到25.1189kHz，已主动SIGINT并完整回收；不是电路失败，没有合格噪声结果，原细网格例未运行。改为10k/1M/2M/10M/100M/492MHz六点，对照解析采样RC协方差；理论谱纹波界小于4e−22，适用于此线性热噪声校准。1ps/default maxacfreq与0.25ps/1THz两例已有限排队在0.75V调谐点之后。逐点PSD、解析积分及自动Jee/2MHz边界均须核对；不能代替实际MOS全频带、非等价边沿或完整PLL验证。

原局部链TT27/1.2V/984MHz/10fF、外部无噪声RF下，原尺寸/RT2/RT4暂定141.281/90.867/63.275fs仍只属于原分频器夹具。修复分频器RT4相对RT2六点PSD改善约3dB已证实，不能用六点宣称完整RMS。**完整PLL的<200fs指标仍未验证**；连续闪烁噪声谐波附近积分和246个非等价沿等问题仍需关闭，不能凭RC通过便推及MOS。详见[新电路noise-on协议](results/rt4_pulsetrip_audit_protocol.json)、[RC六点校准协议](results/core_noise_calibration_sparse_protocol.json)、[密扫停止审计](results/core_noise_calibration_cancellation.json)。

严格64us完整PLL在2026-10-04T10:13:27.842825+08:00已到57.380us，coarse23/DAC36/state5，qualified=高。仍为中途观测，需跑完并核对保持、锁定时间及精度差异。

## 接续

先审阅正在运行的实际噪声和测量控制，推进同码细调/真实环路交接。CF40、RT4和修复分频器均未合并主`pll_capture_v14`。功耗仅记录；4mW及面积目标保留，优化后置。

复现入口：`analyze_core_cf40_settle.py`、`analyze_rt4_coarse_program.py`、`analyze_core_period_drift.py --run coretripgear01 --case core_pulsetrip_gear_noise_tt --snapshot live_tstab --audit core_gear_live_tstab_audit.json --output core_gear_initial_period_drift.json`。新结果完成后使用`analyze_core_noise_calibration.py --protocol core_noise_calibration_sparse_protocol.json`、`analyze_rt2_fine_audit.py --factor 4 --bank pulsetrip`、`analyze_rt4_code24_tuning.py`。
