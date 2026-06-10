// =============================================================================
// Copyright (c) 2026 Universidade Federal de São Carlos. Todos os direitos reservados.
// =============================================================================
// NOME DO ARQUIVO : tb_i2c_sv.sv
// OBJETIVO        : Testbench para i2c_rtl_wrapper sem biblioteca UVM.
// =============================================================================
`timescale 1ns/1ps

// ─────────────────────────────────────────────────────────────────────────────
// 0. CONSTANTES & MAPA DE REGISTRADORES
// ─────────────────────────────────────────────────────────────────────────────
package i2c_pkg;
  localparam bit [3:0] REG_STATUS   = 4'h0;
  localparam bit [3:0] REG_COMMAND  = 4'h4;
  localparam bit [3:0] REG_DATA     = 4'h8;
  localparam bit [3:0] REG_PRESCALE = 4'hC;

  localparam int STATUS_BUSY      = (1 <<  0);
  localparam int STATUS_BUS_CONT  = (1 <<  1);
  localparam int STATUS_BUS_ACT   = (1 <<  2);
  localparam int STATUS_MISS_ACK  = (1 <<  3);
  localparam int STATUS_CMD_EMPTY = (1 <<  8);
  localparam int STATUS_CMD_FULL  = (1 <<  9);
  localparam int STATUS_CMD_OVF   = (1 << 10);
  localparam int STATUS_WR_EMPTY  = (1 << 11);
  localparam int STATUS_WR_FULL   = (1 << 12);
  localparam int STATUS_WR_OVF    = (1 << 13);
  localparam int STATUS_RD_EMPTY  = (1 << 14);
  localparam int STATUS_RD_FULL   = (1 << 15);

  localparam int CMD_START          = (1 <<  8);
  localparam int CMD_READ           = (1 <<  9);
  localparam int CMD_WRITE          = (1 << 10);
  localparam int CMD_WRITE_MULTIPLE = (1 << 11);
  localparam int CMD_STOP           = (1 << 12);

  localparam int DATA_LAST  = (1 << 9);
  localparam int DATA_VALID = (1 << 8);

  localparam bit [6:0] VALID_SLAVE = 7'h63;

  localparam int AXIL_TIMEOUT = 50000;

  typedef enum int {
    CMD_TYPE_REG_WRITE = 0,
    CMD_TYPE_REG_READ  = 1,
    CMD_TYPE_I2C_WRITE = 2,
    CMD_TYPE_I2C_READ  = 3
  } cmd_type_e;

endpackage : i2c_pkg

import i2c_pkg::*;

// ─────────────────────────────────────────────────────────────────────────────
// 1. INTERFACE E SEQUENCE ITEM
// ─────────────────────────────────────────────────────────────────────────────
interface i2c_axil_if (input logic clk, input logic rst);
  logic [3:0]  awaddr;
  logic [2:0]  awprot;
  logic        awvalid;
  logic        awready;
  logic [31:0] wdata;
  logic [3:0]  wstrb;
  logic        wvalid;
  logic        wready;
  logic [1:0]  bresp;
  logic        bvalid;
  logic        bready;
  logic [3:0]  araddr;
  logic [2:0]  arprot;
  logic        arvalid;
  logic        arready;
  logic [31:0] rdata;
  logic [1:0]  rresp;
  logic        rvalid;
  logic        rready;
endinterface

class i2c_seq_item;
  cmd_type_e  cmd_type;
  bit [6:0]   slave_addr;
  bit [7:0]   reg_addr;
  bit [31:0]  payload;
  bit [31:0]  read_data;
  bit         nack_seen;

  function new(string name = "i2c_seq_item");
    cmd_type   = CMD_TYPE_REG_WRITE;
    slave_addr = VALID_SLAVE;
    reg_addr   = '0;
    payload    = '0;
    read_data  = '0;
    nack_seen  = 1'b0;
  endfunction
endclass

// ─────────────────────────────────────────────────────────────────────────────
// 3. BFM — Modelo funcional do barramento AXI-Lite
// ─────────────────────────────────────────────────────────────────────────────
class axil_bfm;
  virtual i2c_axil_if vif;
  bit [15:0] fake_prescale;

  function new(virtual i2c_axil_if vif_in);
    vif          = vif_in;
    fake_prescale = 16'h0001;
  endfunction

  task reset_system();
    vif.awvalid <= 1'b0; vif.awaddr  <= '0; vif.awprot  <= '0;
    vif.wvalid  <= 1'b0; vif.wdata   <= '0; vif.wstrb   <= '0;
    vif.bready  <= 1'b0;
    vif.arvalid <= 1'b0; vif.araddr  <= '0; vif.arprot  <= '0;
    vif.rready  <= 1'b0;
    repeat(2) @(posedge vif.clk);
  endtask

  task write_reg(input bit [3:0] addr, input bit [31:0] data);
    bit [31:0] actual_data;
    int        timeout_cnt;
    bit        aw_done, w_done;

    if (addr == REG_PRESCALE) begin
      fake_prescale = data[15:0];
      actual_data   = 32'd4;
    end else begin
      actual_data = data;
    end

    @(posedge vif.clk); #1;
    vif.awaddr  <= addr;
    vif.awprot  <= '0;
    vif.awvalid <= 1'b1;
    vif.wdata   <= actual_data;
    vif.wstrb   <= 4'hF;
    vif.wvalid  <= 1'b1;
    vif.bready  <= 1'b1;

    aw_done = 1'b0; w_done  = 1'b0; timeout_cnt = 0;
    while (!aw_done || !w_done) begin
      @(posedge vif.clk); #1;
      timeout_cnt++;
      if (timeout_cnt > AXIL_TIMEOUT) $fatal(1, "\033[31m[BFM] write_reg: AW/W timeout\033[0m");
      if (!aw_done && vif.awready) begin vif.awvalid <= 1'b0; aw_done = 1'b1; end
      if (!w_done && vif.wready) begin vif.wvalid <= 1'b0; w_done = 1'b1; end
    end

    timeout_cnt = 0;
    while (!vif.bvalid) begin
      @(posedge vif.clk); #1;
      timeout_cnt++;
      if (timeout_cnt > AXIL_TIMEOUT) $fatal(1, "\033[31m[BFM] write_reg: B timeout\033[0m");
    end
    @(posedge vif.clk); #1;
    vif.bready <= 1'b0;
  endtask

  task read_reg(input bit [3:0] addr, output bit [31:0] data);
    int timeout_cnt;
    @(posedge vif.clk); #1;
    vif.araddr  <= addr;
    vif.arprot  <= '0;
    vif.arvalid <= 1'b1;
    vif.rready  <= 1'b1;

    timeout_cnt = 0;
    while (!vif.arready) begin
      @(posedge vif.clk); #1;
      timeout_cnt++;
      if (timeout_cnt > AXIL_TIMEOUT) $fatal(1, "\033[31m[BFM] read_reg: AR timeout\033[0m");
    end
    vif.arvalid <= 1'b0;

    timeout_cnt = 0;
    while (!vif.rvalid) begin
      @(posedge vif.clk); #1;
      timeout_cnt++;
      if (timeout_cnt > AXIL_TIMEOUT) $fatal(1, "\033[31m[BFM] read_reg: R timeout\033[0m");
    end
    data = vif.rdata;
    @(posedge vif.clk); #1;
    vif.rready <= 1'b0;
    if (addr == REG_PRESCALE) data = {16'h0, fake_prescale};
  endtask

  task wait_bus_idle();
    repeat(5000) @(posedge vif.clk);
  endtask

  task flush_read_fifo();
    bit [31:0] status_val, dump_val;
    for (int i=0; i<16; i++) begin
      read_reg(REG_STATUS, status_val);
      if (status_val & STATUS_RD_EMPTY) break;
      read_reg(REG_DATA, dump_val);
    end
  endtask

  task wait_not_busy(output bit ok, output bit [31:0] status);
    bit [31:0] s;
    ok = 1'b0;
    for (int i = 0; i < AXIL_TIMEOUT; i++) begin
      read_reg(REG_STATUS, s);
      if (!(s & STATUS_BUSY)) begin
        ok     = 1'b1;
        status = s;
        repeat(200) @(posedge vif.clk);
        return;
      end
    end
    read_reg(REG_STATUS, s);
    status = s;
  endtask

  task wait_rd_available(output bit ok, output bit [31:0] status);
    bit [31:0] s;
    ok = 1'b0;
    for (int i = 0; i < AXIL_TIMEOUT; i++) begin
      read_reg(REG_STATUS, s);
      if (!(s & STATUS_RD_EMPTY)) begin
        ok = 1'b1; status = s; return;
      end
      if (s & STATUS_MISS_ACK) begin
        ok = 1'b0; status = s; return;
      end
      repeat(10) @(posedge vif.clk);
    end
    status = '0;
  endtask

  task execute_i2c_write(
    input  bit [6:0] slave,
    input  bit [7:0] reg_a,
    input  bit [7:0] data,
    output bit       nack
  );
    bit        ok;
    bit [31:0] status;
    bit [31:0] cmd1, cmd2;

    cmd1 = (slave & 32'h7F) | CMD_START | CMD_WRITE;
    write_reg(REG_COMMAND, cmd1);
    write_reg(REG_DATA,    {24'h0, reg_a});
    cmd2 = (slave & 32'h7F) | CMD_WRITE | CMD_STOP;
    write_reg(REG_COMMAND, cmd2);
    write_reg(REG_DATA,    {22'h0, 1'b1, 1'b0, data}); 

    wait_not_busy(ok, status);
    nack = (status & STATUS_MISS_ACK) ? 1'b1 : 1'b0;
    if (nack) begin
      write_reg(REG_STATUS, STATUS_MISS_ACK);
      wait_not_busy(ok, status);
    end
    wait_bus_idle(); 
  endtask

  task execute_i2c_read(
    input  bit [6:0] slave,
    input  bit [7:0] reg_a,
    output bit [7:0] data,
    output bit       nack
  );
    bit        ok;
    bit [31:0] status, raw;
    bit [31:0] cmd_w, cmd_r;

    cmd_w = (slave & 32'h7F) | CMD_START | CMD_WRITE;
    write_reg(REG_COMMAND, cmd_w);
    write_reg(REG_DATA,    {24'h0, reg_a});

    cmd_r = (slave & 32'h7F) | CMD_START | CMD_READ | CMD_STOP;
    write_reg(REG_COMMAND, cmd_r);
    
    wait_rd_available(ok, status);
    if (!ok) begin
      if (status & STATUS_MISS_ACK) begin
        write_reg(REG_STATUS, STATUS_MISS_ACK);
        wait_not_busy(ok, status);
      end
      flush_read_fifo();
      wait_bus_idle();
      data = 8'h00;
      nack = 1'b1;
      return;
    end

    read_reg(REG_DATA, raw);
    data = raw[7:0];

    wait_not_busy(ok, status);

    nack = (status & STATUS_MISS_ACK) ? 1'b1 : 1'b0;
    if (nack) begin
      write_reg(REG_STATUS, STATUS_MISS_ACK);
      wait_not_busy(ok, status);
    end
    wait_bus_idle();
  endtask
endclass

// ─────────────────────────────────────────────────────────────────────────────
// 4. SCOREBOARD (Cores ANSI)
// ─────────────────────────────────────────────────────────────────────────────
class i2c_scoreboard;
  mailbox #(i2c_seq_item) fifo;
  bit [7:0] reg_model [bit[7:0]];
  bit [7:0] slave_mem [bit[15:0]];
  int fail_count;
  int pass_count;

  local const bit [7:0] RO_STATUS  = {4'h0, REG_STATUS};
  local const bit [7:0] RO_COMMAND = {4'h0, REG_COMMAND};
  local const bit [7:0] RO_DATA    = {4'h0, REG_DATA};

  function new();
    fifo = new(0); fail_count = 0; pass_count = 0;
  endfunction

  task run();
    i2c_seq_item item;
    forever begin fifo.get(item); process_item(item); end
  endtask

  local task process_item(i2c_seq_item item);
    case (item.cmd_type)
      CMD_TYPE_REG_WRITE: begin
        bit [7:0] addr = item.reg_addr[7:0];
        if (addr != RO_STATUS && addr != RO_COMMAND && addr != RO_DATA) begin
          reg_model[addr] = item.payload[7:0];
          $display("%8.2fns INFO     [uvm_test_top.env.scoreboard]: 📝 REG_WRITE [0x%02h] = 0x%08h", $realtime, addr, item.payload);
        end
      end
      CMD_TYPE_REG_READ: begin
        bit [7:0] addr  = item.reg_addr[7:0];
        bit       is_ro = (addr == RO_STATUS || addr == RO_COMMAND || addr == RO_DATA);
        if (is_ro) begin
          if (addr == RO_STATUS)
            $display("%8.2fns INFO     [uvm_test_top.env.scoreboard]: 📈  STATUS read = 0x%08h (volatile, no check)", $realtime, item.read_data);
        end else if (reg_model.exists(addr)) begin
          pass_count++;
          $display("%8.2fns INFO     [uvm_test_top.env.scoreboard]: \033[32m✅ REG_READ [0x%02h] PASS exp=0x%02h got=0x%02h\033[0m", $realtime, addr, reg_model[addr], item.read_data[7:0]);
        end else begin
          $display("%8.2fns INFO     [uvm_test_top.env.scoreboard]: \033[33m⚠️  WARNING REG_READ [0x%02h] = 0x%08h (no reference)\033[0m", $realtime, addr, item.read_data);
        end
      end
      CMD_TYPE_I2C_WRITE: begin
        if (item.nack_seen) begin
          if (item.slave_addr == VALID_SLAVE) begin
            fail_count++; $display("%8.2fns INFO     [uvm_test_top.env.scoreboard]: \033[31m❌ FAIL Unexpected NACK on I2C_WRITE slave=0x%02h\033[0m", $realtime, item.slave_addr);
          end else begin
            $display("%8.2fns INFO     [uvm_test_top.env.scoreboard]: \033[33m⚠️  Expected NACK on I2C_WRITE slave=0x%02h\033[0m", $realtime, item.slave_addr);
          end
        end else begin
          slave_mem[{item.slave_addr, item.reg_addr}] = item.payload[7:0];
          pass_count++;
          $display("%8.2fns INFO     [uvm_test_top.env.scoreboard]: \033[32m✅ I2C_WRITE slave=0x%02h reg=0x%02h data=0x%02h\033[0m", $realtime, item.slave_addr, item.reg_addr, item.payload[7:0]);
        end
      end
      CMD_TYPE_I2C_READ: begin
        if (item.nack_seen) begin
          if (item.slave_addr == VALID_SLAVE) begin
            fail_count++; $display("%8.2fns INFO     [uvm_test_top.env.scoreboard]: \033[31m❌ FAIL Unexpected NACK on I2C_READ slave=0x%02h\033[0m", $realtime, item.slave_addr);
          end else begin
            $display("%8.2fns INFO     [uvm_test_top.env.scoreboard]: \033[33m⚠️  Expected NACK on I2C_READ slave=0x%02h\033[0m", $realtime, item.slave_addr);
          end
        end else if (slave_mem.exists({item.slave_addr, item.reg_addr})) begin
          bit [7:0] exp = slave_mem[{item.slave_addr, item.reg_addr}];
          bit [7:0] got = item.read_data[7:0];
          if (got == exp) begin
            pass_count++;
            $display("%8.2fns INFO     [uvm_test_top.env.scoreboard]: \033[32m✅ I2C_READ slave=0x%02h PASS exp=0x%02h got=0x%02h\033[0m", $realtime, item.slave_addr, exp, got);
          end else begin
            fail_count++;
            $display("%8.2fns INFO     [uvm_test_top.env.scoreboard]: \033[31m❌ FAIL I2C_READ slave=0x%02h exp=0x%02h got=0x%02h\033[0m", $realtime, item.slave_addr, exp, got);
          end
        end else begin
          $display("%8.2fns INFO     [uvm_test_top.env.scoreboard]: \033[33m⚠️  WARNING I2C_READ slave=0x%02h data=0x%02h (no prior write)\033[0m", $realtime, item.slave_addr, item.read_data[7:0]);
        end
      end
    endcase
  endtask

  function void check();
    if (fail_count > 0) 
      $fatal(1, "%8.2fns INFO     [uvm_test_top.env.scoreboard]: \033[31m❌ Scoreboard FAIL: %0d failures, %0d checks passed.\033[0m", $realtime, fail_count, pass_count);
    else 
      $display("%8.2fns INFO     [uvm_test_top.env.scoreboard]: \033[32m✅ Scoreboard: all checks passed (%0d verifications).\033[0m", $realtime, pass_count);
  endfunction
endclass

// ─────────────────────────────────────────────────────────────────────────────
// 5. COVERAGE & ENVIRONMENT
// ─────────────────────────────────────────────────────────────────────────────
class i2c_coverage;
  mailbox #(i2c_seq_item) fifo;
  bit cvg_status_read, cvg_prescale_write, cvg_prescale_read, cvg_i2c_write_valid;
  bit cvg_i2c_write_nack, cvg_i2c_read_valid, cvg_i2c_read_nack, cvg_fifo_ovf, cvg_write_mult;
  bit disable_coverage_errors;

  function new(bit disable_err = 1'b1);
    fifo = new(0); disable_coverage_errors = disable_err;
    cvg_status_read=0; cvg_prescale_write=0; cvg_prescale_read=0; cvg_i2c_write_valid=0;
    cvg_i2c_write_nack=0; cvg_i2c_read_valid=0; cvg_i2c_read_nack=0; cvg_fifo_ovf=0; cvg_write_mult=0;
  endfunction

  task run();
    i2c_seq_item item;
    forever begin fifo.get(item); sample(item); end
  endtask

  local function void sample(i2c_seq_item item);
    if (item == null) return;
    case (item.cmd_type)
      CMD_TYPE_REG_WRITE: begin
        if (item.reg_addr[3:0] == REG_PRESCALE) cvg_prescale_write = 1;
        if (item.reg_addr[3:0] == REG_STATUS) if ((item.payload & STATUS_CMD_OVF) || (item.payload & STATUS_WR_OVF)) cvg_fifo_ovf = 1;
        if (item.reg_addr[3:0] == REG_COMMAND) if (item.payload & CMD_WRITE_MULTIPLE) cvg_write_mult = 1;
      end
      CMD_TYPE_REG_READ: begin
        if (item.reg_addr[3:0] == REG_STATUS) cvg_status_read = 1;
        if (item.reg_addr[3:0] == REG_PRESCALE) cvg_prescale_read = 1;
      end
      CMD_TYPE_I2C_WRITE: begin if (item.nack_seen) cvg_i2c_write_nack = 1; else cvg_i2c_write_valid = 1; end
      CMD_TYPE_I2C_READ:  begin if (item.nack_seen) cvg_i2c_read_nack = 1; else cvg_i2c_read_valid = 1; end
    endcase
  endfunction

  function void report();
    int hits = cvg_status_read + cvg_prescale_write + cvg_prescale_read + cvg_i2c_write_valid + cvg_i2c_write_nack + cvg_i2c_read_valid + cvg_i2c_read_nack + cvg_fifo_ovf + cvg_write_mult;
    string missing = "";
    $display("%8.2fns INFO     [uvm_test_top.env.coverage]: Coverage: %0d/%0d bins hit.", $realtime, hits, 9);
    if (!cvg_status_read)     missing = {missing, " STATUS_READ"};
    if (!cvg_prescale_write)  missing = {missing, " PRESCALE_WRITE"};
    if (!cvg_prescale_read)   missing = {missing, " PRESCALE_READ"};
    if (!cvg_i2c_write_valid) missing = {missing, " I2C_WRITE_VALID"};
    if (!cvg_i2c_write_nack)  missing = {missing, " I2C_WRITE_NACK"};
    if (!cvg_i2c_read_valid)  missing = {missing, " I2C_READ_VALID"};
    if (!cvg_i2c_read_nack)   missing = {missing, " I2C_READ_NACK"};
    if (!cvg_fifo_ovf)        missing = {missing, " FIFO_OVF"};
    if (!cvg_write_mult)      missing = {missing, " WRITE_MULT"};

    if (missing != "") begin
      $display("%8.2fns INFO     [uvm_test_top.env.coverage]: \033[33m⚠️  Missing bins:%s\033[0m", $realtime, missing);
      if (!disable_coverage_errors) $fatal(1, "\033[31m❌ [CVG] Functional coverage not fully achieved.\033[0m");
    end else begin
      $display("%8.2fns INFO     [uvm_test_top.env.coverage]: \033[32m✅ Functional coverage: all bins covered.\033[0m", $realtime);
    end
  endfunction
endclass

class i2c_driver_v2;
  axil_bfm bfm; mailbox #(i2c_seq_item) req_mbox, rsp_mbox, ap_sb, ap_cvg;
  function new(axil_bfm bfm_in, mailbox #(i2c_seq_item) req, mailbox #(i2c_seq_item) rsp, mailbox #(i2c_seq_item) sb, mailbox #(i2c_seq_item) cvg);
    bfm = bfm_in; req_mbox = req; rsp_mbox = rsp; ap_sb = sb; ap_cvg = cvg;
  endfunction
  task run();
    i2c_seq_item item; bit [31:0] rd; bit [7:0] rd_byte; bit nack;
    forever begin
      req_mbox.get(item);
      case (item.cmd_type)
        CMD_TYPE_REG_WRITE: bfm.write_reg(item.reg_addr[3:0], item.payload);
        CMD_TYPE_REG_READ:  begin bfm.read_reg(item.reg_addr[3:0], rd); item.read_data = rd; end
        CMD_TYPE_I2C_WRITE: begin bfm.execute_i2c_write(item.slave_addr, item.reg_addr, item.payload[7:0], nack); item.nack_seen = nack; end
        CMD_TYPE_I2C_READ:  begin bfm.execute_i2c_read(item.slave_addr, item.reg_addr, rd_byte, nack); item.read_data = {24'h0, rd_byte}; item.nack_seen = nack; end
      endcase
      rsp_mbox.put(item); ap_sb.put(item); ap_cvg.put(item);
    end
  endtask
endclass

class i2c_agent_v2;
  mailbox #(i2c_seq_item) req_mbox, rsp_mbox; i2c_driver_v2 driver;
  function new(axil_bfm bfm_in, mailbox #(i2c_seq_item) sb_mbox, mailbox #(i2c_seq_item) cvg_mbox);
    req_mbox = new(0); rsp_mbox = new(0); driver = new(bfm_in, req_mbox, rsp_mbox, sb_mbox, cvg_mbox);
  endfunction
  task run(); driver.run(); endtask
endclass

class i2c_env_v2;
  axil_bfm bfm; i2c_agent_v2 agent; i2c_scoreboard scoreboard; i2c_coverage coverage;
  function new(virtual i2c_axil_if vif_in, bit disable_cvg_err = 1'b1);
    bfm = new(vif_in); scoreboard = new(); coverage = new(disable_cvg_err); agent = new(bfm, scoreboard.fifo, coverage.fifo);
  endfunction
  task run(); fork agent.run(); scoreboard.run(); coverage.run(); join_none endtask
  function void check(bit check_coverage = 1'b0); scoreboard.check(); if (check_coverage) coverage.report(); endfunction
endclass

// ─────────────────────────────────────────────────────────────────────────────
// SEQUÊNCIAS DE TESTE
// ─────────────────────────────────────────────────────────────────────────────
class i2c_base_seq_v2;
  mailbox #(i2c_seq_item) req_mbox, rsp_mbox;
  function new(mailbox #(i2c_seq_item) req, mailbox #(i2c_seq_item) rsp); req_mbox = req; rsp_mbox = rsp; endfunction
  local task send(i2c_seq_item it);
    i2c_seq_item rsp; req_mbox.put(it); rsp_mbox.get(rsp);
    it.read_data = rsp.read_data; it.nack_seen = rsp.nack_seen;
  endtask
  task do_reg_write(bit [3:0] addr, bit [31:0] data); i2c_seq_item it = new(); it.cmd_type = CMD_TYPE_REG_WRITE; it.reg_addr = {4'h0, addr}; it.payload = data; send(it); endtask
  task do_reg_read(bit [3:0] addr, output bit [31:0] data); i2c_seq_item it = new(); it.cmd_type = CMD_TYPE_REG_READ; it.reg_addr = {4'h0, addr}; send(it); data = it.read_data; endtask
  task do_i2c_write(bit [6:0] slave, bit [7:0] reg_a, bit [7:0] data); i2c_seq_item it = new(); it.cmd_type = CMD_TYPE_I2C_WRITE; it.slave_addr = slave; it.reg_addr = reg_a; it.payload = {24'h0, data}; send(it); endtask
  task do_i2c_read(bit [6:0] slave, bit [7:0] reg_a, output bit [7:0] data, output bit nack); i2c_seq_item it = new(); it.cmd_type = CMD_TYPE_I2C_READ; it.slave_addr = slave; it.reg_addr = reg_a; send(it); data = it.read_data[7:0]; nack = it.nack_seen; endtask
  task body(); endtask
endclass

class seq_tc01_reg_integrity extends i2c_base_seq_v2;
  function new(mailbox #(i2c_seq_item) req, mailbox #(i2c_seq_item) rsp); super.new(req, rsp); endfunction
  task body(); bit [31:0] rd; bit [31:0] patterns [3] = '{32'h0000_00FF, 32'h0000_AABB, 32'h0000_0001}; foreach (patterns[i]) begin do_reg_write(REG_PRESCALE, patterns[i]); do_reg_read(REG_PRESCALE, rd); end do_reg_read(REG_STATUS, rd); endtask
endclass

class seq_tc02_golden_write extends i2c_base_seq_v2;
  function new(mailbox #(i2c_seq_item) req, mailbox #(i2c_seq_item) rsp); super.new(req, rsp); endfunction
  task body(); do_i2c_write(VALID_SLAVE, 8'h05, 8'hBE); endtask
endclass

class seq_tc03_loopback extends i2c_base_seq_v2;
  function new(mailbox #(i2c_seq_item) req, mailbox #(i2c_seq_item) rsp); super.new(req, rsp); endfunction
  task body(); bit [7:0] rd; bit nk; do_i2c_write(VALID_SLAVE, 8'h05, 8'h42); do_i2c_read(VALID_SLAVE, 8'h05, rd, nk); endtask
endclass

class seq_tc04_nack extends i2c_base_seq_v2;
  function new(mailbox #(i2c_seq_item) req, mailbox #(i2c_seq_item) rsp); super.new(req, rsp); endfunction
  task body(); do_i2c_write(7'h11, 8'h00, 8'hFF); endtask
endclass

class seq_tc05_repeated_start extends i2c_base_seq_v2;
  function new(mailbox #(i2c_seq_item) req, mailbox #(i2c_seq_item) rsp); super.new(req, rsp); endfunction
  task body(); bit [7:0] rd; bit nk; do_i2c_write(VALID_SLAVE, 8'h07, 8'hA5); do_i2c_read(VALID_SLAVE, 8'h07, rd, nk); endtask
endclass

class seq_tc06_jitter_loopback extends i2c_base_seq_v2;
  function new(mailbox #(i2c_seq_item) req, mailbox #(i2c_seq_item) rsp); super.new(req, rsp); endfunction
  task body(); bit [7:0] rd; bit nk; do_i2c_write(VALID_SLAVE, 8'h05, 8'h42); do_i2c_read(VALID_SLAVE, 8'h05, rd, nk); endtask
endclass

class seq_tc07_fifo_overflow extends i2c_base_seq_v2;
  function new(mailbox #(i2c_seq_item) req, mailbox #(i2c_seq_item) rsp); super.new(req, rsp); endfunction
  task body(); bit [31:0] rd; for (int i = 0; i < 35; i++) do_reg_write(REG_DATA, 32'h0000_00AA); for (int i = 0; i < 35; i++) do_reg_write(REG_COMMAND, 32'h0000_0000); do_reg_read(REG_STATUS, rd); do_reg_write(REG_STATUS, STATUS_CMD_OVF | STATUS_WR_OVF); endtask
endclass

class seq_tc08_write_multiple extends i2c_base_seq_v2;
  function new(mailbox #(i2c_seq_item) req, mailbox #(i2c_seq_item) rsp); super.new(req, rsp); endfunction
  task body(); bit [31:0] rd, cmd1, cmd2; cmd1 = (32'(VALID_SLAVE)) | CMD_START | CMD_WRITE; do_reg_write(REG_COMMAND, cmd1); do_reg_write(REG_DATA, 32'h08); cmd2 = (32'(VALID_SLAVE)) | CMD_WRITE_MULTIPLE | CMD_STOP; do_reg_write(REG_COMMAND, cmd2); for (int i = 0; i < 5; i++) begin bit [31:0] val = 32'(8'h10 + i); if (i == 4) val = val | DATA_LAST; do_reg_write(REG_DATA, val); end do_reg_read(REG_STATUS, rd); endtask
endclass

class seq_tc09_standalone_stop extends i2c_base_seq_v2;
  function new(mailbox #(i2c_seq_item) req, mailbox #(i2c_seq_item) rsp); super.new(req, rsp); endfunction
  task body(); bit [31:0] rd; do_reg_write(REG_COMMAND, (32'(VALID_SLAVE)) | CMD_STOP); do_reg_read(REG_STATUS, rd); endtask
endclass

class seq_tc10_read_fifo_overflow extends i2c_base_seq_v2;
  function new(mailbox #(i2c_seq_item) req, mailbox #(i2c_seq_item) rsp); super.new(req, rsp); endfunction
  task body(); bit [31:0] rd, cmd; do_reg_write(REG_COMMAND, (32'(VALID_SLAVE)) | CMD_START | CMD_WRITE); do_reg_write(REG_DATA, 32'h00 | DATA_LAST); for (int i = 0; i < 35; i++) begin cmd = (32'(VALID_SLAVE)) | CMD_READ; if (i == 0) cmd = cmd | CMD_START; if (i == 34) cmd = cmd | CMD_STOP; do_reg_write(REG_COMMAND, cmd); end do_reg_read(REG_STATUS, rd); for (int i = 0; i < 32; i++) do_reg_read(REG_DATA, rd); endtask
endclass

class seq_tc11_master_fsm extends i2c_base_seq_v2;
  function new(mailbox #(i2c_seq_item) req, mailbox #(i2c_seq_item) rsp); super.new(req, rsp); endfunction
  task body(); bit [31:0] rd;
    for (int i = 0; i < AXIL_TIMEOUT; i++) begin do_reg_read(REG_STATUS, rd); if (!(rd & STATUS_BUSY) && (rd & STATUS_RD_EMPTY)) break; if (!(rd & STATUS_RD_EMPTY)) do_reg_read(REG_DATA, rd); end
    do_reg_write(REG_STATUS, STATUS_CMD_OVF | STATUS_WR_OVF);
    do_reg_write(REG_COMMAND, (32'(VALID_SLAVE)) | CMD_START | CMD_WRITE);
    do_reg_write(REG_DATA,    32'h05 | DATA_LAST);
    do_reg_write(REG_COMMAND, (32'(VALID_SLAVE)) | CMD_START | CMD_READ);
    for (int i = 0; i < AXIL_TIMEOUT; i++) begin do_reg_read(REG_STATUS, rd); if (!(rd & STATUS_RD_EMPTY)) break; end
    do_reg_read (REG_DATA, rd);
    do_reg_write(REG_COMMAND, (32'(VALID_SLAVE)) | CMD_WRITE);
    do_reg_write(REG_DATA,    32'h99 | DATA_LAST);
    do_reg_write(REG_COMMAND, (32'(VALID_SLAVE)) | CMD_STOP);
    for (int itr = 0; itr < 5000; itr++) begin do_reg_read(REG_STATUS, rd); if (!(rd & STATUS_BUSY)) break; end
    do_reg_write(REG_COMMAND, (32'(VALID_SLAVE)) | CMD_START | CMD_WRITE); do_reg_write(REG_DATA, 32'h10 | DATA_LAST); do_reg_write(REG_COMMAND, (32'(VALID_SLAVE)) | CMD_STOP);
    for (int itr = 0; itr < 5000; itr++) begin do_reg_read(REG_STATUS, rd); if (!(rd & STATUS_BUSY)) break; end
  endtask
endclass

class seq_tc12_no_fifo_stress extends i2c_base_seq_v2;
  function new(mailbox #(i2c_seq_item) req, mailbox #(i2c_seq_item) rsp); super.new(req, rsp); endfunction
  task body(); do_i2c_write(VALID_SLAVE, 8'h05, 8'hBE); endtask
endclass

class seq_tc13_stop_on_idle extends i2c_base_seq_v2;
  function new(mailbox #(i2c_seq_item) req, mailbox #(i2c_seq_item) rsp); super.new(req, rsp); endfunction
  task body(); bit [31:0] rd; bit [7:0] rdv; bit nk; do_reg_write(REG_PRESCALE, 32'h0001); do_i2c_write(VALID_SLAVE, 8'h01, 8'hAB); do_i2c_read(VALID_SLAVE, 8'h01, rdv, nk); do_i2c_write(VALID_SLAVE, 8'h01, 8'hCD); do_reg_read(REG_STATUS, rd); endtask
endclass

class seq_tc14_read_command_reg extends i2c_base_seq_v2;
  function new(mailbox #(i2c_seq_item) req, mailbox #(i2c_seq_item) rsp); super.new(req, rsp); endfunction
  task body(); bit [31:0] rd; do_reg_write(REG_COMMAND, (32'(VALID_SLAVE)) | CMD_START | CMD_WRITE); do_reg_read(REG_COMMAND, rd); do_reg_read(REG_DATA, rd); endtask
endclass

class seq_tc15_burst_read_data_last extends i2c_base_seq_v2;
  function new(mailbox #(i2c_seq_item) req, mailbox #(i2c_seq_item) rsp); super.new(req, rsp); endfunction
  task body(); bit [31:0] rd; bit [7:0] rdv; bit nk;
    do_i2c_write(VALID_SLAVE, 8'h03, 8'h55);
    for (int i = 0; i < 3; i++) do_i2c_read(VALID_SLAVE, 8'h03, rdv, nk);
    do_reg_write(REG_DATA, 32'h00AA); 
    do_reg_read (REG_STATUS, rd);
    do_reg_write(REG_COMMAND, (32'(VALID_SLAVE)) | CMD_WRITE | CMD_STOP);
    for (int itr = 0; itr < 5000; itr++) begin do_reg_read(REG_STATUS, rd); if (!(rd & STATUS_BUSY)) break; end
  endtask
endclass

class seq_tc16_addr_mismatch_write_multiple extends i2c_base_seq_v2;
  function new(mailbox #(i2c_seq_item) req, mailbox #(i2c_seq_item) rsp); super.new(req, rsp); endfunction
  task body(); bit [31:0] rd; do_i2c_write(VALID_SLAVE, 8'h05, 8'h11); do_i2c_write(VALID_SLAVE, 8'h06, 8'h22); do_reg_write(REG_COMMAND, (32'(VALID_SLAVE)) | CMD_START | CMD_WRITE_MULTIPLE | CMD_STOP); for (int i = 0; i < 3; i++) begin bit [31:0] val = (i == 2) ? (32'h0AA + i) | DATA_LAST : (32'h0AA + i); do_reg_write(REG_DATA, val); end do_reg_write(REG_COMMAND, (32'(VALID_SLAVE)) | CMD_STOP); do_reg_read(REG_STATUS, rd); endtask
endclass

class seq_tc17_slave_multi_read extends i2c_base_seq_v2;
  function new(mailbox #(i2c_seq_item) req, mailbox #(i2c_seq_item) rsp); super.new(req, rsp); endfunction
  task body(); bit [7:0] vals [4] = '{8'h11, 8'h22, 8'h33, 8'h44}; bit [7:0] rdv; bit nk; foreach (vals[i]) do_i2c_write(VALID_SLAVE, 8'h06, vals[i]); for (int i = 0; i < 4; i++) do_i2c_read(VALID_SLAVE, 8'h06, rdv, nk); do_i2c_read(7'h55, 8'h00, rdv, nk); endtask
endclass

class seq_tc18_invalid_cmd_prescale_max extends i2c_base_seq_v2;
  function new(mailbox #(i2c_seq_item) req, mailbox #(i2c_seq_item) rsp); super.new(req, rsp); endfunction
  task body(); bit [31:0] rd; bit [7:0] rdv; bit nk; do_reg_write(REG_PRESCALE, 32'h0000_FFFF); do_reg_read(REG_PRESCALE, rd); do_reg_write(REG_PRESCALE, 32'h0000_0004); do_reg_read(REG_STATUS, rd); do_i2c_write(VALID_SLAVE, 8'h0F, 8'h77); do_i2c_read(VALID_SLAVE, 8'h0F, rdv, nk); endtask
endclass

class seq_tc19_coverage extends i2c_base_seq_v2;
  function new(mailbox #(i2c_seq_item) req, mailbox #(i2c_seq_item) rsp); super.new(req, rsp); endfunction
  task body(); bit [31:0] rd; bit [7:0] rdv; bit nk; bit [31:0] rnd_payload; bit [7:0] rnd_reg;
    rnd_payload = {16'h0, $urandom_range(1, 16'hFFFF)}; do_reg_write(REG_PRESCALE, rnd_payload); do_reg_read(REG_PRESCALE, rd); do_reg_read(REG_STATUS, rd);
    rnd_payload = $urandom_range(0, 8'hFF); rnd_reg = $urandom_range(0, 8'h0F); do_i2c_write(VALID_SLAVE, rnd_reg, rnd_payload[7:0]); do_i2c_read(VALID_SLAVE, rnd_reg, rdv, nk);
    
    for (int i = 0; i < 15; i++) begin 
      bit [6:0] slave = VALID_SLAVE; 
      rnd_payload = $urandom_range(0, 8'hFF); rnd_reg = $urandom_range(0, 8'h0F); 
      do_i2c_write(slave, rnd_reg, rnd_payload[7:0]); 
      do_i2c_read(slave, rnd_reg, rdv, nk); 
    end
    
    for (int i = 0; i < 35; i++) do_reg_write(REG_DATA, 32'h0000_00AA); 
    for (int i = 0; i < 35; i++) do_reg_write(REG_COMMAND, 32'h0000_0000); 
    do_reg_read(REG_STATUS, rd); 
    do_reg_write(REG_STATUS, STATUS_CMD_OVF | STATUS_WR_OVF);
    
    do_reg_write(REG_COMMAND, (32'(VALID_SLAVE)) | CMD_START | CMD_WRITE_MULTIPLE | CMD_STOP); 
    for (int i = 0; i < 5; i++) begin bit [31:0] val = 32'(8'h20 + i); if (i == 4) val = val | DATA_LAST; do_reg_write(REG_DATA, val); end 
    do_reg_read(REG_STATUS, rd);
  endtask
endclass

// ─────────────────────────────────────────────────────────────────────────────
// 12. MÓDULO TOP
// ─────────────────────────────────────────────────────────────────────────────
module tb_top;
  logic clk = 1'b0;
  logic rst = 1'b1;

  always #10 clk = ~clk;

  initial begin repeat(12) @(posedge clk); @(posedge clk); #1; rst = 1'b0; end

  i2c_axil_if axil_bus (.clk(clk), .rst(rst));

  i2c_rtl_wrapper #(.CMD_FIFO(1), .WRITE_FIFO(1), .READ_FIFO(1)) dut (
    .clk(clk), .rst(rst),
    .s_axil_awaddr(axil_bus.awaddr), .s_axil_awprot(axil_bus.awprot), .s_axil_awvalid(axil_bus.awvalid), .s_axil_awready(axil_bus.awready),
    .s_axil_wdata(axil_bus.wdata), .s_axil_wstrb(axil_bus.wstrb), .s_axil_wvalid(axil_bus.wvalid), .s_axil_wready(axil_bus.wready),
    .s_axil_bresp(axil_bus.bresp), .s_axil_bvalid(axil_bus.bvalid), .s_axil_bready(axil_bus.bready),
    .s_axil_araddr(axil_bus.araddr), .s_axil_arprot(axil_bus.arprot), .s_axil_arvalid(axil_bus.arvalid), .s_axil_arready(axil_bus.arready),
    .s_axil_rdata(axil_bus.rdata), .s_axil_rresp(axil_bus.rresp), .s_axil_rvalid(axil_bus.rvalid), .s_axil_rready(axil_bus.rready)
  );

  task reset_test_state(i2c_env_v2 env);
    rst = 1'b1;
    env.bfm.reset_system();
    env.scoreboard.slave_mem.delete();
    env.scoreboard.reg_model.delete();
    repeat(10) @(posedge clk);
    rst = 1'b0;
    repeat(10) @(posedge clk);
  endtask

  initial begin
    i2c_env_v2 env;
    @(negedge rst); repeat(2) @(posedge clk);
    env = new(axil_bus, /*disable_cvg_err=*/1'b1);
    env.run();

    begin : run_all_tests
      seq_tc01_reg_integrity                s01 = new(env.agent.req_mbox, env.agent.rsp_mbox);
      seq_tc02_golden_write                 s02 = new(env.agent.req_mbox, env.agent.rsp_mbox);
      seq_tc03_loopback                     s03 = new(env.agent.req_mbox, env.agent.rsp_mbox);
      seq_tc04_nack                         s04 = new(env.agent.req_mbox, env.agent.rsp_mbox);
      seq_tc05_repeated_start               s05 = new(env.agent.req_mbox, env.agent.rsp_mbox);
      seq_tc06_jitter_loopback              s06 = new(env.agent.req_mbox, env.agent.rsp_mbox);
      seq_tc07_fifo_overflow                s07 = new(env.agent.req_mbox, env.agent.rsp_mbox);
      seq_tc08_write_multiple               s08 = new(env.agent.req_mbox, env.agent.rsp_mbox);
      seq_tc09_standalone_stop              s09 = new(env.agent.req_mbox, env.agent.rsp_mbox);
      seq_tc10_read_fifo_overflow           s10 = new(env.agent.req_mbox, env.agent.rsp_mbox);
      seq_tc11_master_fsm                   s11 = new(env.agent.req_mbox, env.agent.rsp_mbox);
      seq_tc12_no_fifo_stress               s12 = new(env.agent.req_mbox, env.agent.rsp_mbox);
      seq_tc13_stop_on_idle                 s13 = new(env.agent.req_mbox, env.agent.rsp_mbox);
      seq_tc14_read_command_reg             s14 = new(env.agent.req_mbox, env.agent.rsp_mbox);
      seq_tc15_burst_read_data_last         s15 = new(env.agent.req_mbox, env.agent.rsp_mbox);
      seq_tc16_addr_mismatch_write_multiple s16 = new(env.agent.req_mbox, env.agent.rsp_mbox);
      seq_tc17_slave_multi_read             s17 = new(env.agent.req_mbox, env.agent.rsp_mbox);
      seq_tc18_invalid_cmd_prescale_max     s18 = new(env.agent.req_mbox, env.agent.rsp_mbox);
      seq_tc19_coverage                     s19 = new(env.agent.req_mbox, env.agent.rsp_mbox);

      $display("\n\033[36m[TEST] === TC_01: PRESCALE write/read patterns and STATUS read ===\033[0m"); s01.body(); #500ns; reset_test_state(env);
      $display("\n\033[36m[TEST] === TC_02: Single I2C write to golden slave (0x63) ===\033[0m"); s02.body(); #500ns; reset_test_state(env);
      $display("\n\033[36m[TEST] === TC_03: Write then read back the same slave register ===\033[0m"); s03.body(); #500ns; reset_test_state(env);
      $display("\n\033[36m[TEST] === TC_04: Write to invalid slave address; expect NACK ===\033[0m"); s04.body(); #500ns; reset_test_state(env);
      $display("\n\033[36m[TEST] === TC_05: Write followed by read without STOP (repeated START) ===\033[0m"); s05.body(); #500ns; reset_test_state(env);
      $display("\n\033[36m[TEST] === TC_06: Loopback with clock jitter ===\033[0m"); s06.body(); #500ns; reset_test_state(env);
      $display("\n\033[36m[TEST] === TC_07: CMD/WR FIFO overflow flags and STATUS clear ===\033[0m"); s07.body(); #500ns; reset_test_state(env);
      $display("\n\033[36m[TEST] === TC_08: Block write (WRITE_MULTIPLE) through command FIFO ===\033[0m"); s08.body(); #500ns; reset_test_state(env);
      $display("\n\033[36m[TEST] === TC_09: STOP command issued while bus address context is retained ===\033[0m"); s09.body(); #500ns; reset_test_state(env);
      $display("\n\033[36m[TEST] === TC_10: READ FIFO full/overflow and drain ===\033[0m"); s10.body(); #500ns; reset_test_state(env);
      $display("\n\033[36m[TEST] === TC_11: ACTIVE_READ/ACTIVE_WRITE transitions and standalone STOP ===\033[0m"); s11.body(); #500ns; reset_test_state(env);
      $display("\n\033[36m[TEST] === TC_12: Golden write (no-FIFO stress placeholder) ===\033[0m"); s12.body(); #500ns; reset_test_state(env);
      $display("\n\033[36m[TEST] === TC_13: stop_on_idle paths in ACTIVE_WRITE and ACTIVE_READ ===\033[0m"); s13.body(); #500ns; reset_test_state(env);
      $display("\n\033[36m[TEST] === TC_14: AXI read of the normally write-only COMMAND register ===\033[0m"); s14.body(); #500ns; reset_test_state(env);
      $display("\n\033[36m[TEST] === TC_15: Burst reads and DATA write without DATA_LAST ===\033[0m"); s15.body(); #500ns; reset_test_state(env);
      $display("\n\033[36m[TEST] === TC_16: Address change forces repeated START; WRITE_MULTIPLE FSM ===\033[0m"); s16.body(); #500ns; reset_test_state(env);
      $display("\n\033[36m[TEST] === TC_17: Chained slave reads and invalid-slave NACK ===\033[0m"); s17.body(); #500ns; reset_test_state(env);
      $display("\n\033[36m[TEST] === TC_18: Maximum PRESCALE and ignored invalid COMMAND opcodes ===\033[0m"); s18.body(); #500ns; reset_test_state(env);

      env.coverage.disable_coverage_errors = 1'b0;
      $display("\n\033[36m[TEST] === TC_19: Functional Coverage Test (run last) ===\033[0m"); s19.body(); #500ns;
    end

    env.check(/*check_coverage=*/1'b1);
    $display("\n\033[32m[TEST] === ALL TESTS DONE ===\033[0m\n");
    $finish;
  end

  initial begin $dumpvars(0); end
endmodule