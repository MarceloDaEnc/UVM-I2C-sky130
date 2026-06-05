# -----------------------------------------------------------------------------
# Copyright (c) 2026 Universidade Federal de São Carlos. Todos os direitos reservados.
# -----------------------------------------------------------------------------
# NOME DO ARQUIVO      : seq.py
# PROPÓSITO  : Sequências UVM (pyuvm) para testes direcionados e I2cCoverageSeq.
# -----------------------------------------------------------------------------
import random
from pyuvm import uvm_sequence
from .seq_item import I2cSeqItem
from .defs import CmdType, VALID_SLAVE_ADDR, RegAddr, CMD_WRITE_MULTIPLE, CMD_START, CMD_WRITE, CMD_STOP, DATA_LAST, CMD_READ

# ---------------------------------------------------------------------------
# TC01 – Integridade do registrador PRESCALE (único reg R/W "seguro")
#   Escreve padrão e lê de volta. Lê STATUS como sanidade.
#   Nota: COMMAND e DATA não são testados com escrita arbitrária aqui
#   porque escrever em COMMAND dispara transações I2C.
# ---------------------------------------------------------------------------
class I2cRegIntegritySeq(uvm_sequence):
    async def body(self):
        # PRESCALE: registrador R/W puro, não dispara HW
        for pattern in [0x0000_00FF, 0x0000_AABB, 0x0000_0001]:
            w = I2cSeqItem("w_prescale", cmd_type=CmdType.REG_WRITE,
                           reg_addr=int(RegAddr.PRESCALE), payload=pattern)
            await self.start_item(w); await self.finish_item(w)

            r = I2cSeqItem("r_prescale", cmd_type=CmdType.REG_READ,
                           reg_addr=int(RegAddr.PRESCALE))
            await self.start_item(r); await self.finish_item(r)

        # STATUS: somente leitura
        r_st = I2cSeqItem("r_status", cmd_type=CmdType.REG_READ,
                          reg_addr=int(RegAddr.STATUS))
        await self.start_item(r_st); await self.finish_item(r_st)


# ---------------------------------------------------------------------------
# TC02 – Escrita I2C no slave válido (0x63)
# ---------------------------------------------------------------------------
class I2cGoldenWriteSeq(uvm_sequence):
    async def body(self):
        item = I2cSeqItem("tc02", cmd_type=CmdType.I2C_WRITE,
                          slave_addr=VALID_SLAVE_ADDR, reg_addr=0x05,
                          payload=0xBE)
        await self.start_item(item); await self.finish_item(item)


# ---------------------------------------------------------------------------
# TC03 – Loopback: escreve e lê de volta do slave válido
# ---------------------------------------------------------------------------
class I2cLoopbackSeq(uvm_sequence):
    async def body(self):
        w = I2cSeqItem("tc03_w", cmd_type=CmdType.I2C_WRITE,
                       slave_addr=VALID_SLAVE_ADDR, reg_addr=0x05,
                       payload=0x42)
        await self.start_item(w); await self.finish_item(w)

        r = I2cSeqItem("tc03_r", cmd_type=CmdType.I2C_READ,
                       slave_addr=VALID_SLAVE_ADDR, reg_addr=0x05)
        await self.start_item(r); await self.finish_item(r)


# ---------------------------------------------------------------------------
# TC04 – Slave inválido → espera NACK (timeout no BFM)
# ---------------------------------------------------------------------------
class I2cNackSeq(uvm_sequence):
    async def body(self):
        item = I2cSeqItem("tc04", cmd_type=CmdType.I2C_WRITE,
                          slave_addr=0x11, reg_addr=0x00, payload=0xFF)
        await self.start_item(item); await self.finish_item(item)


