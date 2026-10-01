"""Analytical diagnostic only: trapezoidal frequency error of an ideal LC tank.

For x'=j*w*x and fixed step h, trapezoidal update has eigenvalue
(1+j*w*h/2)/(1-j*w*h/2). Thus its phase frequency is2*atan(w*h/2)/h.
The nonlinear PDK oscillator and Spectre's adaptive grid are not this model.
"""
import json,math
from analyze import H
f=3.936e9;w=2*math.pi*f
rows=[]
for h in [2e-12,1e-12,.5e-12]:
 fd=math.atan(w*h/2)/(math.pi*h)
 rows.append(dict(step_s=h,numerical_frequency_hz=fd,error_hz=fd-f,relative_error=fd/f-1))
out=dict(scope='Analytical ideal lossless LC with constant-step trapezoidal integration. Diagnostic scale estimate only; not a simulation or error bound for nonlinear Q5 PDK VCO, adaptive Spectre steps, or PLL.',physical_frequency_hz=f,formula='f_num=atan(pi*f*h)/(pi*h)',rows=rows,change_2ps_to_1ps_hz=rows[1]['numerical_frequency_hz']-rows[0]['numerical_frequency_hz'],inference='Feedback can compensate an integration-induced oscillator frequency shift by changing control voltage. This is one possible contributor to step-dependent PLL control, not a demonstrated cause or a Kvco extraction.')
(H/'results/integration_frequency_estimate.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
