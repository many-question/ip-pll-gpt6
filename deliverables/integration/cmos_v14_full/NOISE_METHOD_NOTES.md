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


## 相同网表不保证相同的有效求解设置（2026-10-04，第49次）

对同一DAC放电核心、同一612项文本初值，AX与APS的tstab日志参数完全相同；进入PSS后，AX实际采用 `steadyratio=0.001, errpreset=moderate, relref=sigglobal`，APS采用 `0.01, conservative, alllocal`。两者显式1ps、Gear2和reltol/vabstol/iabstol相同，但有效PSS默认值不同。首个归一化范数3.69M→369k不能解释为物理误差改善：对应VDD支路误差分别约5.68063/5.6811mA。

因此该试验保留为求解器及实际默认值的联合诊断。必须检查接受的周期波形、实际频率/边沿和噪声，不能按迭代范数的数值大小选择电路。证据：[有效设置快照](results/core_mode_settings_validation.json)、[只读回收入口](record_core_mode_settings.py)。源日志为运行中的部分日志，未宣称PSS或噪声完成。原APS协议中前驱结果路径与hash配对的文字错误也在补充记录中明确更正，冻结协议保留。

## 2026-10-04：直接瞬态噪声与状态接续的控制试验

整环周期解尚未通过，新增一条直接瞬态器件噪声路径的前置控制。它没有把失败的 PSS 当作噪声工作点，也没有把原生 tran 状态送入 PSS。入口是 [RC 协议](results/transient_noise_recovery_protocol.json)：先保存无噪声 RC 的原生瞬态状态，分别恢复为无噪声、两个随机种子的噪声，以及加倍源带宽；另跑直接开启噪声的对照。比较均值、热噪声方差和恢复时间。解析方差为

`2 k T / (pi C) * atan(2 pi noisefmax R C)`，是单边热噪声 PSD 经实际 RC 滤波后的积分。

预设方差允许误差为10%，包含有限长度统计波动；此门限用于短方法控制，不是 PLL 抖动的数值精度门限。即使 RC 通过，仍需实际 MOS、PLL 的源带宽、时间步长、记录长度、噪声种子及确定性杂散处理验证。