# ---------------------------------------------------------------------------
# TC05 – Repeated Start: write→read no slave válido
# ---------------------------------------------------------------------------
class I2cRepeatedStartSeq(uvm_sequence):
    async def body(self):
        w = I2cSeqItem("tc05_w", cmd_type=CmdType.I2C_WRITE,
                       slave_addr=VALID_SLAVE_ADDR, reg_addr=0x07,
                       payload=0xA5)
        await self.start_item(w); await self.finish_item(w)

        r = I2cSeqItem("tc05_r", cmd_type=CmdType.I2C_READ,
                       slave_addr=VALID_SLAVE_ADDR, reg_addr=0x07)
        await self.start_item(r); await self.finish_item(r)


# ---------------------------------------------------------------------------
# TC07 – Cobertura aleatória completa
# ---------------------------------------------------------------------------
class I2cCoverageSeq(uvm_sequence):
    async def body(self):
        # Cobertura de PRESCALE (REG_WRITE + REG_READ)
        val = random.randint(1, 0xFFFF)
        w = I2cSeqItem("cov_w_presc", cmd_type=CmdType.REG_WRITE,
                       reg_addr=int(RegAddr.PRESCALE), payload=val)
        await self.start_item(w); await self.finish_item(w)

        r = I2cSeqItem("cov_r_presc", cmd_type=CmdType.REG_READ,
                       reg_addr=int(RegAddr.PRESCALE))
        await self.start_item(r); await self.finish_item(r)

        # STATUS read
        r_st = I2cSeqItem("cov_r_st", cmd_type=CmdType.REG_READ,
                          reg_addr=int(RegAddr.STATUS))
        await self.start_item(r_st); await self.finish_item(r_st)

        # Garante bins I2C: válido e inválido × write e read
        for slave in [VALID_SLAVE_ADDR, 0x11]:
            payload  = random.randint(0, 0xFF)
            reg_addr = random.randint(0x00, 0x0F)

            w = I2cSeqItem("cov_i2c_w", cmd_type=CmdType.I2C_WRITE,
                           slave_addr=slave, reg_addr=reg_addr,
                           payload=payload)
            await self.start_item(w); await self.finish_item(w)

            r = I2cSeqItem("cov_i2c_r", cmd_type=CmdType.I2C_READ,
                           slave_addr=slave, reg_addr=reg_addr)
            await self.start_item(r); await self.finish_item(r)

        # Transações aleatórias adicionais
        for _ in range(15):
            is_valid = random.random() < 0.7
            slave    = VALID_SLAVE_ADDR if is_valid else random.choice([0x11, 0x22, 0x7F])
            payload  = random.randint(0, 0xFF)
            reg_addr = random.randint(0x00, 0x0F)

            w = I2cSeqItem("rand_w", cmd_type=CmdType.I2C_WRITE,
                           slave_addr=slave, reg_addr=reg_addr,
                           payload=payload)
            await self.start_item(w); await self.finish_item(w)

            r = I2cSeqItem("rand_r", cmd_type=CmdType.I2C_READ,
                           slave_addr=slave, reg_addr=reg_addr)
            await self.start_item(r); await self.finish_item(r)

        # Bin FIFO_OVF — dispara overflow de CMD/WR e limpa via STATUS write
        fifo_ovf = I2cFifoOverflowSeq("cov_fifo_ovf")
        await fifo_ovf.start(self.sequencer)

        # Bin WRITE_MULT — envia bloco de bytes com CMD_WRITE_MULTIPLE
        write_mult = I2cWriteMultipleSeq("cov_write_mult")
        await write_mult.start(self.sequencer)

