# -----------------------------------------------------------------------------
# Copyright (c) 2026 Universidade Federal de São Carlos. Todos os direitos reservados.
# -----------------------------------------------------------------------------
# NOME DO ARQUIVO      : defs.py
# PROPÓSITO  : Mapa de registradores, Status dos barramentos, e enumeração das sequências/coverbins.
# -----------------------------------------------------------------------------
from enum import IntEnum

CLK_HZ = 50_000_000
CLK_P  = 20 # ns

VALID_SLAVE_ADDR = 0x63

class CmdType(IntEnum):
    REG_WRITE = 0
    REG_READ  = 1
    I2C_WRITE = 2
    I2C_READ  = 3

class RegAddr(IntEnum):
    # Mapa real do i2c_master_axil.v (addr[3:0])
    STATUS   = 0x00  # R  - busy[0], bus_cont[1], bus_act[2], miss_ack[3],
                     #      cmd_empty[8], cmd_full[9], cmd_ovf[10],
                     #      wr_empty[11], wr_full[12], wr_ovf[13],
                     #      rd_empty[14], rd_full[15]
    COMMAND  = 0x04  # W  - cmd_address[6:0], cmd_start[8], cmd_read[9],
                     #      cmd_write[10], cmd_write_multiple[11], cmd_stop[12]
    DATA     = 0x08  # RW - data[7:0], data_valid[8](R), data_last[9](W)
    PRESCALE = 0x0C  # RW - prescale[15:0]

# Bits do registrador COMMAND (0x04)
CMD_START          = (1 << 8)
CMD_READ           = (1 << 9)
CMD_WRITE          = (1 << 10)
CMD_WRITE_MULTIPLE = (1 << 11)
CMD_STOP           = (1 << 12)

# Bits do registrador STATUS (0x00)
STATUS_BUSY       = (1 << 0)
STATUS_BUS_CONT   = (1 << 1)
STATUS_BUS_ACT    = (1 << 2)
STATUS_MISS_ACK   = (1 << 3)
STATUS_CMD_EMPTY  = (1 << 8)
STATUS_WR_EMPTY   = (1 << 11)
STATUS_RD_EMPTY   = (1 << 14)

# Bits do registrador DATA (0x08)
# Escrita: bit 9 = data_last (último byte de write_multiple)
# Leitura: bit 8 = data_valid (dado de leitura disponível), bit 9 = data_last
DATA_LAST  = (1 << 9)   # RTL: s_axil_wdata[9]  → data_in_last
DATA_VALID = (1 << 8)   # RTL: s_axil_rdata[8]  → data_out_valid

class I2cDir(IntEnum):
    WRITE = 0
    READ  = 1