# 当前 RT4 电路的 RNL 交付检查

入口：[`../../rnl/rt4_callback110/top.scs`](../../rnl/rt4_callback110/top.scs)。该目录只有 82 份 `.scs` 网表；`cells/` 保存原有 81 个子电路，没有脚本、图像、模型卡或运行库。

在支持 RNL 0.3 的 desktop viewer 中打开 `top.scs`，双击 `XPLL` 进入系统，再双击模块进入下一级。网页版需要载入整个目录，以便解析相对 include。原始设计顶层为 `pll_capture_rt4_r48_recenter109_v14_pdk110_0`。`XPLL` 只是 viewer 入口实例，没有增加激励或更改原有子电路。

原始输入是 `share/deliverables/blocks/cmos_v14_full/rt4_callback110_after.scs`，SHA256 为 `260a50e7e62d0d25cfdfb21d6004a22f31ca38544632329448bea811dcd38f62`。每个子电路的电气语句、器件名、端口顺序、网络、参数及层次均逐条保持一致。所有修改是绘图注释与文件拆分。原冻结文件未修改。

每个器件都有完整 `PLACE(x,y)` 和 `ORIENT`，每个端子都有 `WIRE(mode="straight")` 的明确路径。没有 `ROUTE`、solver 调用或 `type="generated"` 记录。模拟主链、LC 核心、TSPC、关键逻辑与 DAC 梯形网络使用连续导线。大型综合逻辑保持原层次和原实例顺序，每 24 个门划成一个编号分区；跨区域连接通过同名网络标签表达，点击网络可追踪同一层次的关联对象。标签不创建新电气连接，原网表决定连接关系。

`nch`、`pch`、`nmoscap` 用明确符号绘制，不分发 PDK 模型卡。晶体管图上标出 W/L，完整 callback 参数仍保留在网表原语句中。本目录可独立渲染；进行仿真仍需原工程的模型配置。

检查使用官方 `@rich-netlist/runtime` **0.1.0-preview.14**，标准包和语言为 **RNL 0.3**。核验结果见 [`audit.json`](audit.json)：

- 82 个可达、非空绘图层次；无缺失 include 或电路子层次。
- 81 个原子电路、2932 个定义内实例；展开 21479 个 MOS。
- 15140 个定义内端子全部有显式走线，所有实例均已定位。
- 0 错误、0 警告、0 提示、0 未定位对象。
- 原电气语句逐条一致，包含每份交付文件的 SHA256。
- 已检查入口、系统主链、LC 核心、反相器、TSPC、DAC、控制器及 FLL 分区的实际渲染。

本地复现脚本：`research/build_rnl126.py`、`research/verify_rnl126.py`；运行库检查器及渲染中间产物在 `research/rnl126_work/`。这些都位于纯网表交付目录以外。

本次仅交付电路绘图。仿真研究与定时任务保持用户暂停状态；没有运行远端审计、poll、结果回收、评审或新仿真。125 的当前计算状态未重新检查；本次不增加任何捕获、噪声、功耗或 PVT 结论。
