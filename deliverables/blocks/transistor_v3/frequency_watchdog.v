// Output-domain frequency check. 32 reference periods measure 32*K edges.
// +/-1 count tolerates asynchronous window quantization; this is not a ppm
// lock specification. For M<=14, an adjacent VCO reference harmonic differs
// by >=32/14 counts and lies outside this nominal acceptance interval.
// Use the existing counter + transparent-when-gate-low snapshot. Leave three
// reference periods after gate closure before examining the settled bus.
module frequency_watchdog(input refclk,reset,active,input [5:0] target_k,
 input [13:0] measured, output reg count_gate,output reg count_reset,
 output reg frequency_good, output reg valid);
 reg [7:0] tick;
 wire [13:0] target={3'b0,target_k,5'b0};
 always @(posedge refclk or posedge reset) begin
  if(reset) begin
   tick<=0;count_gate<=0;count_reset<=1;frequency_good<=0;valid<=0;
  end else if(!active) begin
   tick<=0;count_gate<=0;count_reset<=1;frequency_good<=0;valid<=0;
  end else begin
   tick<=tick+1'b1;valid<=0;
   case(tick)
    0: count_reset<=0;
    2: count_gate<=1;
    34: count_gate<=0;
    37: begin
     frequency_good <= target_k>=9 && target_k<=41 &&
       measured+14'd1>=target && measured<=target+14'd1;
     valid<=1;
    end
    38: count_reset<=1;
   endcase
  end
 end
endmodule
