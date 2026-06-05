# -----------------------------------------------------------------------------
# Copyright (c) 2026 Universidade Federal de São Carlos. Todos os direitos reservados.
# -----------------------------------------------------------------------------
# NOME DO ARQUIVO      : scoreboard.py
# PROPÓSITO  : Golden model para gravações em registros AXI e memória de escravos I2C.
# -----------------------------------------------------------------------------

import cocotb
from pyuvm import *
from .defs import CmdType, RegAddr, VALID_SLAVE_ADDR

_READ_ONLY_REGS = {int(RegAddr.STATUS), int(RegAddr.COMMAND), int(RegAddr.DATA)}


class Scoreboard(uvm_component):
    """Compares driver transactions against a software register/slave model."""

    def build_phase(self):
        self.cmd_fifo = uvm_tlm_analysis_fifo("cmd_fifo", self)
        self.cmd_get_port = uvm_get_port("cmd_get_port", self)
        self.cmd_export = self.cmd_fifo.analysis_export
        self.fail_count = 0
        self.pass_count = 0
        self.reg_model = {}
        self.slave_mem = {}

    def connect_phase(self):
        self.cmd_get_port.connect(self.cmd_fifo.get_export)

    async def run_phase(self):
        while True:
            item = await self.cmd_get_port.get()

            if item.cmd_type == CmdType.REG_WRITE:
                if item.reg_addr not in _READ_ONLY_REGS:
                    if item.reg_addr == int(RegAddr.PRESCALE):
                        self.reg_model[item.reg_addr] = item.payload & 0xFFFF
                    else:
                        self.reg_model[item.reg_addr] = item.payload
                    self.logger.info(
                        f"📝 REG_WRITE [0x{item.reg_addr:02X}] = 0x{item.payload:08X}"
                    )

            elif item.cmd_type == CmdType.REG_READ:
                if item.reg_addr in _READ_ONLY_REGS:
                    self.logger.info(
                        f"📈  STATUS read = 0x{item.read_data:08X} (volatile, no check)"
                    )
                elif item.reg_addr in self.reg_model:
                    exp = self.reg_model[item.reg_addr]
                    got = item.read_data
                    if item.reg_addr == int(RegAddr.PRESCALE):
                        exp &= 0xFFFF
                        got &= 0xFFFF
                    if got == exp:
                        self.pass_count += 1
                        self.logger.info(
                            f"✅ REG_READ [0x{item.reg_addr:02X}] PASS "
                            f"exp=0x{exp:X} got=0x{got:X}"
                        )
                    else:
                        self.fail_count += 1
                        self.logger.error(
                            f"❌ REG_READ [0x{item.reg_addr:02X}] FAIL "
                            f"exp=0x{exp:X} got=0x{got:X}"
                        )
                else:
                    self.logger.info(
                        f"REG_READ [0x{item.reg_addr:02X}] = 0x{item.read_data:08X} "
                        "(no reference)"
                    )

            elif item.cmd_type == CmdType.I2C_WRITE:
                if item.nack_seen:
                    if item.slave_addr == VALID_SLAVE_ADDR:
                        self.logger.error(
                            f"❌ Unexpected NACK on I2C_WRITE slave=0x{item.slave_addr:02X}"
                        )
                        self.fail_count += 1
                    else:
                        self.logger.info(
                            f"⚠️  Expected NACK on I2C_WRITE slave=0x{item.slave_addr:02X}"
                        )
                else:
                    self.slave_mem[item.slave_addr] = item.payload & 0xFF
                    self.pass_count += 1
                    self.logger.info(
                        f"✅ I2C_WRITE slave=0x{item.slave_addr:02X} "
                        f"reg=0x{item.reg_addr:02X} data=0x{item.payload & 0xFF:02X}"
                    )

            elif item.cmd_type == CmdType.I2C_READ:
                if item.nack_seen:
                    if item.slave_addr == VALID_SLAVE_ADDR:
                        self.logger.error(
                            f"❌ Unexpected NACK on I2C_READ slave=0x{item.slave_addr:02X}"
                        )
                        self.fail_count += 1
                    else:
                        self.logger.info(
                            f"⚠️  Expected NACK on I2C_READ slave=0x{item.slave_addr:02X}"
                        )
                elif item.slave_addr in self.slave_mem:
                    exp = self.slave_mem[item.slave_addr]
                    got = item.read_data & 0xFF
                    if got == exp:
                        self.pass_count += 1
                        self.logger.info(
                            f"✅ I2C_READ slave=0x{item.slave_addr:02X} "
                            f"PASS exp=0x{exp:02X} got=0x{got:02X}"
                        )
                    else:
                        self.fail_count += 1
                        self.logger.error(
                            f"❌ I2C_READ slave=0x{item.slave_addr:02X} "
                            f"FAIL exp=0x{exp:02X} got=0x{got:02X}"
                        )
                else:
                    self.logger.info(
                        f"I2C_READ slave=0x{item.slave_addr:02X} "
                        f"data=0x{item.read_data & 0xFF:02X} (no prior write)"
                    )

    def check_phase(self):
        if self.fail_count > 0:
            self.logger.error(
                f"❌ Scoreboard: {self.fail_count} failures, {self.pass_count} checks passed."
            )
            assert False, "Scoreboard reported mismatches."
        self.logger.info(
            f"✅ Scoreboard: all checks passed ({self.pass_count} verifications)."
        )