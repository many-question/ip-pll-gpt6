// Candidate109: original SAR then fresh fine bisection with one automatic coarse recenter.
// Candidate: bounded fresh-count validation before PLL handoff.
// Coarse32/fine128 SAR precedes fresh verification with legal DAC bounds.
// Handoff uses two new matching measurements, never a stale minimum.
// Acquisition counts RF/4 for32 reference periods:3MHz RF count quantum.
// This is synthesized hardware, not a simulator shortcut; all counters remain MOS.
// Hardware acquisition controller. Count a continuously running divided output
// for 32 reference periods. Freeze counter and drain ripple carry before use.
// Probe code 0, coarse/fine SAR, then handoff only without a range error.
// This version does not implement background relock or a phase lock detector.
module fll_recenter109_v14(input refclk, input reset,
 input [5:0] target_k, input [13:0] measured,
 output reg [7:0] coarse, output reg [5:0] dac,
 output reg count_gate, output reg count_reset,
 output reg enable, output reg range_error,
 output [2:0] state_out);
 localparam SETTLE=0, MEASURE=1, DRAIN=2, EVAL=3, HANDOFF=4, DONE=5;
 reg [2:0] state;
 reg [7:0] tick;
 reg fine;
 reg endpoint_checked;
 reg [7:0] bitmask;
 reg verify_mode, good_once, coarse_recentered;
 reg [2:0] checks;
 // Target = K*M*8. Explicit channel plan matches kickstart/02.
 wire [13:0] kext = {8'b0,target_k};
 wire [13:0] coarse_target = (target_k==9) ? ((kext<<6)+(kext<<5)+(kext<<4)) :
   (target_k<=11) ? ((kext<<6)+(kext<<5)) :
   (target_k<=13) ? ((kext<<6)+(kext<<4)) :
   (target_k<=18) ? (kext<<6) :
   (target_k<=27) ? ((kext<<5)+(kext<<4)) : (kext<<5);
 wire [13:0] target = fine ? (coarse_target << 2) : coarse_target;
 wire high_freq = fine ? (measured >= target) : (measured > target);
 wire [7:0] coarse_keep = high_freq ? coarse : (coarse & ~bitmask);
 wire [5:0] fine_keep = high_freq ? (dac & ~bitmask[5:0]) : dac;
 wire [13:0] trial_error = (measured>=target) ? measured-target : target-measured;
 // Discard stale SAR minima. New measurements narrow inclusive DAC bounds.
 reg [5:0] verify_low, verify_high;
 wire [6:0] lower_sum = {1'b0,verify_low}+{1'b0,dac}-7'd1;
 wire [6:0] upper_sum = {1'b0,dac}+7'd1+{1'b0,verify_high};
 // Four DAC codes of edge margin are a candidate design assumption.
 // A fresh signed count can request at most one neighboring coarse code.
 wire need_slower = (dac<=15) && (measured>target);
 wire need_faster = (dac>=49) && (measured<target);
 assign state_out=state;
 always @(posedge refclk or posedge reset) begin
   if (reset) begin
     coarse<=0; dac<=11; bitmask<=8'h80; fine<=0; endpoint_checked<=0;
     state<=SETTLE; tick<=0; count_gate<=0; count_reset<=1;
     enable<=0; range_error<=0; verify_mode<=0; good_once<=0; checks<=0; coarse_recentered<=0; verify_low<=11; verify_high<=53;
   end else begin
     case(state)
       SETTLE: begin
         count_reset<=1; count_gate<=0;
         if(tick==(verify_mode ? 31 : 7)) begin tick<=0; count_reset<=0; state<=MEASURE; end
         else tick<=tick+1'b1;
       end
       MEASURE: begin
         count_gate<=1;
         if(tick==(fine ? 127 : 31)) begin tick<=0; state<=DRAIN; end
         else tick<=tick+1'b1;
       end
       DRAIN: begin
         count_gate<=0;
         if(tick==2) begin tick<=0; state<=EVAL; end
         else tick<=tick+1'b1;
       end
       EVAL: begin
         count_reset<=1; state<=SETTLE;
         // The SAR floor+1 search cannot distinguish code 0 from code 1.
         // Measure code 0 first so the high-frequency endpoint is reachable.
         if(!endpoint_checked) begin
           endpoint_checked<=1;
           if(high_freq) begin coarse<=8'h80; bitmask<=8'h80; end
           else begin coarse<=0; dac<=32; bitmask<=32; fine<=1; end
         end else if(!fine) begin
           if(bitmask==1) begin
             coarse <= (coarse_keep>=254) ? 255 : coarse_keep+2'd2;
             dac<=32; bitmask<=32; fine<=1;
           end else begin
             coarse<=coarse_keep | (bitmask>>1); bitmask<=bitmask>>1;
           end
         end else if(verify_mode) begin
           // Remeasure the currently applied code; never reuse an older minimum.
           // Two consecutive 128-ref windows within one RF count (0.75MHz).
           if(need_slower || need_faster) begin
             good_once<=0;
             if(coarse_recentered || checks==7 || (need_slower && coarse==255) || (need_faster && coarse==0)) begin
               range_error<=1; enable<=0; state<=DONE;
             end else begin
               coarse<=need_slower ? coarse+1'b1 : coarse-1'b1;
               coarse_recentered<=1; checks<=checks+1'b1;
               dac<=32; verify_low<=11; verify_high<=53;
             end
           end else if(trial_error<=1 && good_once) begin state<=HANDOFF; end
           else if(checks==7) begin range_error<=1; enable<=0; state<=DONE; end
           else begin
             checks<=checks+1'b1;
             if(trial_error<=1) good_once<=1;
             else begin
               good_once<=0;
               if(measured>target) begin
                 if(dac<=verify_low) begin range_error<=1; enable<=0; state<=DONE; end
                 else begin verify_high<=dac-1'b1; dac<=lower_sum[6:1]; end
               end else begin
                 if(dac>=verify_high) begin range_error<=1; enable<=0; state<=DONE; end
                 else begin verify_low<=dac+1'b1; dac<=upper_sum[6:1]; end
               end
             end
           end
         end else begin
           if(bitmask==1) begin
             // Midpoint is a search trial, never an accepted fixed code.
             // Always remeasure the full legal interval, even if old SAR saturated.
             dac<=32; verify_low<=11; verify_high<=53;
             verify_mode<=1; good_once<=0; checks<=0; state<=SETTLE;
           end else begin dac<=fine_keep | (bitmask[5:0]>>1); bitmask<=bitmask>>1; end
         end
       end
       HANDOFF: begin
         if(tick==31) begin enable<=!range_error; state<=DONE; tick<=0; end
         else tick<=tick+1'b1;
       end
       DONE: begin count_gate<=0; count_reset<=1; end
       default: begin state<=SETTLE; tick<=0; end
     endcase
   end
 end
endmodule