# ---------------------------------------------------------------------------
# TC07 – FIFO overflow: fill CMD/DATA FIFOs faster than the I2C engine drains them
# ---------------------------------------------------------------------------
class I2cFifoOverflowSeq(uvm_sequence):
    async def body(self):
        # Envia 35 bytes super rápido para a FIFO de dados
        for i in range(35):
            w = I2cSeqItem(f"ovf_data_{i}", cmd_type=CmdType.REG_WRITE,
                           reg_addr=int(RegAddr.DATA), payload=0xAA)
            await self.start_item(w); await self.finish_item(w)

        # Envia 35 comandos super rápido para a FIFO de comandos
        for i in range(35):
            w_cmd = I2cSeqItem(f"ovf_cmd_{i}", cmd_type=CmdType.REG_WRITE,
                               reg_addr=int(RegAddr.COMMAND), payload=0x00)
            await self.start_item(w_cmd); await self.finish_item(w_cmd)

        # Checa o STATUS (Deverá ter as flags WR_OVF e CMD_OVF ativadas)
        r = I2cSeqItem("r_stat_ovf", cmd_type=CmdType.REG_READ, reg_addr=int(RegAddr.STATUS))
        await self.start_item(r); await self.finish_item(r)

        # Clear Overflow Flags: Escrevendo 1 nos bits 10 (cmd_ovf) e 13 (wr_ovf)
        clear_val = (1 << 10) | (1 << 13)
        w_clr = I2cSeqItem("clr_ovf", cmd_type=CmdType.REG_WRITE,
                           reg_addr=int(RegAddr.STATUS), payload=clear_val)
        await self.start_item(w_clr); await self.finish_item(w_clr)

# ---------------------------------------------------------------------------
# TC09 – Write Multiple (Block Write)
# Testa a FSM de Múltiplos Bytes (STATE_WRITE_3) do Master
# ---------------------------------------------------------------------------
class I2cWriteMultipleSeq(uvm_sequence):
    async def body(self):
        # 1. Envia Comando de Início + Endereço do Registrador
        cmd1 = (VALID_SLAVE_ADDR & 0x7F) | CMD_START | CMD_WRITE
        w_cmd1 = I2cSeqItem("blk_cmd1", cmd_type=CmdType.REG_WRITE, reg_addr=int(RegAddr.COMMAND), payload=cmd1)
        await self.start_item(w_cmd1); await self.finish_item(w_cmd1)

        w_reg = I2cSeqItem("blk_reg", cmd_type=CmdType.REG_WRITE, reg_addr=int(RegAddr.DATA), payload=0x08)
        await self.start_item(w_reg); await self.finish_item(w_reg)

        # 2. Configura a FSM para WRITE MULTIPLE
        cmd_blk = (VALID_SLAVE_ADDR & 0x7F) | CMD_WRITE_MULTIPLE | CMD_STOP
        w_cmd2 = I2cSeqItem("blk_cmd2", cmd_type=CmdType.REG_WRITE, reg_addr=int(RegAddr.COMMAND), payload=cmd_blk)
        await self.start_item(w_cmd2); await self.finish_item(w_cmd2)

        # 3. Dispara uma rajada de 5 bytes (O último leva a flag DATA_LAST)
        for i in range(5):
            val = 0x10 + i
            if i == 4: 
                val |= DATA_LAST
            w_d = I2cSeqItem(f"blk_d{i}", cmd_type=CmdType.REG_WRITE, reg_addr=int(RegAddr.DATA), payload=val)
            await self.start_item(w_d); await self.finish_item(w_d)

        # 4. Aguarda a FSM digerir tudo
        r_st = I2cSeqItem("wait_idle", cmd_type=CmdType.REG_READ, reg_addr=int(RegAddr.STATUS))
        await self.start_item(r_st); await self.finish_item(r_st)

# ---------------------------------------------------------------------------
# TC10 – Standalone Stop & Error Recovery
# Força condições de interrupção soltas mantendo o endereço para evitar Repeated Start
# ---------------------------------------------------------------------------
class I2cStandaloneStopSeq(uvm_sequence):
    async def body(self):
        # Comando STOP isolado (Deve conter o endereço atual para não gerar Repeated Start!)
        cmd_stop = (VALID_SLAVE_ADDR & 0x7F) | CMD_STOP
        w_stop = I2cSeqItem("cmd_stop_only", cmd_type=CmdType.REG_WRITE, 
                            reg_addr=int(RegAddr.COMMAND), payload=cmd_stop)
        await self.start_item(w_stop); await self.finish_item(w_stop)
        
        r_st = I2cSeqItem("r_stat_err", cmd_type=CmdType.REG_READ, reg_addr=int(RegAddr.STATUS))
        await self.start_item(r_st); await self.finish_item(r_st)

