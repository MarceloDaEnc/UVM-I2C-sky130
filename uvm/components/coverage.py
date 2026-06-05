# -----------------------------------------------------------------------------
# Copyright (c) 2026 Universidade Federal de São Carlos. Todos os direitos reservados.
# -----------------------------------------------------------------------------
# NOME DO AEQUIVO      : coverage.py
# PROPÓSITO  : Cobertura funcional para o ambiente UVM I2C.
#
# Register bins: STATUS read, PRESCALE write/read.
# I2C bins: write/read × valid/invalid slave address.
# Feature bins: FIFO overflow clear, WRITE_MULTIPLE command.
# -----------------------------------------------------------------------------

from pyuvm import *
from .seq_item import I2cSeqItem
from .defs import (
    CmdType,
    VALID_SLAVE_ADDR,
    RegAddr,
    CMD_WRITE_MULTIPLE,
)

_EXPECTED_REGS = {
    (CmdType.REG_READ, int(RegAddr.STATUS)),
    (CmdType.REG_WRITE, int(RegAddr.PRESCALE)),
    (CmdType.REG_READ, int(RegAddr.PRESCALE)),
}

_EXPECTED_I2C = {
    (CmdType.I2C_WRITE, True),
    (CmdType.I2C_WRITE, False),
    (CmdType.I2C_READ, True),
    (CmdType.I2C_READ, False),
    ("FIFO_OVF", True),
    ("WRITE_MULT", True),
}


class Coverage(uvm_subscriber):
    """Records stimulus bins and asserts completeness in report_phase."""

    def end_of_elaboration_phase(self):
        self.cvg_regs = set()
        self.cvg_i2c = set()

    def write(self, item):
        if not isinstance(item, I2cSeqItem):
            return

        if item.cmd_type in (CmdType.REG_WRITE, CmdType.REG_READ):
            self.cvg_regs.add((item.cmd_type, item.reg_addr))
            if item.cmd_type == CmdType.REG_WRITE and item.reg_addr == int(RegAddr.STATUS):
                if item.payload & ((1 << 10) | (1 << 13)):
                    self.cvg_i2c.add(("FIFO_OVF", True))
            if item.cmd_type == CmdType.REG_WRITE and item.reg_addr == int(RegAddr.COMMAND):
                if item.payload & CMD_WRITE_MULTIPLE:
                    self.cvg_i2c.add(("WRITE_MULT", True))
        elif item.cmd_type in (CmdType.I2C_WRITE, CmdType.I2C_READ):
            is_valid = item.slave_addr == VALID_SLAVE_ADDR
            self.cvg_i2c.add((item.cmd_type, is_valid))

    def report_phase(self):
        try:
            disable_errors = ConfigDB().get(self, "", "DISABLE_COVERAGE_ERRORS")
        except UVMConfigItemNotFound:
            disable_errors = False

        reg_hits = len(self.cvg_regs & _EXPECTED_REGS)
        i2c_hits = len(self.cvg_i2c & _EXPECTED_I2C)
        total = len(_EXPECTED_REGS) + len(_EXPECTED_I2C)
        hits = reg_hits + i2c_hits
        missing_regs = _EXPECTED_REGS - self.cvg_regs
        missing_i2c = _EXPECTED_I2C - self.cvg_i2c

        self.logger.info(f"Coverage: {hits}/{total} bins hit.")

        if missing_regs or missing_i2c:
            self.logger.info(f"  Missing registers: {missing_regs or 'none'}")
            self.logger.info(f"  Missing I2C/features: {missing_i2c or 'none'}")

        if not disable_errors:
            if missing_regs or missing_i2c:
                assert False, "Functional coverage not fully achieved."
            self.logger.info("Functional coverage: all bins covered.")
