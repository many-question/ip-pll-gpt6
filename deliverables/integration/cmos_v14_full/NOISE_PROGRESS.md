# V14 闭环抖动验证进展

验收口径保持 **RMS <200fs，10kHz–输出频率一半，排除离散杂散**。K41/M4时上限492MHz。本页没有新增整机RMS通过结论。

## 已启动的器件噪声测试

`pll_noise_core_v14`从当前`pll_capture_v14`生成，采用TT27、1.2V、理想24MHz参考、粗调23/DAC38、984MHz/10fF、Q5 πRLC。保留真实VCO及偏置、亚采样反馈、CP及MOS脉冲电路、环路RC和预置开关、RF接收、完整可编程分频树、重定时/输出、有效性检测，以及关闭状态的实际DAC和静默计数器输入负载。

为先测量噪声关键闭环，FLL、配置、监督和看门狗被诊断边界上的固定控制电平替代。这不是新的全晶体管PLL交付版本，也不是全PLL签核：未覆盖慢速逻辑噪声/活动、它们对参考缓冲的加载、实际控制码输出阻抗/噪声、外部参考/电源噪声及PEX。后续必须比较核心与完整DUT的工作点/边沿，并验证这些缺项，不能仅将局部链141fs或本核心结果写为整机指标。

正常完整DUT的共同周期至少32µs；固定慢控制后，仍翻转的÷8/÷12支路与24MHz参考共同周期为250ns。因此本核心使用4MHz PSS，不强行按24MHz周期求解。PSF应检查246个输出上升沿、正确谐波和周期端点；每个上升沿的噪声未必相同。

## 流程与当前边界

1. `corenoiseprobe01/core_noise_probe_tt`的1.251µs稳定段已回收，1ps/reltol1e-5。参考采样相位展开跨度18.345rad，平均漂移15.289rad/µs；末200ns RF3937.755MHz、输出984.432MHz，仍连续滑相。首轮PSS迭代不收敛，已主动SIGINT停止并保留原始输入/PSF及取消原因。**尚未进入可用PNoise测量，没有RMS结果。**
2. 对照`corepreflight4ps01`改为4ps/reltol1e-4，绝对容差仍保持1e-7V/1e-13A；1µs瞬态完成0error，但相位跨度3.014rad、漂移1.648rad/µs，亦未达到稳态。这不是完整DUT的4ps捕获失败，也不是随机抖动。
3. 裁剪核心的参考边沿约59.6/52.8ps，完整DUT保持轨迹约200/182ps，参考负载显著不同。`coreload01`额外2/5/10pF的三组300ns诊断对照均已完成0error，分别得到196/174、414/360、784/678ps；2pF接近完整DUT，但三组均未达到稳定相位。理想等效电容不能代替最终逻辑噪声/周期活动验证。
4. `analyze_core_preflight.py`先检查实际工作点与相位稳定性；`analyze_closedloop_noise.py`再检查PSS最终0error、周期谐波/端点、输出边沿、噪声贡献求和和单位。原一次性继续脚本已记录`probe_failed_no_band_launched`，没有启动完整频带任务。
5. 待工作点、周期轨迹验证通过后，先做六频点归因探测，再做10kHz–492MHz、20点/dec全频带PSD/slew²积分。六点本身不积分；自动Jee可能截断到PSS基频一半，不能作为项目全频带RMS。完整积分后仍需边沿位置、谐波邻近有限频率、步长/边带收敛及各模块单独noise-on对照。

当前另一个工作点差异是粗调码的驱动边界：完整DUT通过八个`tx_dff_r0`输出驱动MOS电容开关，固定理想电压会移除输出阻抗及RF回灌。新`pll_noise_register_core_v14`保留相同八个MOS DFF、实际refb时钟和D=q保持反馈，以实际64µs终态初始化每级9个内部节点。用1.9pF诊断补载补偿其余参考负载，`coreregister01`正在跑2µs/1ps严格瞬态。它仍省略其它慢控制和部分负载，不是完整PLL；先验稳态和实际DUT一致性，再进入PSS。

周期解复用流程已准备：读取旧PSS状态使用`checkpss=yes`，本地/远程SHA匹配；不跳过周期解有效性检查。已完成两次相同RC校准（新求解与复用状态），PSD最大相对差约8.9e-14，见`results/pss_reuse_validation.json`。这是测量流程校验，不是PLL性能。

## 复现入口

- 构建：`build_closedloop_noise.py`；边界：`results/closedloop_noise_protocol.json`。
- 分析：`analyze_closedloop_noise.py corenoiseprobe01 corenoiseband01`，只读取已完成结果。
- 运行器新增`--pss-state <项目research内已回收状态文件>`；状态跨电路变更禁止复用，继续脚本会检查全部依赖。
- 原始输入/PSF/状态/日志位于项目`research/runs/spectre_cmos_v14_full/corenoiseprobe01/`；后续完整频带使用独立`corenoiseband01`目录。
- `results/chain_noise_validation.json`、`chain_alias_validation.json`与`vco_noise_validation.json`保留此前各自边界的局部噪声证据。

诊断证据：`results/core_preflight_validation.json`；原始稳定段953,481,254字节，SHA256 `c9436fa4e0eccc1a41a8395785a6babd0c41c54ec98c54088c03a49d541a3852`，本地与远程一致。4ps对照原始波形SHA256 `fdb5e67388361dc99c16e97f9a882b27c60898b57d7703c0a8d08cbf2e61eb2f`亦已核对。
