# -----------------------------------------------------------------------------
# Copyright (c) 2026 Universidade Federal de São Carlos. Todos os direitos reservados.
# -----------------------------------------------------------------------------
# NOME DO ARQUIVO      : monitor.py
# -----------------------------------------------------------------------------
from pyuvm import *

class Monitor(uvm_subscriber):
    def build_phase(self):
        super().build_phase() 
        self.ap = uvm_analysis_port("ap", self)

    def write(self, item):
        self.ap.write(item)