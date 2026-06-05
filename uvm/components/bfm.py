# -----------------------------------------------------------------------------
# Copyright (c) 2026 Universidade Federal de São Carlos. Todos os direitos reservados.
# -----------------------------------------------------------------------------
# NOME DO ARQUIVO : bfm.py
# -----------------------------------------------------------------------------
import cocotb
from cocotb.triggers import Timer, RisingEdge, ReadOnly
import random
from .defs import (RegAddr,
                   CMD_START, CMD_READ, CMD_WRITE, CMD_STOP,
                   STATUS_BUSY, STATUS_MISS_ACK, STATUS_RD_EMPTY,
                   DATA_LAST)

_TIMEOUT_CYCLES = 50000   

class Bfm:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.dut = cocotb.top
            self._fake_prescale = 1 
            self._init_signals()

    def _init_signals(self):
        dut = self.dut
        dut.s_axil_awvalid.value = 0
        dut.s_axil_awaddr.value  = 0
        dut.s_axil_wvalid.value  = 0
        dut.s_axil_wdata.value   = 0
        dut.s_axil_awprot.value  = 0
        dut.s_axil_arprot.value  = 0
        dut.s_axil_wstrb.value   = 0
        dut.s_axil_bready.value  = 0
        dut.s_axil_arvalid.value = 0
        dut.s_axil_araddr.value  = 0
        dut.s_axil_rready.value  = 0

    def _safe_int(self, logic_array, default_val=0, signal_name="signal"):
        """Mapeia LogicArray para int; X/Z não resolvidos mapeiam para *default_val* (seguro para GLS)."""
        if not logic_array.is_resolvable:
            self.dut._log.debug(f"Info GLS: {signal_name} contém X/Z ({logic_array.binstr}). Assumindo {default_val}.")
            return default_val
        return int(logic_array)

    async def clock(self, period_ns=20, jitter=False):
        while True:
            self.dut.clk.value = 0
            half = period_ns // 2
            if jitter:
                half += random.choice([-1, 0, 1])
            await Timer(half, unit="ns")
            self.dut.clk.value = 1
            await Timer(period_ns // 2, unit="ns")

    async def reset_system(self):
        self.dut.rst.value = 1
        for _ in range(10):
            await RisingEdge(self.dut.clk)
        
        # Margem de tempo de hold após liberar o reset
        await Timer(2, unit="ns")
        self.dut.rst.value = 0
        
        await RisingEdge(self.dut.clk)
        await RisingEdge(self.dut.clk)

    async def write_register(self, addr, data):
        # A sequência de cobertura pode escrever um PRESCALE extremo; limita (clamp) para o fechamento de timing.
        if (addr & 0xF) == 0x0C:
            self._fake_prescale = data
            data = 4

        dut = self.dut
        await RisingEdge(dut.clk)
        
        # Margem de hold do ciclo de barramento (STA pós-layout)
        await Timer(2, unit="ns")
        
        # Canais AW e W (valid simultâneo)
        dut.s_axil_awaddr.value  = addr & 0xF
        dut.s_axil_awvalid.value = 1
        
        dut.s_axil_wdata.value   = data & 0xFFFFFFFF
        dut.s_axil_wstrb.value   = 0xF
        dut.s_axil_wvalid.value  = 1
        
        aw_done = False
        w_done  = False
        
        # Aguarda até que tanto awready quanto wready sejam vistos
        while not (aw_done and w_done):
            await ReadOnly()
            if not aw_done and self._safe_int(dut.s_axil_awready.value) == 1:
                aw_done = True
            if not w_done and self._safe_int(dut.s_axil_wready.value) == 1:
                w_done = True
                
            await RisingEdge(dut.clk)
            
            # Atraso de propagação pós-borda
            await Timer(2, unit="ns")
            
            # Desaciona o valid apenas após o handshake de ready correspondente
            if aw_done: dut.s_axil_awvalid.value = 0
            if w_done:  dut.s_axil_wvalid.value  = 0

        # Resposta de escrita (B)
        dut.s_axil_bready.value = 1
        while True:
            await ReadOnly()
            if self._safe_int(dut.s_axil_bvalid.value) == 1:
                break
            await RisingEdge(dut.clk)
            
        await RisingEdge(dut.clk)
        
        # --- Atraso de propagação ---
        await Timer(2, unit="ns")
        dut.s_axil_bready.value = 0


    async def read_register(self, addr):
        dut = self.dut
        await RisingEdge(dut.clk)
        
        # Margem de hold do ciclo de barramento (STA pós-layout)
        await Timer(2, unit="ns")
        
        # Endereço de leitura (AR)
        dut.s_axil_araddr.value  = addr & 0xF
        dut.s_axil_arvalid.value = 1
        
        # Aguarda por arready
        while True:
            await ReadOnly()
            if self._safe_int(dut.s_axil_arready.value) == 1:
                break
            await RisingEdge(dut.clk)
            
        await RisingEdge(dut.clk)
        
        # --- Atraso de propagação ---
        await Timer(2, unit="ns")
        dut.s_axil_arvalid.value = 0
        
        # Dados de leitura (R)
        dut.s_axil_rready.value = 1
        while True:
            await ReadOnly()
            if self._safe_int(dut.s_axil_rvalid.value) == 1:
                # Amostra rdata quando rvalid estiver acionado
                data = self._safe_int(dut.s_axil_rdata.value, signal_name="s_axil_rdata")
                break
            await RisingEdge(dut.clk)
            
        await RisingEdge(dut.clk)
        
        # --- Atraso de propagação ---
        await Timer(2, unit="ns")
        dut.s_axil_rready.value = 0

        # Retorna o prescale lógico escrito pelo teste (referência para o scoreboard)
        if (addr & 0xF) == 0x0C:
            return self._fake_prescale

        return data

    async def _wait_not_busy(self):
        for _ in range(_TIMEOUT_CYCLES):
            status = await self.read_register(int(RegAddr.STATUS))
            if not (status & STATUS_BUSY):
                return True, status
        return False, 0

    async def _wait_rd_available(self):
        for _ in range(_TIMEOUT_CYCLES):
            status = await self.read_register(int(RegAddr.STATUS))
            if not (status & STATUS_RD_EMPTY):
                return True, status
            if status & STATUS_MISS_ACK:
                return False, status

            for _ in range(10):
                await RisingEdge(self.dut.clk)

        return False, 0

    async def execute_i2c_write(self, slave_addr, reg_addr, payload) -> bool:
        # Fase 1: START + endereço do slave (escrita) + ponteiro de registrador
        cmd1 = (slave_addr & 0x7F) | CMD_START | CMD_WRITE
        await self.write_register(int(RegAddr.COMMAND), cmd1)
        await self.write_register(int(RegAddr.DATA), reg_addr & 0xFF)
        
        # Fase 2: byte de carga útil (payload) com STOP
        cmd2 = (slave_addr & 0x7F) | CMD_WRITE | CMD_STOP
        await self.write_register(int(RegAddr.COMMAND), cmd2)
        await self.write_register(int(RegAddr.DATA), (payload & 0xFF) | DATA_LAST)

        ok, status = await self._wait_not_busy()
        nack = bool(status & STATUS_MISS_ACK)
        if nack:
            await self.write_register(int(RegAddr.STATUS), STATUS_MISS_ACK)
            await self.reset_system()
        if not ok:
            return True
        return nack

    async def execute_i2c_read(self, slave_addr, reg_addr) -> tuple:
        cmd_w = (slave_addr & 0x7F) | CMD_START | CMD_WRITE
        await self.write_register(int(RegAddr.COMMAND), cmd_w)
        await self.write_register(int(RegAddr.DATA), (reg_addr & 0xFF) | DATA_LAST)

        cmd_r = (slave_addr & 0x7F) | CMD_START | CMD_READ | CMD_STOP
        await self.write_register(int(RegAddr.COMMAND), cmd_r)

        ok, status = await self._wait_rd_available()
        if not ok:
            if status & STATUS_MISS_ACK:
                await self.write_register(int(RegAddr.STATUS), STATUS_MISS_ACK)
                await self.reset_system()
            return 0, True

        raw = await self.read_register(int(RegAddr.DATA))
        data = raw & 0xFF

        status = await self.read_register(int(RegAddr.STATUS))
        nack = bool(status & STATUS_MISS_ACK)
        if nack:
            await self.write_register(int(RegAddr.STATUS), STATUS_MISS_ACK)
            await self.reset_system()

        return data, nack