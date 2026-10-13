# RT4交接前复测候选
更新：2026-10-13T16:33:28+08:00

目的：修正984MHz捕获中，细调搜索选择的早期最佳DAC码在交接时已偏离目标的问题。此候选尚未采用，完整PLL结果待仿真完成。

保留4.8fF模拟电路与粗/细SAR搜索。选中DAC后增加32参考周期等待，重新计数RF/4的128参考周期。每次仅根据新计数将DAC增减1，限制在11–53；连续两次误差不超过1个计数（0.75MHz RF）才执行原交接。最多复测8次，达到边界或预算耗尽则报range_error并禁止enable；不强制粗码或预设成功DAC。

新RTL映射为1408个逻辑单元，再映射为既有实际MOS单元。11项映射后门级定向测试通过，包含K14/K41理想连续相位计数、SAR后频率移动、一次通过后再次偏移、预算耗尽、边界时刻第二次通过及复位清除。这些是逻辑检查，不能替代MOS时序或实际VCO捕获。新整环日志清点19,851 MOS；原已采用基线17,617 MOS未改。

仅派发`rt4recheckk41ssd01 / rt4r48_recheck_k41_tt`：TT27/1.2V/24MHz/K41/M4/10fF，Spectre X AX，8ps/reltol1e-3、traponly、noise-off。独立冷复位，120µs覆盖原搜索、最多约54.7µs新增复测及至少10µs交接后观察。延长记录是为容纳新增控制流程，未提高精度或增加频点。只用4个请求线程，所有计算位于项目SSD。

运行者：`research/run_rt4_recheck101.py`；唯一状态：`research/rt4_recheck_pipeline.json`。不重启、不自动重试。实际进程、cwd/TMPDIR、输入哈希已核验，仍在初始捕获，qualified低正常。完成后运行`research/audit_rt4_recheck101.py 新证据名.json`并用`review_rt4_recheck.py 新输出路径.json`核对原始终态、波形及锁定。

证据：[协议](results/rt4_recheck_protocol.json)、[映射逻辑检查](results/rt4_recheck_logic101.json)、[问题来源](results/rt4_range48_k41_search_review101.json)。原4.4fF、仅改4.8fF、新控制器三个版本分开；任何已知通过或115.2fs阶段值均不直接继承。先处理这一项，不扩展频点、角落、方法或种子矩阵。
