# 第117次：物理细调两点完成，转向自主SAR选码

## 完成结果

DAC32配对`rt4cbmid116ssd01 / rt4_callback_mid116_tt`已自然完成。7µs、700001个有限物理采样点，退出0、零错误、PSF END及输入/raw/日志/final.ic哈希通过；两次独立稳定终态相隔99.266142秒。Spectre耗时18分6.0秒。流水线已completed_reviewed_diagnostic，禁止重新派发、重启或重复poll回收。

与已完成115的DAC49试验相同，固定粗码8，实际DAC、预置滤波器、禁用CP、RF÷4/RT4、计数器与快照参与；1MΩ/10pF偏置从nfilt=.728V释放。仅两个外部DAC输入位改变，窗口均为128参考周期等长。

| 量 | DAC32 | DAC49（115） |
|---|---:|---:|
| 真实快照计数 | 5232 | 5254 |
| 相对5248误差 | −16 | +6 |
| 物理门控时钟边沿 | 5232 | 5254 |
| 测量窗口RF均频MHz | 3924.030978 | 3940.716448 |
| 末段ctrl均值V | .591714577 | .899053024 |
| 末段RF均频MHz | 3923.454694 | 3940.069328 |
| 末段nfilt均值V | .732077509 | .732082033 |
| 末段nfilt斜率mV/µs | +.183863 | +.189238 |

两个快照均与对应物理gclk边沿一致，且窗口内acqclk和缓冲时钟边沿数一致。当前两个窗口未发现漏计或多计；不据此外推所有PVT/码/启动条件下的计数可靠性。

1.7–2.0、3.7–4.0、6.5–6.8µs三段以及各100ns子窗，DAC32的RF均低于3936MHz，DAC49均高于3936MHz，均正确÷4。对应nfilt均值差为2.962/3.303/4.524µV。局部真实DAC两点包围目标，支持这些条件下的细调能力；偏置仍漂移，两次记录各自从同一初值开始，不是顺序二分或同一渐近稳态曲线。没有通过插值指定所谓锁定码。

离线RTL方向：DAC32/−16应向较高细DAC搜索，DAC49/+6应向较低细DAC搜索。两者均不满足粗码修正边缘条件，也不在±1合格区间。局部夹具没有执行完整FLL，这不代表实际发生了自动修正、连续合格或HANDOFF。

[DAC32完整结果](results/rt4_callback_mid116_review117.json) · [两点对照](results/rt4_callback_count_comparison117.json) · [DAC49结果](results/rt4_callback_margin115_review116.json)

原始输入、波形、日志及final.ic在research/runs/spectre_cmos_v14_full/rt4cbmid116ssd01/rt4_callback_mid116_tt。独立审计callback_mid116_terminal117_a.json、callback_mid116_terminal117_b.json及哈希列于结果JSON。物理波形均有限，units元数据NaN单独排除。

## 唯一117任务：20µs自主粗码搜索前段

已验证局部调谐能力之后，剩余关键问题是完整硬件从原复位/配置流程实际选择哪一粗码。下一项`rt4cbsar117ssd01 / rt4_callback_sar117_tt`使用冻结callback110完整电路、recenter109控制器和原109的复位/配置/LC差分种子激励，仅观察前20µs。没有强制粗码或DAC，没有暖nfilt初值、状态加载、跳过状态机或修改硬件。

选择20µs的依据：原109粗码搜索约17.25µs结束，20µs可覆盖端点测量、8次粗码判断及进入细调后的状态。实际是否按该时间完成由新波形决定。这是启动前段观察，不以20µs代替120µs锁定验收，不增加原八次复测预算。预先建立1.2V电源后复位，不是供电爬升试验。

仅K41/TT27°C/1.2V/24MHz/10fF，AX8ps/reltol1e-3/traponly/noise-off，4请求线程；2ns保存间隔，预期10001点0–20µs。RF/输出频率辅助观察使用原有内部周期观察器，2ns保存波形不能直接用于RF边沿计数或抖动测量。

- [独立协议](results/rt4_callback_sar117_protocol.json)，输入manifest research/rt4_callback_sar_implementation117.json，唯一流水线research/rt4_callback_sar117_pipeline.json。
- 审计research/audit_rt4_callback_sar117.py UNIQUE.json；唯一有界回收入口poll_rt4_callback_sar117.py。runner存活由其回收，消失才用pipeline旁OS锁接续原SSD目录；禁止重复启动launcher、runner或仿真。
- 终态须两次独立相隔至少60秒稳定观察、退出0/零错误、PSF END、input/raw/log/final.ic哈希及10001个有限物理点。分析入口`review_rt4_callback_sar117.py 审计A 审计B 新输出JSON`。
- 逐次解码稳定EVAL的粗码/DAC/快照，核对目标1312与`measured>1312`的实际SAR分支；报告最终粗码和进入细调的时刻、ctrl/nfilt、enable/range_error/restart/qualified。正常前段qualified低不应当作完整捕获失败。

完成后依据真实自主选码及偏置轨迹判断下一项必要验证，不机械继续扫码、不直接延长记录或复测预算，不强制绝对码冒充闭环成功。

## 版本边界

115/116两项7µs固定码试验、114两项2µs局部诊断、113端点、110六项配对以及原109和其他旧队列均已完成，不再派发或回收。原109的持续qualified/15.815ppm属于旧几何版本，其新增粗码修正分支未触发；不能移植给callback或拼接全频通过。

callback110器件尺寸及派生几何保持；WPE默认off，CDF默认几何不是版图/PEX，尺寸变化需重新callback。原4.4fF采用基线保留。最终10kHz至fOUT/2排除杂散RMS<200fs不变，115.2fs仅原RT4高偏移阶段依据；频偏不是抖动。功耗和后端后置，没有开始版图。