# ---------------------------------------------------------------------------
# TC11 – Read FIFO Full & Overflow
# Dispara mais leituras do que a FIFO suporta para testar o limite do RX.
# ---------------------------------------------------------------------------
class I2cReadFifoOverflowSeq(uvm_sequence):
    async def body(self):
        # 1. Configura o ponteiro no slave
        cmd_w = (VALID_SLAVE_ADDR & 0x7F) | CMD_START | CMD_WRITE
        w_cmd1 = I2cSeqItem("rd_ovf_c1", cmd_type=CmdType.REG_WRITE, reg_addr=int(RegAddr.COMMAND), payload=cmd_w)
        await self.start_item(w_cmd1); await self.finish_item(w_cmd1)
        
        w_reg = I2cSeqItem("rd_ovf_reg", cmd_type=CmdType.REG_WRITE, reg_addr=int(RegAddr.DATA), payload=0x00 | DATA_LAST)
        await self.start_item(w_reg); await self.finish_item(w_reg)

        # 2. Envia 35 comandos de leitura consecutivos super rápidos (A FIFO só cabe 32)
        for i in range(35):
            cmd = (VALID_SLAVE_ADDR & 0x7F) | CMD_READ
            if i == 0: cmd |= CMD_START
            if i == 34: cmd |= CMD_STOP
            w_cmd = I2cSeqItem(f"rd_ovf_req_{i}", cmd_type=CmdType.REG_WRITE, reg_addr=int(RegAddr.COMMAND), payload=cmd)
            await self.start_item(w_cmd); await self.finish_item(w_cmd)

        # 3. Lê o STATUS esperando ver flags de FULL
        r_st = I2cSeqItem("r_st_rd_full", cmd_type=CmdType.REG_READ, reg_addr=int(RegAddr.STATUS))
        await self.start_item(r_st); await self.finish_item(r_st)

        # 4. Esvazia a FIFO de leitura para não quebrar testes futuros
        for i in range(32): # Só conseguimos ler os 32 que cabem!
            r_d = I2cSeqItem(f"rd_ovf_pop_{i}", cmd_type=CmdType.REG_READ, reg_addr=int(RegAddr.DATA))
            await self.start_item(r_d); await self.finish_item(r_d)

