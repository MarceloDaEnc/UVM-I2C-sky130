# -----------------------------------------------------------------------------
# Copyright (c) 2026 Universidade Federal de São Carlos. Todos os direitos reservados.
# -----------------------------------------------------------------------------
# NOME DO ARQUIVO      : __init__.py
# -----------------------------------------------------------------------------

from .defs       import (CLK_HZ, CLK_P, VALID_SLAVE_ADDR, CmdType, RegAddr, I2cDir,
                          CMD_START, CMD_READ, CMD_WRITE, CMD_WRITE_MULTIPLE, CMD_STOP,
                          STATUS_BUSY, STATUS_BUS_CONT, STATUS_BUS_ACT, STATUS_MISS_ACK,
                          STATUS_CMD_EMPTY, STATUS_WR_EMPTY, STATUS_RD_EMPTY,
                          DATA_LAST, DATA_VALID)
from .seq_item   import I2cSeqItem
from .bfm        import Bfm
from .driver     import Driver
from .monitor    import Monitor
from .scoreboard import Scoreboard
from .coverage   import Coverage
from .agent      import Agent
from .env        import Env
from .seq        import (
    I2cRegIntegritySeq,
    I2cGoldenWriteSeq,
    I2cLoopbackSeq,
    I2cNackSeq,
    I2cRepeatedStartSeq,
    I2cCoverageSeq,
    I2cFifoOverflowSeq,
    I2cWriteMultipleSeq,
    I2cStandaloneStopSeq,
    I2cReadFifoOverflowSeq,
    I2cMasterFsmSeq,
    I2cStopOnIdleSeq,
    I2cReadCommandRegSeq,
    I2cBurstReadDataLastSeq,
    I2cAddressMismatchWriteMultipleSeq,
    I2cSlaveMultiReadSeq,
    I2cInvalidCmdPrescaleMaxSeq,
)

__all__ = [
    "CLK_HZ", "CLK_P", "VALID_SLAVE_ADDR", "CmdType", "RegAddr", "I2cDir",
    "CMD_START", "CMD_READ", "CMD_WRITE", "CMD_WRITE_MULTIPLE", "CMD_STOP",
    "STATUS_BUSY", "STATUS_BUS_CONT", "STATUS_BUS_ACT", "STATUS_MISS_ACK",
    "STATUS_CMD_EMPTY", "STATUS_WR_EMPTY", "STATUS_RD_EMPTY", "DATA_LAST", "DATA_VALID",
    "I2cSeqItem", "Bfm", "Driver", "Monitor", "Scoreboard", "Coverage", "Agent", "Env",
    "I2cRegIntegritySeq", "I2cGoldenWriteSeq", "I2cLoopbackSeq",
    "I2cNackSeq", "I2cRepeatedStartSeq", "I2cCoverageSeq",
    "I2cFifoOverflowSeq", "I2cWriteMultipleSeq", "I2cStandaloneStopSeq",
    "I2cReadFifoOverflowSeq", "I2cMasterFsmSeq", "I2cStopOnIdleSeq",
    "I2cReadCommandRegSeq", "I2cBurstReadDataLastSeq",
    "I2cAddressMismatchWriteMultipleSeq", "I2cSlaveMultiReadSeq",
    "I2cInvalidCmdPrescaleMaxSeq",
]
