# 第116次：真实DAC49计数完成及中点配对

## 已完成的115局部诊断

`rt4cbmargin115ssd01 / rt4_callback_margin115_tt` 已自然完成并回收。7µs、700001个有限物理采样点、退出码0、零错误、PSF END、输入/raw/日志/final.ic哈希均通过；两次独立终态间隔90.377750秒。Spectre实际耗时18分1.4秒。115流水线已关闭，禁止重新派发、重启或再次poll回收。

固定粗码8、真实DAC49，实际预置滤波器、禁用CP、RF÷4/RT4、MOS计数器及快照参与，真实1MΩ/10pF偏置网络从nfilt=.728V初值释放。外部门控覆盖128参考周期等长窗口。

- 快照5254，物理门控时钟、窗口内acqclk和缓冲后时钟均为5254个上升沿；目标5248，误差+6。该窗口没有观察到计数器漏计或多计。
- 窗口内RF平均3940.716448MHz；计数折算3940.5MHz，两者采用不同测量口径，不能把整数计数量化当作丢边沿。
- 1.7–2.0、3.7–4.0、6.5–6.8µs三段RF分别3941.382350、3940.680374、3940.069328MHz，均正确÷4。最后一段三个100ns子窗最低3939.577916MHz，仍高于3936MHz。
- 三段ctrl均值约.89906/.89905/.89905V；最后一段ctrl峰峰值41.100mV，preset均值.899299V。理想空载DAC49=.91875V不是实际控制电压。
- nfilt均值.730724/.731352/.732082V，最后一段斜率+.189238mV/µs；nb均值约.734064V。偏置仍漂移，不能称渐近稳态。

离线代入冻结RTL：DAC49且计数偏高，不满足要求偏低的粗码-1条件，也不满足低DAC端粗码+1条件；误差超过±1。该样本若送入正常复测判断，应走细DAC二分降低方向。夹具不含完整FLL状态机，此判断不代表实际执行了任何分支，更不证明连续两次合格、HANDOFF或锁定。

分析脚本修正独立于仿真：原115分析器对保存波形插值得到的门控长度要求2fs误差，实际10ps保存栅格在下降沿造成约−.833325ps插值偏差。原脚本保留；新版`review_rt4_callback_margin116.py`逐点核对冻结PWL（最大电压残差9.58e-11V），将插值边沿误差限制在一个保存间隔内，并按精确PWL半幅时刻核对128周期时长。未修改输入、波形或仿真。

证据：[完整分析](results/rt4_callback_margin115_review116.json)、[原协议](results/rt4_callback_margin115_protocol.json)。独立审计在research/margin115_terminal116_a.json、margin115_terminal116_b.json，哈希收录在分析结果。

## 唯一下一项：DAC32配对

`rt4cbmid116ssd01 / rt4_callback_mid116_tt` 是一个7µs、2线程、TT AX8ps/1e-3/traponly/noise-off任务。保留115夹具全部电路、初值、门控、保存步长、负载及粗码8，仅DAC49改为新计数复测的起始中点32（只改变外部d0、d4源）。器件尺寸和callback派生几何保持。

目的：检查实际中点计数是否在5248的另一侧，与已测DAC49形成同夹具条件下的细调范围证据。DAC32来自冻结控制器的起始规则；未假定49处未知搜索上下界，也未将32说成上一次计数决定的下一码。这是两次相同初值的独立局部试验，不是连续自主二分轨迹。

输入协议：[rt4_callback_mid116_protocol.json](results/rt4_callback_mid116_protocol.json)。流水线research/rt4_callback_mid116_pipeline.json；输入manifest research/rt4_callback_mid_implementation116.json；审计research/audit_rt4_callback_mid116.py UNIQUE.json；唯一有界入口poll_rt4_callback_mid116.py。runner存活时由其回收，消失时只接续原SSD目录，禁止重启launcher/runner/仿真。

终态后需要两次相隔至少60秒审计、退出0/零错误、PSF END、input/raw/log/final.ic哈希及700001点0–7µs有限波形。用`review_rt4_callback_mid116.py 审计A 审计B 新输出JSON`分析，并和本次DAC49结果比较。正常运行不重复通知；发现计数不一致或终态异常时先定位证据，不用旧队列资源断言。

## 边界与延续

115与114还存在真实DAC/滤波器/禁用CP/计数负载等差别，不能把频率变化单独归因于偏置。固定粗码、暖偏置短诊断不能代替自主SAR、完整捕获、渐近稳态或噪声；本次未修改交接阈值、8次复测预算、120µs长记录或模拟参数。

原109的120µs K41捕获通过仅属于旧几何版本，其新增粗码修正分支未触发。callback110、原4.4fF采用基线、仅4.8fF与各控制器独立保留，不能移植旧三个低端结果或拼接全频通过。最终10kHz至fOUT/2排除杂散RMS<200fs不变；频偏不是抖动。WPE保持PDK默认off，默认CDF几何不是版图/PEX；尺寸变化须重新callback。功耗及后端继续后置，没有开始版图。
