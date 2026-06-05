# -----------------------------------------------------------------------------
# Copyright (c) 2026 Universidade Federal de São Carlos. Todos os direitos reservados.
# -----------------------------------------------------------------------------
# NOME DO ARQUIVO      : env.py
# -----------------------------------------------------------------------------
from pyuvm import *
from .agent import Agent
from .scoreboard import Scoreboard
from .coverage import Coverage

class Env(uvm_env):
    def build_phase(self):
        self.agent      = Agent.create("agent", self)
        self.coverage   = Coverage.create("coverage", self)
        self.scoreboard = Scoreboard.create("scoreboard", self)

    def connect_phase(self):
        ConfigDB().set(None, "*", "SEQR", self.agent.seqr)
        self.agent.driver_ap.connect(self.coverage.analysis_export)
        self.agent.monitor_ap.connect(self.scoreboard.cmd_export)