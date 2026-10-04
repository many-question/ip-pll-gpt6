# 噪声方法核查（2026-10-04）

本页记录实际参考的方法来源，不作为本电路性能证据。

- 本机已回收的 Spectre 21.1 帮助：项目 `research/spectre_help/pss.txt`、`pnoise.txt`、`jitterevent.txt`。PSS 的稳定段、周期求解和 PNoise 是不同阶段；失败运行生成的状态文件不能仅凭文件存在而复用。当前流程要求完成日志、周期轨迹和源文件 SHA 同时通过。
- [Cadence：PLL + PSS + PNOISE convergence](https://community.cadence.com/cadence_technology_forums/f/custom-ic-design/48474/pll-pss-pnoise-convergence)。驱动 PLL 应使用受迫周期解；全部内部信号须与共同周期相容。原生检查点不能在 tran 与 PSS 两种分析之间混用。本项目使用的文本终态只是初值种子，重启扰动必须重新稳定。
- [Cadence：Measuring Noise in Digital Circuits](https://community.cadence.com/cadence_blogs_8/b/cic/posts/spectre-tech-tips-measuring-noise-in-digital-circuits)。数字边沿使用 sampled edge crossing；fullspectrum 仍需核查 PSS 的频率覆盖。本项目还会检查 maxacfreq、步长、边带及不同输出边沿，不能只改变 maxsideband 就宣称收敛。
- [Cadence：Pnoise on signal at multiple of the fundamental](https://community.cadence.com/cadence_technology_forums/f/custom-ic-design/56829/pnoise-on-signal-at-multiple-of-the-fundamental)。输出频率高于 PSS 基频时使用 sample ratio 的适用说明。内部帮助定义其为采样频率/PSS基频；本项目局部链使用6，4MHz锁定核心使用246。

工具实测校准仍见 `results/noise_measurement_fixture.json`、`results/pss_reuse_validation.json`。局部链在精确 PSS 谐波处存在 flicker 警告，邻近有限频率检查也未完全关闭；现有 logarithmic-grid 积分仅为暂定数值。用户排除的是离散杂散，这不授权删除谐波邻近的随机噪声。

当前的 Gear2、2µs稳定段属于数值收敛诊断；相位瞬态、Newton异常电压和无噪声仿真中的边沿变化都不能算作随机抖动。


## 2026-10-04：复用与初态恢复的实测限制

- 本地Spectre帮助说明`readpss`检查电路方程残差，`checkpss=yes`会在必要时重求；这并不替代噪声对照。当前MOS局部链复用前后波形近似相同，但1／10／100MHz全噪声PSD比达2.592／4.564／5.049。RC校准通过不能推及MOS；当前流程暂用新求解PSS作性能依据。详见`results/rt_noise_controls.json`，保留冲突结果，不归因于电路尺寸。
- [Cadence：Transient results as starting point in PSS](https://community.cadence.com/cadence_technology_forums/f/rf-design/28744/transient-results-as-starting-point-in-pss)建议文本writefinal／readic配合skipdc=yes，并允许未保存状态重新稳定。新核心测试采用此建议；不是已证明的修复。
- 本地`research/spectre_help/pss.txt`还建议避开强非线性跳变启动shooting。新核心使用与5µs终态匹配的`tstart=5u`，250ns稳定后在5.25µs启动求解；原默认从参考起跳相位开始。物理电路和容差未变。
- [Cadence：reuse PSS results to run standalone Pnoise](https://community.cadence.com/cadence_technology_forums/f/custom-ic-design/62486/reuse-pss-results-to-run-standalone-pnoise/)确认该功能的正常用途；它不是对本项目当前版本／模型／配置噪声一致性的担保。当前实测差异的底层原因尚未确定。

## 电流观测对初态节点集合的影响

实际A/B已确认：瞬态中未保存支路电流时被消除的零伏探针电源节点，在PSS保存电流后重新保留。原readic缺少三个电压条目，skipdc初始化为0V；只补三个1.2V条目即可去除209A数值尖峰。详见[初始化修复](CORE_INITIALIZATION.md)。该实验只证明初始化原因，修正后的PSS仍须独立收敛；不把尖峰当正常功耗。

## 2026-10-04：谐波邻域的积分解释

[Ken Kundert，2009-12-27，关于开关电容采样电路的 PNoise 答复](https://www.designers-guide.org/forum/YaBB.pl?num=1261493675/0)解释了闪烁噪声上变频形成窄峰、精确谐波处无穷项被忽略，以及稀疏扫频可能漏掉窄峰的问题，并建议在谐波两侧补扫。访问日期2026-10-04。该一手说明支持本项目补扫有限邻域和检查器件贡献的方法；它不证明本项目sample-ratio、多边沿相关性或积分已经正确，也没有给出可直接采用的物理低频截止。不得把未测的中心邻域当作零噪声或离散杂散删除。

## 2026-10-04：实际 MOS 单周期／六周期校准

同一个 984 MHz CMOS 缓冲器，以及同一个实际 RT4 TSPC 重定时器，分别使用 984 MHz／sample ratio 1 和 164 MHz／sample ratio 6 重新求解 PSS。两种设置保持相同物理电路、输入、负载、绝对频率覆盖和最大步长；没有复用 PSS 状态。十个偏移点包含 164 MHz、328 MHz 两侧相距 1 Hz 的点，以及 492 MHz 下方 1 Hz 的点。

缓冲器的最大时序 PSD 差为 0.000146 dB，重定时器为 0.000126 dB；各周期波形、输出沿、噪声器件总和及斜率检查通过。它们支持对重复相同边沿的 MOS 电路采用当前 sample-ratio 设置，不能推及实际分频链中随六个边沿位置变化的噪声传递，也不解决此前 readpss 复用冲突。

首次缓冲器测试使用普通 Spectre 模式，PSS 成功，但 fullspectrum PNoise 被 SPCRTRF-15412 拒绝。改用与实际数字链相同的 AX／APS 系列模式后，两项对照完成；失败输入和日志仍保留。

独立 RT4 的 95 点积分与半步长、更高频率覆盖对照另见 [完整频带结果](results/retimer_standalone_band_validation.json)。理想时钟／数据下约 53.9 fs 的结果仅属于此模块，不可取代含接收器、实际分频器和 LC 的整机结果。
