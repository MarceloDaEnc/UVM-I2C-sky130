// =============================================================================
// FILE NAME      : i2c_rtl_wrapper.v
// =============================================================================
`timescale 1ns / 1ps

module i2c_rtl_wrapper #
(
    parameter CMD_FIFO   = 1,
    parameter WRITE_FIFO = 1,
    parameter READ_FIFO  = 1
)
(
    input  wire        clk,
    input  wire        rst,

    input  wire [3:0]  s_axil_awaddr,
    input  wire [2:0]  s_axil_awprot,
    input  wire        s_axil_awvalid,
    output wire        s_axil_awready,
    input  wire [31:0] s_axil_wdata,
    input  wire [3:0]  s_axil_wstrb,
    input  wire        s_axil_wvalid,
    output wire        s_axil_wready,
    output wire [1:0]  s_axil_bresp,
    output wire        s_axil_bvalid,
    input  wire        s_axil_bready,
    input  wire [3:0]  s_axil_araddr,
    input  wire [2:0]  s_axil_arprot,
    input  wire        s_axil_arvalid,
    output wire        s_axil_arready,
    output wire [31:0] s_axil_rdata,
    output wire [1:0]  s_axil_rresp,
    output wire        s_axil_rvalid,
    input  wire        s_axil_rready
);

wire master_scl_o, master_sda_o;
wire slave_scl_o,  slave_sda_o;
wire scl_bus = master_scl_o & slave_scl_o;
wire sda_bus = master_sda_o & slave_sda_o;

i2c_master_axil #(
    .DEFAULT_PRESCALE (1),
    .FIXED_PRESCALE   (0),
    .CMD_FIFO         (CMD_FIFO),
    .CMD_FIFO_DEPTH   (32),
    .WRITE_FIFO       (WRITE_FIFO),
    .WRITE_FIFO_DEPTH (32),
    .READ_FIFO        (READ_FIFO),
    .READ_FIFO_DEPTH  (32)
) i2c_master_inst (
    .clk              (clk),
    .rst              (rst),
    .s_axil_awaddr    (s_axil_awaddr),
    .s_axil_awprot    (s_axil_awprot),
    .s_axil_awvalid   (s_axil_awvalid),
    .s_axil_awready   (s_axil_awready),
    .s_axil_wdata     (s_axil_wdata),
    .s_axil_wstrb     (s_axil_wstrb),
    .s_axil_wvalid    (s_axil_wvalid),
    .s_axil_wready    (s_axil_wready),
    .s_axil_bresp     (s_axil_bresp),
    .s_axil_bvalid    (s_axil_bvalid),
    .s_axil_bready    (s_axil_bready),
    .s_axil_araddr    (s_axil_araddr),
    .s_axil_arprot    (s_axil_arprot),
    .s_axil_arvalid   (s_axil_arvalid),
    .s_axil_arready   (s_axil_arready),
    .s_axil_rdata     (s_axil_rdata),
    .s_axil_rresp     (s_axil_rresp),
    .s_axil_rvalid    (s_axil_rvalid),
    .s_axil_rready    (s_axil_rready),
    .i2c_scl_i        (scl_bus),
    .i2c_scl_o        (master_scl_o),
    .i2c_scl_t        (),
    .i2c_sda_i        (sda_bus),
    .i2c_sda_o        (master_sda_o),
    .i2c_sda_t        ()
);

wire [7:0] slave_m_axis_tdata;
wire       slave_m_axis_tvalid;
wire       slave_m_axis_tready;
wire       slave_m_axis_tlast;

wire [7:0] slave_s_axis_tdata;
wire       slave_s_axis_tvalid;
wire       slave_s_axis_tready;
wire       slave_s_axis_tlast;

wire       slave_bus_active;
wire       slave_bus_addressed;

i2c_slave #(
    .FILTER_LEN (1)
) i2c_slave_inst (
    .clk                    (clk),
    .rst                    (rst),
    .release_bus            (1'b0),
    .m_axis_data_tdata      (slave_m_axis_tdata),
    .m_axis_data_tvalid     (slave_m_axis_tvalid),
    .m_axis_data_tready     (slave_m_axis_tready),
    .m_axis_data_tlast      (slave_m_axis_tlast),
    .s_axis_data_tdata      (slave_s_axis_tdata),
    .s_axis_data_tvalid     (slave_s_axis_tvalid),
    .s_axis_data_tready     (slave_s_axis_tready),
    .s_axis_data_tlast      (slave_s_axis_tlast),
    .scl_i                  (scl_bus),
    .scl_o                  (slave_scl_o),
    .scl_t                  (),
    .sda_i                  (sda_bus),
    .sda_o                  (slave_sda_o),
    .sda_t                  (),
    .busy                   (),
    .bus_address            (),
    .bus_addressed          (slave_bus_addressed),
    .bus_active             (slave_bus_active),
    .enable                 (1'b1),
    .device_address         (7'h63),
    .device_address_mask    (7'h7f)
);

// ---------------------------------------------------------------------------
// Controlador de EEPROM
// ---------------------------------------------------------------------------
reg [7:0] slave_mem [0:255];
reg [7:0] current_addr;
reg       first_byte;      
reg [7:0] tx_data;
reg       tx_valid;
reg       bus_addressed_d;

integer k;
initial begin
    for (k = 0; k < 256; k = k + 1)
        slave_mem[k] = 8'h00;
    current_addr    = 8'h00;
    first_byte      = 1'b1;
    tx_data         = 8'h00;
    tx_valid        = 1'b0;
    bus_addressed_d = 1'b0;
end

assign slave_m_axis_tready = 1'b1;
assign slave_s_axis_tdata  = tx_data;
assign slave_s_axis_tvalid = tx_valid;
assign slave_s_axis_tlast  = 1'b0;

always @(posedge clk) begin
    if (rst) begin
        current_addr    <= 8'h00;
        first_byte      <= 1'b1;
        tx_data         <= 8'h00;
        tx_valid        <= 1'b0;
        bus_addressed_d <= 1'b0;
    end else begin
        bus_addressed_d <= slave_bus_addressed;

        if (slave_bus_addressed && !bus_addressed_d) begin
            first_byte <= 1'b1;
            tx_data  <= slave_mem[current_addr];
            tx_valid <= 1'b1;
        end

        if (slave_m_axis_tvalid && slave_m_axis_tready) begin
            if (first_byte) begin
                current_addr <= slave_m_axis_tdata;
                first_byte   <= 1'b0;
                tx_data  <= slave_mem[slave_m_axis_tdata];
                tx_valid <= 1'b1;
            end else begin
                slave_mem[current_addr] <= slave_m_axis_tdata;
                current_addr <= current_addr + 1;
                tx_data  <= slave_mem[current_addr + 1];
                tx_valid <= 1'b1;
            end
        end 
        else if (slave_s_axis_tready && tx_valid) begin
            current_addr <= current_addr + 1;
            tx_data  <= slave_mem[current_addr + 1];
            tx_valid <= 1'b1;
        end 
        else if (!tx_valid) begin
            tx_data  <= slave_mem[current_addr];
            tx_valid <= 1'b1;
        end
    end
end

initial begin
    $dumpvars(0);
end

endmodule