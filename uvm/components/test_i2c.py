# -----------------------------------------------------------------------------
# Copyright (c) 2026 Universidade Federal de São Carlos. Todos os direitos reservados.
# -----------------------------------------------------------------------------
# NOME DO ARQUIVO: test_i2c.py
# AUTOR          : Marcelo Rodrigues Soares
# EMAIL DO AUTOR : marcelo.soares@ufscar.br
# -----------------------------------------------------------------------------
# OBJETIVO : Testes de nível superior cocotb/pyuvm para o wrapper I2C master + slave.
#
#   BaseI2cTest      — Desabilita a falha de cobertura funcional (scoreboard ativo).
#   I2cCoverageTest  — Teste PRIMÁRIO de verificação; deve rodar por ÚLTIMO. Exercita todos os
#                      bins de cobertura funcional e verifica 100% de conclusão.
#
# DUT: i2c_rtl_wrapper (i2c_master_axil + i2c_slave no barramento SCL/SDA wired-open)
#   Host: AXI4-Lite (s_axil_*) conduzido pelo Bfm/Driver
#   Bus:  i2c_scl / i2c_sda entre os modelos master e slave
#   clk   — 50 MHz (20 ns)
#   rst   — síncrono, ativo em ALTO
# -----------------------------------------------------------------------------

import cocotb
import pyuvm
from pyuvm import *
from cocotb.triggers import Timer

from .env import Env
from .bfm import Bfm
from .seq import *


async def _run_test_flow(test_obj, seq_class, jitter_clock=False):
    """Inicia o clock/reset, roda *seq_class* no sequencer, e então finaliza (drains)."""
    bfm = Bfm()
    clock_task = cocotb.start_soon(bfm.clock(period_ns=20, jitter=jitter_clock))
    await bfm.reset_system()

    seqr = ConfigDB().get(test_obj, "", "SEQR")
    seq = seq_class.create("test_sequence")
    await seq.start(seqr)
    await Timer(500, unit="ns")
    clock_task.cancel()


class BaseI2cTest(uvm_test):
    """Classe base para testes direcionados; erros de cobertura funcional são suprimidos."""

    def build_phase(self):
        ConfigDB().set(None, "*", "DISABLE_COVERAGE_ERRORS", True)
        self.env = Env.create("env", self)


# ---------------------------------------------------------------------------
# Testes direcionados (rodar antes de I2cCoverageTest)
# ---------------------------------------------------------------------------

@pyuvm.test()
class I2cRegIntegrityTest(BaseI2cTest):
    """TC_01 — Padrões de escrita/leitura de PRESCALE e leitura de STATUS."""

    async def run_phase(self):
        self.raise_objection()
        await _run_test_flow(self, I2cRegIntegritySeq)
        self.drop_objection()


@pyuvm.test()
class I2cGoldenWriteTest(BaseI2cTest):
    """TC_02 — Única escrita I2C para o slave golden (0x63)."""

    async def run_phase(self):
        self.raise_objection()
        await _run_test_flow(self, I2cGoldenWriteSeq)
        self.drop_objection()


@pyuvm.test()
class I2cLoopbackTest(BaseI2cTest):
    """TC_03 — Escreve e depois lê de volta o mesmo registrador do slave."""

    async def run_phase(self):
        self.raise_objection()
        await _run_test_flow(self, I2cLoopbackSeq)
        self.drop_objection()


@pyuvm.test()
class I2cNackTest(BaseI2cTest):
    """TC_04 — Escreve em um endereço de slave inválido; espera NACK."""

    async def run_phase(self):
        self.raise_objection()
        await _run_test_flow(self, I2cNackSeq)
        self.drop_objection()


@pyuvm.test()
class I2cRepeatedStartTest(BaseI2cTest):
    """TC_05 — Escrita seguida de leitura sem STOP (START repetido)."""

    async def run_phase(self):
        self.raise_objection()
        await _run_test_flow(self, I2cRepeatedStartSeq)
        self.drop_objection()


@pyuvm.test()
class I2cClockJitterLoopbackTest(BaseI2cTest):
    """TC_06 — Loopback com jitter de clock de ±1 ns no clock do host."""

    async def run_phase(self):
        self.raise_objection()
        await _run_test_flow(self, I2cLoopbackSeq, jitter_clock=True)
        self.drop_objection()


@pyuvm.test()
class I2cFifoOverflowTest(BaseI2cTest):
    """TC_07 — Flags de overflow da FIFO de CMD/WR e limpeza de STATUS."""

    async def run_phase(self):
        self.raise_objection()
        await _run_test_flow(self, I2cFifoOverflowSeq)
        self.drop_objection()