# ---------------------------------------------------------------------------
# TC11 – Master FSM: ACTIVE_READ/WRITE hand-off and standalone STOP
# ---------------------------------------------------------------------------
class I2cMasterFsmSeq(uvm_sequence):
    async def body(self):

        async def wait_for_idle():
            for _ in range(5000):
                r_st = I2cSeqItem("poll", cmd_type=CmdType.REG_READ, reg_addr=int(RegAddr.STATUS))
                await self.start_item(r_st); await self.finish_item(r_st)
                if not (r_st.read_data & 1):
                    break

        # Scene 1: ACTIVE_READ then direction change (write without STOP)
        cmd_w = (VALID_SLAVE_ADDR & 0x7F) | CMD_START | CMD_WRITE
        w_cmd1 = I2cSeqItem("adv_c1", cmd_type=CmdType.REG_WRITE, reg_addr=int(RegAddr.COMMAND), payload=cmd_w)
        await self.start_item(w_cmd1); await self.finish_item(w_cmd1)
        
        w_reg = I2cSeqItem("adv_d1", cmd_type=CmdType.REG_WRITE, reg_addr=int(RegAddr.DATA), payload=0x05 | DATA_LAST)
        await self.start_item(w_reg); await self.finish_item(w_reg)

        # Inicia Leitura SEM STOP (Master entra e trava em STATE_ACTIVE_READ)
        cmd_r1 = (VALID_SLAVE_ADDR & 0x7F) | CMD_START | CMD_READ
        w_cmd2 = I2cSeqItem("adv_c2", cmd_type=CmdType.REG_WRITE, reg_addr=int(RegAddr.COMMAND), payload=cmd_r1)
        await self.start_item(w_cmd2); await self.finish_item(w_cmd2)
        
        # Pop read FIFO so the master does not stall
        r_d1 = I2cSeqItem("adv_rd1", cmd_type=CmdType.REG_READ, reg_addr=int(RegAddr.DATA))
        await self.start_item(r_d1); await self.finish_item(r_d1)

        # Issue WRITE while still in ACTIVE_READ (repeated-start style)
        cmd_w_rs = (VALID_SLAVE_ADDR & 0x7F) | CMD_WRITE
        w_cmd_rs = I2cSeqItem("adv_c_rs", cmd_type=CmdType.REG_WRITE, reg_addr=int(RegAddr.COMMAND), payload=cmd_w_rs)
        await self.start_item(w_cmd_rs); await self.finish_item(w_cmd_rs)
        w_d_rs = I2cSeqItem("adv_d_rs", cmd_type=CmdType.REG_WRITE, reg_addr=int(RegAddr.DATA), payload=0x99 | DATA_LAST)
        await self.start_item(w_d_rs); await self.finish_item(w_d_rs)

        # Finaliza com STOP isolado
        w_cmd_stop = I2cSeqItem("adv_c_stop", cmd_type=CmdType.REG_WRITE, reg_addr=int(RegAddr.COMMAND), payload=(VALID_SLAVE_ADDR & 0x7F) | CMD_STOP)
        await self.start_item(w_cmd_stop); await self.finish_item(w_cmd_stop)

        await wait_for_idle()

        # Scene 2: ACTIVE_WRITE followed by standalone STOP
        w_cmd5 = I2cSeqItem("adv_c5", cmd_type=CmdType.REG_WRITE, reg_addr=int(RegAddr.COMMAND), payload=cmd_w)
        await self.start_item(w_cmd5); await self.finish_item(w_cmd5)
        w_reg2 = I2cSeqItem("adv_d2", cmd_type=CmdType.REG_WRITE, reg_addr=int(RegAddr.DATA), payload=0x10 | DATA_LAST)
        await self.start_item(w_reg2); await self.finish_item(w_reg2)

        w_cmd6 = I2cSeqItem("adv_c6", cmd_type=CmdType.REG_WRITE, reg_addr=int(RegAddr.COMMAND), payload=(VALID_SLAVE_ADDR & 0x7F) | CMD_STOP)
        await self.start_item(w_cmd6); await self.finish_item(w_cmd6)

        await wait_for_idle()


# ---------------------------------------------------------------------------
# TC14 – STATE_START_WAIT: Garante que o master espera o barramento ficar
#         livre antes de iniciar. Requer dois mestres competindo ou um slave
#         ativo. Aqui fazemos write→write em slave diferente para forçar
#         o branch bus_active → STATE_START_WAIT via prescale baixo.
#         Também cobre: STATE_ACTIVE_WRITE → stop_on_idle path (linha 401-402)
#         e stop_on_idle na STATE_ACTIVE_READ (linhas 457-460).
# ---------------------------------------------------------------------------
class I2cStopOnIdleSeq(uvm_sequence):
    """Ativa stop_on_idle via PRESCALE=0 e encadeia comandos para cobrir
    as transições STATE_ACTIVE_WRITE→IDLE e STATE_ACTIVE_READ→STOP via idle."""
    async def body(self):
        from .defs import STATUS_BUSY, RegAddr

        # 1. Escreve prescale=0 para que o master fique rápido no barramento
        w_presc = I2cSeqItem("presc0", cmd_type=CmdType.REG_WRITE,
                             reg_addr=int(RegAddr.PRESCALE), payload=0x0001)
        await self.start_item(w_presc); await self.finish_item(w_presc)

        # 2. Escrita I2C normal para o slave válido
        w = I2cSeqItem("tc14_w", cmd_type=CmdType.I2C_WRITE,
                       slave_addr=VALID_SLAVE_ADDR, reg_addr=0x01, payload=0xAB)
        await self.start_item(w); await self.finish_item(w)

        # 3. Leitura imediata para ficar em STATE_ACTIVE_READ
        r = I2cSeqItem("tc14_r", cmd_type=CmdType.I2C_READ,
                       slave_addr=VALID_SLAVE_ADDR, reg_addr=0x01)
        await self.start_item(r); await self.finish_item(r)

        # 4. Segunda escrita no mesmo endereço e slave → STATE_ACTIVE_WRITE→WRITE
        #    (branch: address and mode match → STATE_WRITE_1 sem repeated start)
        w2 = I2cSeqItem("tc14_w2", cmd_type=CmdType.I2C_WRITE,
                        slave_addr=VALID_SLAVE_ADDR, reg_addr=0x01, payload=0xCD)
        await self.start_item(w2); await self.finish_item(w2)

        # 5. Lê status para checar ocupado
        r_st = I2cSeqItem("tc14_st", cmd_type=CmdType.REG_READ,
                          reg_addr=int(RegAddr.STATUS))
        await self.start_item(r_st); await self.finish_item(r_st)


