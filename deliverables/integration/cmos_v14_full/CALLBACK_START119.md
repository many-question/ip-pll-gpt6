# 第119次：实际选中粗码6的DAC49计数完成

118局部试验`rt4cbedge118ssd01 / rt4_callback_edge118_tt`自然完成并由原runner回收。7µs、700001个有限物理点、退出0、零错误、PSF END及input/raw/log/final.ic哈希通过；两次独立终态相隔71.874794秒，Spectre实际耗时18分22.1秒。units元数据NaN单独排除。118流水线已completed_reviewed_diagnostic，禁止重启、重复派发或再poll回收。

## 计数与上侧余量

保持callback110几何、尺寸及模拟参数，外部固定117实际SAR选中的粗码6，DAC49取自冻结控制器的上侧粗码修正门槛。真实DAC、预置滤波器、禁用CP、RF÷4/RT4及MOS计数器/快照参与。nfilt初值0.74006129886311578V在t=0释放，保留1MΩ/10pF网络；其他状态重新初始化，未加载117状态。

128参考周期等长门控窗口为1.500005–6.833338333333333µs。稳定快照 **5265**，相对目标5248为 **+17**；物理门控时钟、acqclk和缓冲计数时钟均为5265个上升沿。本窗口未发现计数与物理边沿不一致。窗口RF均频 **3948.714549MHz**，由10ps保存波形的差分过零边沿测得；不是抖动。

| 观察窗口µs | RF均频MHz | 输出均频MHz | ctrl均值V | nfilt均值V | nfilt线性斜率mV/µs |
|---|---:|---:|---:|---:|---:|
| 1.7–2.0 | 3947.163520 | 986.792256 | .898993173 | .741280769 | −.472103 |
| 3.7–4.0 | 3948.544428 | 987.137588 | .898992399 | .740447253 | −.407128 |
| 6.5–6.8 | 3950.172476 | 987.549828 | .899004906 | .739466652 | −.343546 |

三段均正确÷4；九个100ns子窗中最低RF均频3946.959014MHz，比3936MHz目标高10.959014MHz。该数值只描述指定初值、负载和短记录下的条件上侧余量，不证明渐近稳态。nfilt仍下降，RF随记录时间变化；没有隔离因果。末段ctrl纹波44.049mVpp、preset均值0.899289817V，真实DAC49不能用理想空载值0.91875V替代。

离线代入冻结RTL：`need_faster`、`need_slower`、`within_one_count`均为false；正误差应使细DAC搜索向低侧移动。夹具未运行FLL状态机，没有已知完整搜索区间，不能由此指定下一DAC，更不能称粗码修正已执行、两次连续合格或锁定。单点结果降低了“本条件下粗6在DAC49仍不够高频”的担忧，但尚未给出同条件低侧计数。

[完整结果](results/rt4_callback_edge118_review119.json)。本地原始数据：research/runs/spectre_cmos_v14_full/rt4cbedge118ssd01/rt4_callback_edge118_tt。独立审计：research/callback_edge118_terminal119_a.json与_b.json，所有哈希保存在结果中。冻结PWL逐点核验通过，插值门沿误差按10ps保存分辨率检查，真实窗口长度仍严格按原PWL核对。

## 唯一下一项：同条件复测起始点

`rt4cbstart119ssd01 / rt4_callback_start119_tt`仅将118的DAC49改为冻结复测起始中点32，也就是VD0、VD4两个输入从1.2V改为0；粗码6、偏置初值、负载、门控、记录长度、求解设置完全相同。只补这一个有明确对照关系的点，不扫描其他码、不插值指定锁定码。

目的：确认实际SAR选中粗码6在相同局部初值下，真实DAC32/49的计数是否位于5248两侧。117的粗6/DAC32属于完整启动历史，且只有内部周期观察器的瞬时值；不能与118拼成同条件计数曲线。119补充的配对也仍是两次独立初始化，不是连续二分、渐近稳态、117状态续跑或完整PLL捕获。

仅一个7µs、2请求线程TT27°C/1.2V/24MHz/10fF、Spectre X AX8ps/reltol1e-3/traponly/noise-off，10ps保存，预期700001点0–7µs。所有计算在项目SSD。没有修改完整硬件、八次复测预算或120µs长记录，也没有开始版图。

- [119协议](results/rt4_callback_start119_protocol.json)，输入manifest research/rt4_callback_start_implementation119.json；唯一流水线research/rt4_callback_start119_pipeline.json。
- 审计research/audit_rt4_callback_start119.py UNIQUE.json；有界入口poll_rt4_callback_start119.py。runner存活由其回收，消失只接续原SSD目录，禁止重新启动launcher、runner或仿真。
- 完成需两次独立相隔60秒稳定终态、退出0/零错误、input/raw/log/final.ic哈希、PSF END及700001点完整有限物理波形，再运行`review_rt4_callback_start119.py 审计A 审计B 新输出JSON`。
- 分析真实快照与门控/原始/缓冲边沿、实际ctrl/preset、nfilt漂移、RF÷4及两点是否包围目标。分析器验证配对输入仅两处DAC位不同，不预设包围结论。

119完成后结合117自主粗SAR及这组真实计数判断完整控制器捕获的必要性，不机械追加固定码点。固定码只是诊断激励，不能冒充自动修复成功。

## 持续边界

117只证明20µs自主粗SAR前段，未进入新计数复测、粗码余量修正或HANDOFF；原109旧几何完整K41锁定通过独立保留，新增粗码修正分支未触发。115/116粗8暖偏置两点也独立保留。118/119与它们不能拼接全频或继承锁定/噪声。

callback110默认CDF几何不是版图/PEX，WPE保持默认off，尺寸修改须重新callback。最终10kHz至fOUT/2排除杂散RMS<200fs保持，115.2fs仅为原RT4高偏移阶段依据。功耗和后端后置，所有旧任务已完成或退役。