@pyuvm.test()
class I2cWriteMultipleTest(BaseI2cTest):
    """TC_08 — Escrita em bloco (WRITE_MULTIPLE) através da FIFO de comandos."""

    async def run_phase(self):
        self.raise_objection()
        await _run_test_flow(self, I2cWriteMultipleSeq)
        self.drop_objection()


@pyuvm.test()
class I2cStandaloneStopTest(BaseI2cTest):
    """TC_09 — Comando STOP emitido enquanto o contexto de endereço do barramento é retido."""

    async def run_phase(self):
        self.raise_objection()
        await _run_test_flow(self, I2cStandaloneStopSeq)
        self.drop_objection()


@pyuvm.test()
class I2cReadFifoOverflowTest(BaseI2cTest):
    """TC_10 — FIFO de leitura (READ) cheia/overflow e esvaziamento (drain)."""

    async def run_phase(self):
        self.raise_objection()
        await _run_test_flow(self, I2cReadFifoOverflowSeq)
        self.drop_objection()


@pyuvm.test()
class I2cMasterFsmTest(BaseI2cTest):
    """TC_11 — Transições ACTIVE_READ/ACTIVE_WRITE e STOP isolado."""

    async def run_phase(self):
        self.raise_objection()
        await _run_test_flow(self, I2cMasterFsmSeq)
        self.drop_objection()


@pyuvm.test()
class I2cNoFifoStressTest(BaseI2cTest):
    """TC_12 — Golden write (placeholder para build com FIFO CMD/WR/RD desabilitada)."""

    async def run_phase(self):
        self.raise_objection()
        await _run_test_flow(self, I2cGoldenWriteSeq)
        self.drop_objection()


@pyuvm.test()
class I2cStopOnIdleTest(BaseI2cTest):
    """TC_13 — Caminhos stop_on_idle em ACTIVE_WRITE e ACTIVE_READ."""

    async def run_phase(self):
        self.raise_objection()
        await _run_test_flow(self, I2cStopOnIdleSeq)
        self.drop_objection()


@pyuvm.test()
class I2cReadCommandRegTest(BaseI2cTest):
    """TC_14 — Leitura AXI do registrador COMMAND (normalmente somente-escrita)."""

    async def run_phase(self):
        self.raise_objection()
        await _run_test_flow(self, I2cReadCommandRegSeq)
        self.drop_objection()


@pyuvm.test()
class I2cBurstReadDataLastTest(BaseI2cTest):
    """TC_15 — Leituras em burst e escrita de DATA sem DATA_LAST (wstrb apenas para byte)."""

    async def run_phase(self):
        self.raise_objection()
        await _run_test_flow(self, I2cBurstReadDataLastSeq)
        self.drop_objection()


@pyuvm.test()
class I2cAddressMismatchWriteMultipleTest(BaseI2cTest):
    """TC_16 — Mudança de endereço força START repetido; FSM WRITE_MULTIPLE."""

    async def run_phase(self):
        self.raise_objection()
        await _run_test_flow(self, I2cAddressMismatchWriteMultipleSeq)
        self.drop_objection()


@pyuvm.test()
class I2cSlaveMultiReadTest(BaseI2cTest):
    """TC_17 — Leituras de slave encadeadas e NACK em slave inválido."""

    async def run_phase(self):
        self.raise_objection()
        await _run_test_flow(self, I2cSlaveMultiReadSeq)
        self.drop_objection()


@pyuvm.test()
class I2cInvalidCmdPrescaleMaxTest(BaseI2cTest):
    """TC_18 — PRESCALE máximo e opcodes COMMAND inválidos ignorados."""

    async def run_phase(self):
        self.raise_objection()
        await _run_test_flow(self, I2cInvalidCmdPrescaleMaxSeq)
        self.drop_objection()


# ---------------------------------------------------------------------------
# Teste final — cobertura funcional completa
# ---------------------------------------------------------------------------

@pyuvm.test()
class I2cCoverageTest(uvm_test):
    """
    TC_19 — Teste de Cobertura Funcional (rodar por último).

    Executa I2cCoverageSeq para atingir todos os bins de registradores e funcionais de I2C.
    A verificação de cobertura é habilitada; o teste falha se faltar algum bin.
    """

    def build_phase(self):
        ConfigDB().set(None, "*", "DISABLE_COVERAGE_ERRORS", False)
        self.env = Env.create("env", self)

    async def run_phase(self):
        self.raise_objection()
        await _run_test_flow(self, I2cCoverageSeq)
        self.drop_objection()