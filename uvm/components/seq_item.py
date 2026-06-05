# -----------------------------------------------------------------------------
# Copyright (c) 2026 Universidade Federal de São Carlos. Todos os direitos reservados.
# -----------------------------------------------------------------------------
# NOME DO ARQUIVO      : seq_item.py
# -----------------------------------------------------------------------------
from pyuvm import uvm_sequence_item
from .defs import CmdType, VALID_SLAVE_ADDR

class I2cSeqItem(uvm_sequence_item):
    def __init__(self, name, cmd_type=CmdType.I2C_WRITE, slave_addr=VALID_SLAVE_ADDR, reg_addr=0, payload=0):
        super().__init__(name)
        self.cmd_type   = cmd_type
        self.slave_addr = slave_addr & 0x7F
        self.reg_addr   = reg_addr & 0xFF
        self.payload    = payload & 0xFFFFFFFF
        
        self.read_data  = 0
        self.nack_seen  = False

    def __str__(self):
        cmd_str = self.cmd_type.name
        return (f"[{cmd_str}] Slave: 0x{self.slave_addr:02X} | "
                f"RegAddr: 0x{self.reg_addr:02X} | Payload: 0x{self.payload:08X} | "
                f"ReadData: 0x{self.read_data:08X} | NACK: {self.nack_seen}")