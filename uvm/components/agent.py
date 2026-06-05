# -----------------------------------------------------------------------------
# Copyright (c) 2026 Universidade Federal de São Carlos. Todos os direitos reservados.
# -----------------------------------------------------------------------------
# NOME DO ARQUIVO      : agent.py
# -----------------------------------------------------------------------------
from pyuvm import *
from .driver import Driver
from .monitor import Monitor

class Agent(uvm_agent):
    def build_phase(self):
        self.seqr    = uvm_sequencer.create("seqr", self)
        self.driver  = Driver.create("driver", self)
        self.monitor = Monitor.create("monitor", self)

    def connect_phase(self):
        self.driver.seq_item_port.connect(self.seqr.seq_item_export)
        self.driver_ap = self.driver.ap
        self.driver_ap.connect(self.monitor.analysis_export)
        self.monitor_ap = self.monitor.ap