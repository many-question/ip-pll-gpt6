// Hardware acquisition controller. Count a continuously running divided output
// for 256 reference periods. Freeze counter and drain ripple carry before use.
// Probe code 0, coarse/fine SAR, then handoff only without a range error.
// This version does not implement background relock or a phase lock detector.
module fll_controller(input refclk, input reset,
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
 wire [13:0] target = {target_k,8'b0};
 wire high_freq = measured > target;
 wire [7:0] coarse_keep = high_freq ? coarse : (coarse & ~bitmask);
 wire [5:0] fine_keep = high_freq ? (dac & ~bitmask[5:0]) : dac;
 assign state_out=state;
 always @(posedge refclk or posedge reset) begin
   if (reset) begin
     coarse<=0; dac<=11; bitmask<=8'h80; fine<=0; endpoint_checked<=0;
     state<=SETTLE; tick<=0; count_gate<=0; count_reset<=1;
     enable<=0; range_error<=0;
   end else begin
     case(state)
       SETTLE: begin
         count_reset<=1; count_gate<=0;
         if(tick==7) begin tick<=0; count_reset<=0; state<=MEASURE; end
         else tick<=tick+1'b1;
       end
       MEASURE: begin
         count_gate<=1;
         if(tick==255) begin tick<=0; state<=DRAIN; end
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
             coarse <= (coarse_keep==255) ? 255 : coarse_keep+1'b1;
             dac<=32; bitmask<=32; fine<=1;
           end else begin
             coarse<=coarse_keep | (bitmask>>1); bitmask<=bitmask>>1;
           end
         end else begin
           if(bitmask==1) begin
             if(fine_keep<11) begin dac<=11; range_error<=1; end
             else if(fine_keep>52) begin dac<=53; range_error<=1; end
             else dac<=fine_keep+1'b1;
             state<=HANDOFF;
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