本机 Spectre 21.1 的 `research/spectre_help/tran.txt` 明确说明 `noisefmax` 开启器件噪声并限制时间步长，`noisefmin` 以下为平坦谱。后者不是测量端的高通截止，不能用它代替10kHz抖动积分下限。当前版本帮助显示默认 `noisefmin=1 Hz`；[Cadence 对默认值的版本说明](https://community.cadence.com/cadence_technology_forums/f/custom-ic-design/63367/transient-simulation-with-noisefmin-blank/)与之相符，不能照搬早期版本“不指定便只有白噪声”的说法。

[Cadence 对瞬态噪声记录长度的说明](https://community.cadence.com/cadence_technology_forums/f/custom-ic-design/41377/transient-noise-analyses-in-cadence/1359627)指出低频成分必须在足够长的记录中观察。项目推算：10kHz一个周期就是100µs；只有一个周期仍不足以给出稳定的统计精度。数微秒试验可先检查高频噪声、数值底噪与方法是否工作，不能据此签核10kHz–fOUT/2的完整指标。

访问日期：2026-10-04。[Cadence 关于 tran/PSS 初态的说明](https://community.cadence.com/cadence_technology_forums/f/rf-design/28744/transient-results-as-starting-point-in-pss)也重新核对过；没有证据表明 `useprevic` 能绕过跨分析原生状态不兼容或本项目MOS `readpss` 噪声差异，因此未增加未经验证的全环PSS重试。

控制实验已经完成：[恢复验证](results/transient_noise_recovery_validation.json)。同种子10GHz恢复与直接仿真的方差差为−0.0901%，但相对上述理想矩形带限解析积分，两个10GHz恢复结果低6.76%和5.65%，20GHz结果低3.64%。10%方法门限通过，只说明恢复开启噪声有效，不能宣称达到1%噪声精度。为分开有限记录、积分步长和源带宽影响，新增[48µs五例精度协议](results/transient_noise_precision_protocol.json)：10GHz的10ps/1ps对照、固定1ps的40/80GHz，以及80GHz第二种子；结果以实际完成的验证文件为准。

上述解析式假定**矩形带限白噪声源**，不能预先把 `noisefmax` 等同于精确矩形滤波器。Cadence 的[2006年瞬态噪声应用说明](https://www.eecis.udel.edu/~vsaxena/courses/ece614/Handouts/Transient%20Noise%20Simulation.pdf)第4–5页给出了分段随机源及其 sinc² 频谱。这是一手历史算法说明，提示源频谱形状也可能产生偏差；它不能证明本项目21.1版本的具体实现，更不能直接校正实测噪声。当前以提高源带宽和减小步长的实际收敛对照判断，不缩放结果来满足解析值。访问日期：2026-10-04。

五例48µs精度控制现已全部完成：[实测结果](results/transient_noise_precision_validation.json)。10GHz下把步长从10ps减至1ps，方差只变化−0.000786%；固定1ps把源带宽从40GHz增加到80GHz，方差变化−0.016610%。80GHz两个种子相对矩形带限解析方差分别低2.8202%和2.7097%，分块标准误差分别为解析方差的0.5294%和0.5440%。预设3%方差门限通过，但剩余偏差仍需保留，不能称为1%精度收敛，也不能通过幅度缩放消除。原10GHz/1ps客户端300s超时和远端311s零错误完成的证据均保留；只是补收原运行，没有重跑。

下一项控制使用实际RT4晶体管电路：[协议](results/retimer_transient_noise_protocol.json)。物理电路、理想时钟/数据和10fF负载与已验证的TT sampled-PNoise一致。先保存100ns无噪声原生瞬态状态，再运行0.5ps/0.25ps无噪声对照；只有两个数值底噪均低于5fs才开启器件噪声。噪声分支比较80/160GHz源带宽、0.5/0.25ps步长和两个种子。测量取200ns之后2048个相邻输出上升沿，与细步长无噪声边沿逐一配对；以边沿序号均匀采样做单边频谱积分。实际FFT格点单元覆盖5.044921875–492MHz，PNoise也积分到同一频带。该短记录不能覆盖10kHz，也不能代替完整PLL。

边沿频谱算法已通过[独立解析校验](results/retimer_transient_noise_spectral_selfcheck.json)：已知正弦和Nyquist分量的总方差误差约7e−15；2048组白噪声样本的平均方差误差−0.0462%，落在统计误差内。该结果验证单边谱归一化和Nyquist计数，不是器件噪声测试结果。实际RT4结果只以已完成的运行及独立验证文件为准。

## RT4首次开启噪声后的数值恢复事件

80GHz源带宽、0.5ps步长、种子11的首例实际MOS噪声已完成。5.044921875–492MHz的诊断RMS为48.9816fs，比同带PNoise的53.3243fs低8.1438%；这个数值虽然落在原10%幅度比较门限内，**仍未通过**，因为日志记录了Newton灾难恢复和跳过时间断点。零终态错误数不能抵消这些数值异常。分析器现将它们作为独立验收失败条件，保留原始数据及计算值，不将该结果用于指标达标声明。见[冻结的首例结果](results/retimer_transient_noise_first_on_validation.json)。

[时间定位](results/retimer_transient_noise_recovery_diagnosis.json)发现，打印的五个跳过断点均与6.25ps候选噪声更新网格在日志舍入精度内重合，其中四个距理想时钟转折点约38–56ps。这支持先检查噪声生成与求解器交互的假设，不能证明内部实现或排除其它根因。打印次数受到日志抑制限制，不是实际事件总数。既有160GHz及0.25ps对照继续检查此问题，不再只按RMS是否接近判定。

本机21.1帮助列出 `trannoisemethod=default/adaptive`。[Cadence关于该选项的说明](https://community.cadence.com/cadence_technology_forums/f/custom-ic-design/55346/spectre-what-is-the-purpose-of-the-trannoisemethod-parameter)针对相近21.1版本指出当时尚未完整公开其细节。因此该选项至多是后续单独数值试验的候选，不能预先声称能修复本例，也不能绕过物理电路相同、数值底噪和噪声幅度交叉核对。访问日期：2026-10-04。

## 2026-10-05：原生恢复、动态参数与实际初态核验

后续实测否定了“动态放宽电压容差修好恢复噪声”的解释。三个动态参数试验虽在日志中显示从100ns接续，输出起点却由原生种子的1.226281V变为0V，且波形cache完全相同。它们是**无效的状态接续**，不能作为容差修复或噪声验收证据。普通原生开启噪声、adaptive、Gear2、静态100nV、微小噪声预初始化及显式start均未消除此处的恢复异常。详见[逐例恢复审计](results/retimer_restart_diagnosis_validation.json)。

整环还测到：改变save集合可能改变电路展开并使原生恢复被拒绝；保持原save集合但增加动态参数仍可能清零状态。保留原观察集合且不增加动态参数后，1ps／0.5ps整环接续的53个物理节点起点与64µs冷启动终态完全相等。运行器现在同时核对恢复错误码、日志和数据起始时间、可用的物理起点及**实际生效**的容差；网表中请求的参数不等于恢复后实际采用的参数。

[Cadence关于延迟启用瞬态噪声的说明](https://community.cadence.com/cadence_technology_forums/f/custom-ic-design/49435/transient-simulation---adding-noise-after-steady-state/1379137)支持在同一次新分析中先`isnoisy=0`，稳定后再切换到1；它没有证明在旧原生恢复上新加动态参数也安全。因此新RT4对照从t=0开始，100ns启用噪声，按实际完成的[延迟噪声验证](results/retimer_delayed_noise_validation.json)评估，不再沿用失败的原生noise-on路径。查阅日期2026-10-05。

## 2026-10-05：完整PLL稳定工作点与容差问题

RT4／新分频候选的64µs独立复位已经完成，通过限定TT27/1.2V/K41/M4/10fF/Q5/4ps条件的功能检查；这不是抖动验收。随后1ps／0.5ps、reltol1e-5的250ns无噪声接续均无数值恢复，但工作点仍调整；128沿、19.21875–492MHz的配对边沿差为469.879fs。该量是确定性步长敏感性，不是器件随机抖动。见[整环前置检查](results/full_pll_jitter_preflight2_validation.json)。

用冷启动实测writefinal作新分析的readic，53个物理节点起点最大误差约4e-15V；相同时间窗口的控制电压与有效原生接续相比RMS差约30µV，FLL码值和qualification保留。该[初始化检查](results/full_pll_warm_noise_method_validation.json)允许进一步稳定，仍不把文本IC称为完整历史或新的冷启动证明。

全环reltol1e-6、1nV/1fA的Trap在noise-off时出现恢复异常，Gear2也失败。详细日志多数失败更新指向power_mw观察输出，但去掉两个非功能VA观测器后异常仍在，**未证明观测器是根因**。无VA的5ns单变量对照中，仅把iabstol改为1pA便无恢复；仅把vabstol改为1µV仍失败。见[求解器审计](results/full_pll_solver_audit_validation.json)。新的[完整电路配对协议](results/full_pll_direct_noise_pair_protocol.json)采用1nV/reltol1e-6/1pA，完整FLL、逻辑、偏置和电阻热噪声均保留，只有测量VA被移除，外部串联测量支路改为等效零伏源。

短MOS噪声控制通过后，新完整电路quiet/noise配对可在资源上限内并行；只有两条实际轨迹完成，并通过quiet工作点、共同前段和噪声日志检查后才接受诊断值。2.2µs记录只作5.28515625–492MHz诊断。**10kHz–492MHz的完整RMS仍须更长记录或另一条经过独立校验的方法**；不得把高偏移段、三个噪声点或不同模块的积分数值拼成已完成的整机验收。改变iabstol后的噪声幅度精度、步长和记录长度收敛仍是待完成项。

RT4的六个延迟噪声控制已完成且通过预定门限：80GHz/.5ps为48.6829fs，160GHz/.5ps为52.6064fs，160GHz/.25ps两个种子为52.5946fs和51.3670fs；同频带PNoise为53.3087fs。全部日志无数值恢复。源带宽加倍仍改变RMS约8.06%，半步长变化−0.0225%，第二种子变化−2.334%；通过的是原定10%短方法门限，不能声称1%完整噪声精度。

较宽松设置的完整暖启动在约0.4µs后丢失qualification和acquired、重新进入FLL捕获，已停止并保留原始轨迹；无数值恢复并不等于稳态有效。该观察同时说明不能只检查文本IC起点或300ns短窗。无VA、严格电压精度的新配对仍需独立完成整个窗口验证，不能由旧冷启动或RT4局部结果担保。
