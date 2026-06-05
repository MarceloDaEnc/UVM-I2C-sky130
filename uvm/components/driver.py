# -----------------------------------------------------------------------------
# Copyright (c) 2026 Universidade Federal de São Carlos. Todos os direitos reservados.
# -----------------------------------------------------------------------------
# NOME DO ARQUIVO      : driver.py
# -----------------------------------------------------------------------------
from pyuvm import *
from .bfm import Bfm
from .defs import CmdType

class Driver(uvm_driver):
    def build_phase(self):
        self.ap = uvm_analysis_port("ap", self)

    def start_of_simulation_phase(self):
        self.bfm = Bfm()

    async def run_phase(self):
        while True:
            item = await self.seq_item_port.get_next_item()
            
            if item.cmd_type == CmdType.REG_WRITE:
                await self.bfm.write_register(item.reg_addr, item.payload)
            elif item.cmd_type == CmdType.REG_READ:
                item.read_data = await self.bfm.read_register(item.reg_addr)
            elif item.cmd_type == CmdType.I2C_WRITE:
                item.nack_seen = await self.bfm.execute_i2c_write(item.slave_addr, item.reg_addr, item.payload)
            elif item.cmd_type == CmdType.I2C_READ:
                data, nack = await self.bfm.execute_i2c_read(item.slave_addr, item.reg_addr)
                item.read_data = data
                item.nack_seen = nack

            self.ap.write(item)
            self.seq_item_port.item_done()