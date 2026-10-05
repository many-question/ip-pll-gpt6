# 第65次噪声与抖动审阅

2026-10-05T13:04:32+08:00。修正短噪声试验的有效频带判读，并确认客户端超时后服务器仍运行；完整PLL抖动尚无新验收结果。

200ns全PLL短噪声试验的真实Spectre日志显示，请求noisefmin=1MHz被按1/stop提高为5MHz，noisefmax仍为160GHz。本机Spectre帮助说明noisefmin以下的源PSD被保持为常数，并非把低频噪声删除；因此不能把请求值或短记录当成低偏移噪声覆盖。原协议和所有仿真输入未改；日志字节、26项输入哈希及原客户端失败manifest已记录。

分析脚本现在分别输出严格协议匹配与activation_method_passed。严格passed仍会因1MHz/5MHz不符而失败；只有日志明确解释的实际频带，加上完成、初始化、逻辑保持和数值检查全部通过，才可判噪声开启方法通过。覆盖真实日志、缺失解释、错误频带及匹配配置的7项检查通过；这是分析代码验证，不是新电路性能结果。

短试验客户端12:53:33等待超时，但远端PID415788仍在推进且未出现Spectre终止摘要。保留原result.json，现有保护脚本将等待真实终止后补充回收completed_result.json。三项仿真及三项本地监控/流水线均仍在运行；未重启或重复派发。

完整PLL的10kHz–fOUT/2、排除离散杂散的RMS<200fs仍未知；短激活方法、高偏移片段和局部RT4结果均不能替代验收。原版与RT4候选保持分开，功耗和后端优化仍后置。

当前缓冲进度（不代表最终完成）：

```json
{
  "time": "2026-10-05T13:04:32+08:00",
  "jobs": [
    {
      "run": "pllmainstrictoff01",
      "case": "full_pll_main_strict_off_tt",
      "state": "running_or_collecting",
      "last": {
        "time": 1.321190909574296e-06,
        "frequency_good": 1.199985229175496,
        "XP.XC.phase_held": 1.200000102123788,
        "XP.restart": -2.733877516111252e-06,
        "XP.ctrl": 0.6412845225392515,
        "qualified": 1.199996417645061,
        "XP.XC.acquired": 1.207783438949999
      },
      "newton": 0,
      "skipped": 0,
      "lte": 0,
      "completed_clean": false,
      "bytes": 659472384
    },
    {
      "run": "pllmainstricton01",
      "case": "full_pll_main_strict_on_tt",
      "state": "not_dispatched"
    },
    {
      "run": "pllprecisionramp01",
      "case": "full_pll_rt4_precision_ramp_tt",
      "state": "running_or_collecting",
      "last": {
        "time": 8.072000000000256e-06,
        "frequency_good": 1.200004757735388,
        "XP.XC.phase_held": 1.200000217510937,
        "XP.restart": -5.828911632801789e-07,
        "XP.ctrl": 0.7504544274314908,
        "qualified": 1.199999047929624,
        "XP.XC.acquired": 1.193381870247064
      },
      "newton": 0,
      "skipped": 0,
      "lte": 0,
      "completed_clean": false,
      "bytes": 3194880
    },
    {
      "run": "pllnoiseactivation01",
      "case": "full_pll_noise_activation_probe_tt",
      "state": "running_or_collecting",
      "last": {
        "frequency_good": 1.199605736346466,
        "XP.XC.acquired": 1.191689255876055,
        "XP.ctrl": 0.6357832490919547,
        "qualified": 1.199819312194153,
        "XP.XC.phase_held": 1.199857636908891,
        "XP.restart": -0.0002836563880084391,
        "time": 1.011658817353263e-07
      },
      "newton": 0,
      "skipped": 0,
      "lte": 0,
      "completed_clean": false,
      "bytes": 260268032
    }
  ]
}
```

原始日志见项目 `research/diagnostics/full_pll_activation_band01/spectre_at_snapshot.out`，SHA256 `1670e5647e31de494945e000a722c97e730374db74bd07036d5e9376657b9aaf`。[证据清单](results/full_pll_noise_activation_band_observation.json)；[代码回归检查](results/noise_activation_band_regression.json)；[全部12项需求、14模块和六层状态](../../../reports/2026-10-05T1304.yaml)。
