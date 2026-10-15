# 第110次：PDK callback 参数更新与小模块对比

PDK callback 几何更新对电路有实质影响：局部 VCO RF 变化 -2.702%，参考缓冲延时变化 +3.713%。六项短仿真正常完成。

## 更新范围与来源

本次按用户要求使用更新后的 [pdk-callback skill](C:/Users/jielu/.codex/skills/pdk-callback/SKILL.md)。`tsmc180bcd-gen2-2022`（PDK 1.6b、adapter 0.1.0）与当前 TSMC180BCD Gen2 的 `nch/pch` 对应，采用 `nmos2v/pmos2v` callback。1595 项已内置 Virtuoso 参考比对通过；它是skill的参考验证，不是本次在线调用 Virtuoso。

按当前109完整层次的 **75种实际 W/L/model** 分别数值求解，生成158条尺寸特化后的MOS定义，覆盖 **21,479个展开MOS实例**。原始依赖文件有94条MOS定义，包含共享和未使用子电路；二者不是同一种计数。callback前后实例数相同，W/L/NF/M、连接、控制逻辑和无源值相同。`nmoscap` 的 lr/wr/mr 保持原PDK原语。

已更新 AD/AS/PD/PS、NRD/NRS、SA/SB/SD，并显式记录 SCA/SCB/SCC=0。使用PDK默认单指、不共享扩散、calcDiff/calcParam开启。**WPE维持默认off**，未猜测真实阱边距离。宽管常见扩散尺寸由项目假设240nm变为callback计算的480nm；窄管另有规则，例如W=240nm/L=1µm：AD=AS=2.004e-13m²、PD=PS=1.88µm、SA=SB=.52µm、SD=.62µm，不能套统一宽管公式。

当前项目交付实现是文本电路网表，尚无已完成的OA原理图。本次更新的是可仿真的完整电路层次，**没有声称修改OA库，也没有生成版图或PEX**。默认CDF/PCell参数是前仿假设，实际布局后仍需提取。

更新版本：[完整callback网表](../../blocks/cmos_v14_full/rt4_callback110_after.scs)；[等条件更新前网表](../../blocks/cmos_v14_full/rt4_callback110_before.scs)。为正确处理窄管，按当前实际尺寸特化子电路；外部频率配置引脚仍保留，改W/L/NF/M或尺寸参数时必须重新运行callback生成版本，不能直接覆盖尺寸。

## 配对结果

六项均TT/27°C/1.2V、Spectre X AX、maxstep8ps/reltol1e-3、traponly、noise-off、2请求线程，三对顺序执行。相同激励、初始条件、测量窗口和负载，仅MOS几何参数不同。

| 量 | 更新前 | callback后 | 相对变化 |
|---|---:|---:|---:|
| 参考缓冲平均上升沿延时 | 319.317005 ps | 331.173721 ps | +3.713% |
| CP 脉冲有效跨导绝对值 | 4.417198 µS | 3.742814 µS | -15.267% |
| 外部RF驱动链输出 | 983.998666 MHz | 983.997742 MHz | -0.000% |
| 外部RF链总供电 | 3.805627 mW | 4.229106 mW | +11.128% |
| 局部VCO RF | 3930.439959 MHz | 3824.247638 MHz | -2.702% |
| 局部VCO ÷4输出 | 982.595520 MHz | 956.048699 MHz | -2.702% |
| VCO夹具总供电 | 7.869193 mW | 7.837254 mW | -0.406% |


- 参考缓冲/CP：300ns；参考24MHz、60fF。CP差分输入±10mV，2ns脉冲，输出钳位.6V。跨导为脉冲中段输出钳位电流差除以20mV，报告绝对值；它不是静态OP gm或完整PLL环路增益。输出电流符号遵循VOUT正端流入方向，原始有符号数据与逐脉冲观察均在JSON。
- RF链：120ns，外部3.936GHz正弦、真实接收器/÷4/RT4、10fF；测量40–120ns。更新前后均观察到正确÷4，最短高/低脉宽和电压范围已保留。
- VCO：400ns，固定粗码20、控制.48V、4.8fF单位电容、真实1MΩ/10pF偏置网络；nfilt初值.728V在t=0释放，带采样器、CP、RF/÷4/RT4及10fF负载。测量最后100ns，前后均÷4。偏置仍在漂移，**此结果为相同短夹具下的变化，不是渐近稳态或完整PLL锁定**。
- VCO nfilt最后100ns均值：0.729969760 → 0.730157163V；线性漂移-0.000086 → 0.000467V/µs。不能只据此把频率差归因于某一个LDE参数。

## 完整性与边界

六项明确退出0、零错误，PSF END与各60001/24001/80001点有限物理波形通过；units元数据NaN单独排除。输入/raw/日志/final.ic本地远程哈希一致，两次独立终态相隔253.021秒稳定。Spectre实际求解总耗时206.06秒（不含上传、下载和审计）。结构比较确认仅上述12个几何参数改变。

原109完整捕获仍是PID305678/原SSD目录，最新保存66.118/120µs，原输入哈希核验通过；244项原实现依赖保持不变。没有重启、停止或改动原仿真。小任务期间总请求6线程，结束后仅原4线程。

独立callback110更新版；旧采用4.4fF与当前4.8fF/recenter109输入均保持原样，不继承锁定、调谐范围或噪声结论。 最终10kHz至fOUT/2排除杂散RMS<200fs保持；115.2fs仅为原RT4高偏移阶段依据。本次无噪声仿真，频率变化不是抖动；功耗优化和后端仍后置。

## 证据与复现

- [参数来源与75种尺寸结果](results/pdk_callback110_parameters.json)、[结构比较及参考验证](results/pdk_callback110_structure.json)
- [配对协议](results/pdk_callback110_protocol.json)、[测量与前后差异](results/pdk_callback110_review.json)、[终态/哈希摘要](results/pdk_callback110_terminal.json)
- 生成脚本 `build_pdk_callback110.py` / `build_pdk_callback110_tests.py`，分析脚本 `review_pdk_callback110.py`。生成器读取原109冻结输入，拒绝覆盖已有交付网表。再次运行必须使用新版本/任务名，不能重跑已完成队列。
- 本地原始输入、raw、日志与final.ic：`research/runs/spectre_cmos_v14_full/pdkcb110ssd01/`；逐项完整哈希在结果JSON。PDK callback运行资源和完整CDF未进入share，仅保留项目实例参数、工艺身份及包哈希。

几何更新造成约2.7%的局部频率变化，后续整环必须明确选择参数版本再建立新基线。当前109先按原输入完成回收，不能将其结果当成callback版的结果。