# ---------------------------------------------------------------------------
# TC15 – Leitura do registrador COMMAND (addr 0x04) via AXI-Lite read
#         Cobre linhas 622-633 do i2c_master_axil.v (branch 4'h4 do read)
# ---------------------------------------------------------------------------
class I2cReadCommandRegSeq(uvm_sequence):
    """Faz uma leitura direta no registrador COMMAND (0x04), que normalmente
    é write-only. Isso ativa o case branch 4'h4 na lógica de leitura AXI."""
    async def body(self):
        from .defs import RegAddr

        # Escreve um comando válido (para que cmd_address_reg tenha valor)
        cmd_val = (VALID_SLAVE_ADDR & 0x7F) | CMD_START | CMD_WRITE
        w_cmd = I2cSeqItem("tc15_wcmd", cmd_type=CmdType.REG_WRITE,
                           reg_addr=int(RegAddr.COMMAND), payload=cmd_val)
        await self.start_item(w_cmd); await self.finish_item(w_cmd)

        # Lê o registrador COMMAND (endereço 0x04)
        r_cmd = I2cSeqItem("tc15_rcmd", cmd_type=CmdType.REG_READ,
                           reg_addr=int(RegAddr.COMMAND))
        await self.start_item(r_cmd); await self.finish_item(r_cmd)

        # Também lê o registrador DATA (0x08) com out-ready para cobrir
        # o branch data_out_ready no read path
        r_data = I2cSeqItem("tc15_rdata", cmd_type=CmdType.REG_READ,
                            reg_addr=int(RegAddr.DATA))
        await self.start_item(r_data); await self.finish_item(r_data)


# ---------------------------------------------------------------------------
# TC16 – data_in_last_next = 1'b0: escreve no registrador DATA com
#         wstrb[1]=0 (escrita de 8 bits). O BFM usa wstrb=0xF por padrão,
#         então aqui enviamos via REG_WRITE com payload sem bit 9 setado.
#         Cobre linha 576 do i2c_master_axil.v.
#         Também cobre múltiplas leituras consecutivas do slave (STATE_READ_1
#         com clock stretching no i2c_slave.v linha 391-392) via burst read.
# ---------------------------------------------------------------------------
class I2cBurstReadDataLastSeq(uvm_sequence):
    """Leituras repetidas do mesmo reg + escrita DATA sem DATA_LAST.
    O slave I2C guarda apenas um valor por endereço; usamos o mesmo
    reg_addr para todas as operações, evitando falsos negativos no
    scoreboard. Cobre: múltiplos ciclos em STATE_READ (bit_count>0),
    STATE_ACTIVE_READ aguardando novo comando, e wstrb byte-only path."""
    async def body(self):
        from .defs import RegAddr

        # Escreve um valor no slave
        w = I2cSeqItem("tc16_w", cmd_type=CmdType.I2C_WRITE,
                       slave_addr=VALID_SLAVE_ADDR, reg_addr=0x03, payload=0x55)
        await self.start_item(w); await self.finish_item(w)

        # Lê três vezes o mesmo registrador (exercita STATE_ACTIVE_READ sem stop)
        for i in range(3):
            r = I2cSeqItem(f"tc16_r{i}", cmd_type=CmdType.I2C_READ,
                           slave_addr=VALID_SLAVE_ADDR, reg_addr=0x03)
            await self.start_item(r); await self.finish_item(r)

        # Escrita no DATA sem DATA_LAST (payload sem bit 9) — cobre linha 576
        w_data_no_last = I2cSeqItem("tc16_data_nolast", cmd_type=CmdType.REG_WRITE,
                                    reg_addr=int(RegAddr.DATA), payload=0xAA)
        await self.start_item(w_data_no_last); await self.finish_item(w_data_no_last)

        r_st = I2cSeqItem("tc16_st", cmd_type=CmdType.REG_READ,
                          reg_addr=int(RegAddr.STATUS))
        await self.start_item(r_st); await self.finish_item(r_st)

