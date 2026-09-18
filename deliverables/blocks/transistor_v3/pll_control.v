// The request is synchronized. Keep cfg_k stable from request assertion to ready.
// Divider reset is asserted before active K changes and held for eight ref cycles.
module pll_config(input refclk, reset, apply, input [5:0] cfg_k,
 output reg [5:0] active_k, output [5:0] select_m,
 output reg ready, output reg invalid, output divider_reset);
 reg req1,req2,req_old;
 reg [3:0] wait_count;
 reg busy;
 reg [5:0] pending_k;
 wire valid=(active_k>=9 && active_k<=41);
 assign select_m[0]=valid && active_k>=28;
 assign select_m[1]=valid && active_k>=19 && active_k<=27;
 assign select_m[2]=valid && active_k>=14 && active_k<=18;
 assign select_m[3]=valid && active_k>=12 && active_k<=13;
 assign select_m[4]=valid && active_k>=10 && active_k<=11;
 assign select_m[5]=valid && active_k==9;
 assign divider_reset=reset || !ready;
 always @(posedge refclk or posedge reset) begin
  if(reset) begin
   req1<=0;req2<=0;req_old<=0;active_k<=0;pending_k<=0;
   ready<=0;invalid<=0;busy<=0;wait_count<=0;
  end else begin
   req1<=apply;req2<=req1;req_old<=req2;
   if(req2 && !req_old) begin
    pending_k<=cfg_k;ready<=0;invalid<=0;busy<=1;wait_count<=0;
   end else if(busy) begin
    if(wait_count==1) active_k<=pending_k;
    if(wait_count==7) begin
     ready<=(pending_k>=9 && pending_k<=41);
     invalid<=!(pending_k>=9 && pending_k<=41);busy<=0;
    end else wait_count<=wait_count+1'b1;
   end
  end
 end
endmodule

// Digital qualification only. phase_good/frequency_good are explicit sensing
// interfaces, not invented proof of analog phase lock. Inputs must be coherent
// at refclk (or synchronized by the producing measurement block).
// 32 good ref samples qualify; 4 bad samples after qualification request reacquire.
module pll_supervisor(input refclk,reset,cfg_ready,fll_enable,range_error,
 input phase_good,frequency_good,
 output pll_enable,output reg qualified,output reg restart,output reg fault);
 reg [5:0] good_count;
 reg [2:0] bad_count;
 reg [3:0] restart_count;
 wire good=phase_good && frequency_good;
 assign pll_enable=cfg_ready && fll_enable && !range_error && !restart && !reset;
 always @(posedge refclk or posedge reset) begin
  if(reset) begin
   qualified<=0;restart<=0;fault<=0;good_count<=0;bad_count<=0;restart_count<=0;
  end else if(!cfg_ready) begin
   qualified<=0;restart<=0;fault<=0;good_count<=0;bad_count<=0;restart_count<=0;
  end else if(range_error) begin
   qualified<=0;fault<=1;good_count<=0;bad_count<=0;
  end else if(restart) begin
   if(restart_count==7) begin restart<=0;restart_count<=0;end
   else restart_count<=restart_count+1'b1;
  end else if(!fll_enable) begin
   qualified<=0;good_count<=0;bad_count<=0;
  end else if(good) begin
   bad_count<=0;
   if(!qualified) begin
    if(good_count==31) begin qualified<=1;good_count<=0;end
    else good_count<=good_count+1'b1;
   end
  end else begin
   good_count<=0;
   if(qualified) begin
    if(bad_count==3) begin qualified<=0;restart<=1;restart_count<=0;bad_count<=0;end
    else bad_count<=bad_count+1'b1;
   end
  end
 end
endmodule
