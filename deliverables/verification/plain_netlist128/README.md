# RT4 / callback110 纯 Spectre 网表库

交付目录：[rt4_callback110_plain](../../netlists/rt4_callback110_plain/)。目录仅包含 83 个 `.scs` 网表文件，没有 RNL、图形符号、定位或走线标注。

- [library.scs](../../netlists/rt4_callback110_plain/library.scs)：库入口，只包含全部 81 个子电路的相对路径引用，不实例化电路。用于接入自己的 testbench。
- [top.scs](../../netlists/rt4_callback110_plain/top.scs)：顶层入口，加载同一组子电路并保留原 `XPLL` 实例及端口连接。
- [顶层子电路定义](../../netlists/rt4_callback110_plain/cells/00_pll_capture_rt4_r48_recenter109_v14.scs)：`pll_capture_rt4_r48_recenter109_v14_pdk110_0`。

两个入口各自加载全库，使用时选择一个入口即可。保持 `cells/` 与入口文件的相对位置。顶层端口顺序为：

```text
ref reset apply k0 k1 k2 k3 k4 k5 out qualified range_error
cfg_ready frequency_good phase_good amp_good vdd vss
```

本版从当前 RNL 交付逐文件去除整行注释和空行；原有 82 个文件的电气语句、参数、节点连接和层次逐行保持。额外的 `library.scs` 仅提供 include-only 入口。原 RNL 目录的文件哈希全部保持不变。

[静态审计](audit.json)核对了 81 个子电路与冻结源 `rt4_callback110_after.scs` 的一致性、全部相对路径、子电路可达性和实例端口数量；共 2932 个定义内实例、15140 个端子，递归展开 21479 个 MOS。83 个交付文件中 RNL 残留为零。

本库不分发 PDK 模型卡；仿真时仍需既有 `nch`、`pch`、`nmoscap` 模型与 testbench 激励/分析设置。本次只做本地文件导出和静态核对，未运行新仿真或访问远程结果。仿真研究和定时任务保持暂停。
