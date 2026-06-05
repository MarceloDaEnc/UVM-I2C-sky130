#!/bin/bash
# Script de Instalação: Ferramentas EDA Open-Source Isoladas (v3)
set -e

# ==========================================
# 1. CONFIGURAÇÕES DO WORKSPACE
# ==========================================
WORKSPACE_DIR="$HOME/eda_workspace"
TOOLS_DIR="$WORKSPACE_DIR/tools"
SRC_DIR="$WORKSPACE_DIR/src"
VENV_DIR="$WORKSPACE_DIR/venv"
CORES=$(nproc)

echo ">>> Preparando o ambiente em: $WORKSPACE_DIR"
mkdir -p "$TOOLS_DIR" "$SRC_DIR"

# ==========================================
# 2. DEPENDÊNCIAS DO SISTEMA (Requer Sudo)
# ==========================================
echo ">>> Verificando dependências de compilação e LCOV..."
sudo apt-get update
sudo apt-get install -y build-essential git flex bison gperf autoconf \
    clang cmake curl libreadline-dev libsqlite3-dev libbz2-dev \
    libssl-dev zlib1g-dev libffi-dev liblzma-dev help2man lcov

# ==========================================
# 3. INSTALAÇÃO DO DOCKER
# ==========================================
echo ">>> Verificando instalação do Docker..."
if ! command -v docker &> /dev/null; then
    echo ">>> Instalando Docker..."
    curl -fsSL https://get.docker.com -o "$SRC_DIR/get-docker.sh"
    sudo sh "$SRC_DIR/get-docker.sh"
    sudo usermod -aG docker "$USER"
    echo "AVISO: Lembre-se de reiniciar a sessão após a instalação para usar o Docker."
else
    echo ">>> Docker já está instalado."
fi

# ==========================================
# 4. PYTHON 3.12.4
# ==========================================
echo ">>> Verificando Python 3.12.4..."
cd "$SRC_DIR"
if [ ! -d "$TOOLS_DIR/python-3.12.4" ]; then
    curl -O https://www.python.org/ftp/python/3.12.4/Python-3.12.4.tgz
    tar -xzf Python-3.12.4.tgz
    cd Python-3.12.4
    ./configure --prefix="$TOOLS_DIR/python-3.12.4" --enable-optimizations
    make -j"$CORES"
    make install
else
    echo ">>> Python 3.12.4 já instalado."
fi

if [ ! -d "$VENV_DIR" ]; then
    echo ">>> Criando Ambiente Virtual (venv)..."
    "$TOOLS_DIR/python-3.12.4/bin/python3" -m venv "$VENV_DIR"
fi

# ==========================================
# 5. ICARUS VERILOG
# ==========================================
echo ">>> Verificando Icarus Verilog..."
cd "$SRC_DIR"
if [ ! -d "$TOOLS_DIR/iverilog/bin" ]; then
    if [ ! -d "iverilog" ]; then
        git clone https://github.com/steveicarus/iverilog.git
    fi
    cd iverilog
    git pull
    sh autoconf.sh
    ./configure --prefix="$TOOLS_DIR/iverilog"
    make -j"$CORES"
    make install
else
    echo ">>> Icarus Verilog já instalado."
fi

# ==========================================
# 6. VERILATOR
# ==========================================
echo ">>> Verificando Verilator..."
cd "$SRC_DIR"
if [ ! -d "$TOOLS_DIR/verilator/bin" ]; then
    if [ ! -d "verilator" ]; then
        git clone https://github.com/verilator/verilator.git
    fi
    cd verilator
    git pull
    git checkout stable
    autoconf
    ./configure --prefix="$TOOLS_DIR/verilator"
    make -j"$CORES"
    make install
else
    echo ">>> Verilator já instalado."
fi

# ==========================================
# 7. FERRAMENTAS PYTHON (Isoladas)
# ==========================================
echo ">>> Instalando pacotes Python no venv isolado..."
source "$VENV_DIR/bin/activate"

pip install --upgrade pip
pip install cocotb pyuvm

echo ">>> Instalando LibreLane e ciel a partir dos novos repositórios oficiais..."
# URLs corrigidas sem a Efabless
pip install git+https://github.com/librelane/librelane.git
pip install git+https://github.com/fossi-foundation/ciel.git

deactivate

# ==========================================
# 8. SCRIPT DE ATIVAÇÃO
# ==========================================
ACTIVATE_SCRIPT="$WORKSPACE_DIR/activate_eda.sh"
cat << 'EOF' > "$ACTIVATE_SCRIPT"
#!/bin/bash

WORKSPACE_DIR="$HOME/eda_workspace"

export PATH="$WORKSPACE_DIR/tools/iverilog/bin:$WORKSPACE_DIR/tools/verilator/bin:$PATH"
source "$WORKSPACE_DIR/venv/bin/activate"

echo "---------------------------------------------------"
echo "🛠️ Ambiente EDA Isolado Ativado com Sucesso! 🛠️"
python --version
iverilog -V | head -n 1
verilator --version
lcov --version
echo "---------------------------------------------------"
EOF

chmod +x "$ACTIVATE_SCRIPT"

echo ">>> Instalação/Atualização Concluída com Sucesso!"