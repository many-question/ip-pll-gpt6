// Same qualification/loss rules as V14, with a bounded initial capture interval.
// The 512-reference timeout (21.333us at24MHz) is an internal working choice.
module pll_supervisor_capture_v14(input refclk,reset,cfg_ready,fll_enable,range_error,
 input phase_good,frequency_good,
 output pll_enable,output reg qualified,output reg restart,output reg fault);
 reg [5:0] good_count;
 reg [2:0] bad_count;
 reg [3:0] restart_count;
 reg [8:0] capture_count;
 wire good=phase_good && frequency_good;
 assign pll_enable=cfg_ready && fll_enable && !range_error && !restart && !reset;
 always @(posedge refclk or posedge reset) begin
  if(reset) begin
   qualified<=0;restart<=0;fault<=0;good_count<=0;bad_count<=0;
   restart_count<=0;capture_count<=0;
  end else if(!cfg_ready) begin
   qualified<=0;restart<=0;fault<=0;good_count<=0;bad_count<=0;
   restart_count<=0;capture_count<=0;
  end else if(range_error) begin
   qualified<=0;fault<=1;good_count<=0;bad_count<=0;capture_count<=0;
  end else if(restart) begin
   capture_count<=0;
   if(restart_count==7) begin restart<=0;restart_count<=0;end
   else restart_count<=restart_count+1'b1;
  end else if(!fll_enable) begin
   qualified<=0;good_count<=0;bad_count<=0;capture_count<=0;
  end else begin
   if(qualified) capture_count<=0;
   else capture_count<=capture_count+1'b1;
   if(good) begin
    bad_count<=0;
    if(!qualified) begin
     if(good_count==31) begin qualified<=1;good_count<=0;capture_count<=0;end
     else good_count<=good_count+1'b1;
    end
   end else begin
    good_count<=0;
    if(qualified) begin
     if(bad_count==3) begin qualified<=0;restart<=1;restart_count<=0;bad_count<=0;end
     else bad_count<=bad_count+1'b1;
    end
   end
   // A successful 32nd good sample on the deadline takes priority over timeout.
   if(!qualified && capture_count==511 && !(good && good_count==31)) begin
    restart<=1;qualified<=0;restart_count<=0;capture_count<=0;
    good_count<=0;bad_count<=0;
   end
  end
 end
endmodule