class I2cAddressMismatchWriteMultipleSeq(uvm_sequence):
    """Cobre:
    1) STATE_ACTIVE_WRITE com endereço diferente → repeated start (linha 382)
    2) STATE_WRITE_3 → STATE_WRITE_1 (write_multiple, não é último byte - linha 554)
    3) IDLE → bus_active → STATE_START_WAIT (linha 347) via write concorrente
    """
    async def body(self):
        from .defs import RegAddr

        # 1. Primeiro write para o slave válido (entra em ACTIVE_WRITE)
        w1 = I2cSeqItem("tc17_w1", cmd_type=CmdType.I2C_WRITE,
                        slave_addr=VALID_SLAVE_ADDR, reg_addr=0x05, payload=0x11)
        await self.start_item(w1); await self.finish_item(w1)

        # 2. Write para endereço DIFERENTE (força repeated start - branch linha 382)
        w2 = I2cSeqItem("tc17_w2", cmd_type=CmdType.I2C_WRITE,
                        slave_addr=VALID_SLAVE_ADDR, reg_addr=0x06, payload=0x22)
        await self.start_item(w2); await self.finish_item(w2)

        # 3. Write Multiple com 3 bytes (cobre STATE_WRITE_3 → WRITE_1 duas vezes)
        cmd_blk = (VALID_SLAVE_ADDR & 0x7F) | CMD_START | CMD_WRITE_MULTIPLE | CMD_STOP
        w_cmd = I2cSeqItem("tc17_wm_cmd", cmd_type=CmdType.REG_WRITE,
                           reg_addr=int(RegAddr.COMMAND), payload=cmd_blk)
        await self.start_item(w_cmd); await self.finish_item(w_cmd)

        # Bytes intermediários (não-last → STATE_WRITE_3 → STATE_WRITE_1)
        for i, val in enumerate([0xAA, 0xBB, 0xCC | DATA_LAST]):
            w_d = I2cSeqItem(f"tc17_wd{i}", cmd_type=CmdType.REG_WRITE,
                             reg_addr=int(RegAddr.DATA), payload=val)
            await self.start_item(w_d); await self.finish_item(w_d)

        # 4. Stop imediato na ACTIVE_WRITE sem write/read (linhas 392-393)
        cmd_stop_only = (VALID_SLAVE_ADDR & 0x7F) | CMD_STOP
        w_stop = I2cSeqItem("tc17_stop", cmd_type=CmdType.REG_WRITE,
                            reg_addr=int(RegAddr.COMMAND), payload=cmd_stop_only)
        await self.start_item(w_stop); await self.finish_item(w_stop)

        r_st = I2cSeqItem("tc17_st", cmd_type=CmdType.REG_READ,
                          reg_addr=int(RegAddr.STATUS))
        await self.start_item(r_st); await self.finish_item(r_st)


