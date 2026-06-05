# UVM-I2C-sky130

Ambiente de verificação funcional e pós-layout para um **controlador I2C mestre** com interface **AXI4-Lite**, implementado no PDK **sky130** da SkyWater Technology. O projeto combina uma infraestrutura UVM em Python (**pyuvm** + **cocotb**) com simuladores open-source e um fluxo de estimativa de consumo baseado em **LibreLane**.

O DUT de simulação são `i2c_rtl_wrapper` e `i2c_netlist_wrapper`: um mestre `i2c_master_axil` e um escravo `i2c_slave` conectados por barramento **wired-AND** em SCL/SDA, permitindo verificação ponta a ponta sem modelo externo de barramento.

---

## Índice

- [Visão Geral](#visão-geral)
- [Protocolo I2C](#protocolo-i2c)
- [Estrutura do Repositório](#estrutura-do-repositório)
- [Ambiente UVM](#ambiente-uvm)
- [Ferramentas Necessárias](#ferramentas-necessárias)
- [Como Executar](#como-executar)
- [Estimativa de Potência](#estimativa-de-potência)
- [Licença](#licença)

---

## Visão Geral

O repositório cobre o ciclo de verificação do IP I2C, desde a simulação RTL até a verificação pós-layout com anotação SDF, medição de cobertura de código e estimativa de potência com VCD real.

```
Host (AXI4-Lite)  ──►  i2c_master_axil  ──►  SCL/SDA  ──►  i2c_slave
                              │
RTL  ──►  Simulação RTL (Icarus + cocotb/pyuvm)
     ──►  Cobertura de Código (Verilator + lcov)
     ──►  P&R (Place and Route) (LibreLane + ciel sky130)
          └──►  Netlist  ──►  Simulação Pós-Layout (Icarus + SDF)
                         ──►  Estimativa de Potência (OpenSTA via LibreLane)
```

---

## Protocolo I2C

O **I2C** (Inter-Integrated Circuit) é um barramento serial síncrono de dois fios, muito usado para sensores, EEPROMs e PMICs em placas embarcadas.

### Sinais

| Sinal | Função |
|-------|--------|
| **SCL** | Clock gerado pelo **mestre**; os escravos amostram SDA na borda de subida (modo padrão). |
| **SDA** | Dados bidirecionais em **wired-AND** (open-drain): qualquer dispositivo só pode puxar para **0**; **1** é o estado de repouso com pull-ups externos. |

Neste repositório, mestre e escravo compartilham o mesmo par SCL/SDA no wrapper; conflitos são evitados pelo protocolo (apenas um transmissor ativo por vez).

### Formato de uma transação

1. **START** — O mestre puxa SDA de 1→0 enquanto SCL permanece em 1.
2. **Endereço + R/W** — 7 bits de endereço do escravo + 1 bit de direção (0 = escrita, 1 = leitura). O receptor responde com **ACK** (SDA=0) ou **NACK** (SDA=1).
3. **Dados** — Bytes MSB-first; cada byte seguido de ACK/NACK do receptor.
4. **STOP** — SDA sobe de 0→1 com SCL em 1, liberando o barramento.

**Repeated START** ocorre quando um novo START é emitido **sem** STOP intermediário — típico em “write do ponteiro de registrador + read dos dados” (como neste BFM de leitura).

### Relação com o DUT

O testbench não fala I2C diretamente: o host escreve em registradores **AXI4-Lite** do `i2c_master_axil`, que enfileira comandos e gera as formas de onda em SCL/SDA:

| Registrador | Endereço | Função resumida |
|-------------|----------|-----------------|
| **STATUS** | `0x00` | Busy, atividade no barramento, FIFOs, overflow, `miss_ack` |
| **COMMAND** | `0x04` | Endereço do escravo + bits START / READ / WRITE / WRITE_MULTIPLE / STOP |
| **DATA** | `0x08` | Byte de payload ou dado lido da FIFO RX |
| **PRESCALE** | `0x0C` | Divisor do clock I2C a partir do clock do sistema |

O escravo de teste (`i2c_slave`, endereço **0x63**) mantém um banco de registradores internos; o scoreboard UVM espelha a última escrita por endereço de escravo para checar leituras.

---

## Estrutura do Repositório

```
open-verification-UVM-sky130/
├── rtl/                          # RTL do mestre, escravo e FIFOs
│   ├── i2c_master_axil.v         # Mestre I2C + interface AXI4-Lite
│   ├── i2c_master.v              # Núcleo do mestre
│   ├── i2c_slave.v               # Escravo de referência
│   └── axis_fifo.v               # FIFOs internas
│
├── uvm/
│   ├── components/               # Ambiente UVM (pyuvm)
│   │   ├── defs.py               # Mapa de registradores e constantes I2C
│   │   ├── seq_item.py           # I2cSeqItem
│   │   ├── bfm.py                # Bus Functional Model (AXI + transações I2C)
│   │   ├── driver.py / monitor.py / agent.py
│   │   ├── scoreboard.py         # Modelo de referência
│   │   ├── coverage.py           # Cobertura funcional
│   │   ├── seq.py                # Sequências direcionadas + I2cCoverageSeq
│   │   ├── env.py
│   │   └── test_i2c.py           # Testes cocotb (I2cCoverageTest por último)
│   └── wrapper/
│       ├── i2c_rtl_wrapper.v     # Mestre + escravo no mesmo barramento
│       └── i2c_netlist_wrapper.v # Wrapper pós-layout
│
├── postlayout/                   # Artefatos LibreLane (GDS, NL, SDF, SPEF, …)
│
├── scripts/
│   ├── RTL_simulation/           # Makefile — simulação RTL
│   ├── code_coverage/            # Makefile — cobertura de código
│   ├── netlist_simulation_with_SDF_annotation/
│   └── power_estimation/
│
└── install_eda_stack.sh          # Instalação isolada das ferramentas EDA
```

---

## Ambiente UVM

Arquitetura UVM clássica implementada em Python com **pyuvm** e **cocotb**:

```
┌─────────────────────────────────────────────────────┐
│  Env                                                │
│  ┌──────────────────────────────────┐               │
│  │  Agent                           │               │
│  │  Sequencer ──► Driver ───────────┼──► Coverage   │
│  │                Monitor ──────────┼──► Scoreboard │
│  └──────────────────────────────────┘               │
└─────────────────────────────────────────────────────┘
```

| Componente   | Arquivo           | Responsabilidade |
|--------------|-------------------|------------------|
| `Bfm`        | `bfm.py`          | Handshake AXI4-Lite e transações I2C de alto nível |
| `Driver`     | `driver.py`       | Converte `I2cSeqItem` em chamadas ao BFM |
| `Monitor`    | `monitor.py`      | Repassa itens do driver ao scoreboard |
| `Scoreboard` | `scoreboard.py`   | Registradores PRESCALE e memória do escravo 0x63 |
| `Coverage`   | `coverage.py`     | Bins funcionais (registradores, I2C, FIFO, block write) |
| `Sequências`   | `seq.py`          | Testes direcionados + `I2cCoverageSeq` |

### Suite de testes (`test_i2c.py`)

| Classe | Descrição |
|--------|-----------|
| `I2cRegIntegrityTest` … `I2cInvalidCmdPrescaleMaxTest` | Testes direcionados (TC_01 … TC_18); cobertura funcional específica |
| **`I2cCoverageTest`** | **Teste final** — deve rodar por último; exige 100 % dos bins funcionais |

---

## Ferramentas Necessárias

A forma recomendada de instalar o stack completo é o script na raiz do repositório:

```bash
./install_eda_stack.sh
```

Isso cria `~/eda_workspace` com Python 3.12.4, Icarus Verilog, Verilator, cocotb, pyuvm, LibreLane e ciel.

### Ativar o ambiente

Após a instalação (ou em qualquer nova sessão de terminal), carregue as ferramentas com:

```bash
source ~/eda_workspace/activate_eda.sh
```

O script ajusta `PATH`, ativa o `venv` e exibe as versões de Python, Icarus e Verilator.

| Ferramenta | Uso no projeto |
|------------|----------------|
| **Icarus Verilog** | Simulação RTL e pós-layout |
| **Verilator** | Cobertura de código RTL |
| **cocotb / pyuvm** | Testbench UVM em Python |
| **LibreLane / ciel** | P&R sky130 e estimativa de potência |
| **Docker** | OpenSTA via container (potência) |

---

## Como Executar

> Execute os comandos após `source ~/eda_workspace/activate_eda.sh`, a partir da raiz do repositório ou do diretório indicado.

### 1. Simulação RTL

```bash
cd scripts/RTL_simulation
make
```

Resultados: `scripts/RTL_simulation/results.xml` e log em `sim_build/`.

### 2. Cobertura de Código

```bash
cd scripts/code_coverage
./run_coverage.sh
```

Relatório HTML: `scripts/code_coverage/relatorio_de_cobertura/index.html`.

### 3. Simulação Pós-Layout com SDF

```bash
cd scripts/netlist_simulation_with_SDF_annotation
./run_simulation.sh
```

O script refatora SDF/netlist e executa `make` com `-gspecify -ginterconnect -DSDF_DELAYS`.

### 4. Estimativa de Potência

```bash
cd scripts/power_estimation
./run_power_script.sh
```

**Pré-requisito:** gerar `dump.vcd` na simulação pós-layout (passo 3).

---

## Licença

Este projeto está licenciado conforme o arquivo [LICENSE](LICENSE). Módulos RTL derivados de projetos de terceiros mantêm os avisos de copyright nos respectivos arquivos `.v`.

---

*Desenvolvido na Universidade Federal de São Carlos (UFSCar) — Autor: Marcelo Rodrigues Soares*