# ---------------------------------------------------------------------------
# TC18 – Slave como Transmissor: força o slave a enviar múltiplos bytes
#         para cobrir STATE_READ_1 (clock stretch), READ_2, READ_3→NACK
#         e READ_3→ACK→READ_1 no i2c_slave.v (linhas 391-392, 424-429)
# ---------------------------------------------------------------------------
class I2cSlaveMultiReadSeq(uvm_sequence):
    """Escreve e lê repetidamente o mesmo reg para exercitar o slave
    no ciclo STATE_READ_3→ACK→READ_1 (linhas 424-429 i2c_slave.v).
    Usar sempre o mesmo reg_addr mantém o espelho do scoreboard consistente."""
    async def body(self):
        from .defs import RegAddr

        # Escreve 4 vezes valores diferentes no mesmo registrador
        # O scoreboard guardará apenas o último (0x44), ok.
        for val in [0x11, 0x22, 0x33, 0x44]:
            w = I2cSeqItem(f"tc18_w_{val}", cmd_type=CmdType.I2C_WRITE,
                           slave_addr=VALID_SLAVE_ADDR, reg_addr=0x06, payload=val)
            await self.start_item(w); await self.finish_item(w)

        # Lê 4 vezes o mesmo reg — slave responderá com o último valor escrito (0x44)
        for i in range(4):
            r = I2cSeqItem(f"tc18_r_{i}", cmd_type=CmdType.I2C_READ,
                           slave_addr=VALID_SLAVE_ADDR, reg_addr=0x06)
            await self.start_item(r); await self.finish_item(r)

        # Leitura de slave inválido para cobrir path NACK no slave
        r_inv = I2cSeqItem("tc18_r_inv", cmd_type=CmdType.I2C_READ,
                           slave_addr=0x55, reg_addr=0x00)
        await self.start_item(r_inv); await self.finish_item(r_inv)

class I2cInvalidCmdPrescaleMaxSeq(uvm_sequence):
    """Testa prescale máximo e um comando inválido (sem start/read/write/stop)
    que deve ser ignorado silenciosamente pela FSM (branch 'invalid - ignore')."""
    async def body(self):
        from .defs import RegAddr

        # Prescale máximo (0xFFFF)
        w_presc = I2cSeqItem("tc19_presc_max", cmd_type=CmdType.REG_WRITE,
                             reg_addr=int(RegAddr.PRESCALE), payload=0xFFFF)
        await self.start_item(w_presc); await self.finish_item(w_presc)

        r_presc = I2cSeqItem("tc19_r_presc", cmd_type=CmdType.REG_READ,
                             reg_addr=int(RegAddr.PRESCALE))
        await self.start_item(r_presc); await self.finish_item(r_presc)

        # Repõe prescale para valor funcional
        w_presc2 = I2cSeqItem("tc19_presc_ok", cmd_type=CmdType.REG_WRITE,
                              reg_addr=int(RegAddr.PRESCALE), payload=0x0004)
        await self.start_item(w_presc2); await self.finish_item(w_presc2)

        # Comando inválido: apenas o endereço sem nenhum bit de operação
        # (cmd_read=0, cmd_write=0, cmd_write_multiple=0, cmd_stop=0)
        cmd_invalid = (VALID_SLAVE_ADDR & 0x7F)  # somente endereço
        w_inv_cmd = I2cSeqItem("tc19_inv_cmd", cmd_type=CmdType.REG_WRITE,
                               reg_addr=int(RegAddr.COMMAND), payload=cmd_invalid)
        await self.start_item(w_inv_cmd); await self.finish_item(w_inv_cmd)

        r_st = I2cSeqItem("tc19_st", cmd_type=CmdType.REG_READ,
                          reg_addr=int(RegAddr.STATUS))
        await self.start_item(r_st); await self.finish_item(r_st)

        # Uma operação normal para checar que o DUT não travou
        w = I2cSeqItem("tc19_w_ok", cmd_type=CmdType.I2C_WRITE,
                       slave_addr=VALID_SLAVE_ADDR, reg_addr=0x0F, payload=0x77)
        await self.start_item(w); await self.finish_item(w)

        r = I2cSeqItem("tc19_r_ok", cmd_type=CmdType.I2C_READ,
                       slave_addr=VALID_SLAVE_ADDR, reg_addr=0x0F)
        await self.start_item(r); await self.finish_item(r)