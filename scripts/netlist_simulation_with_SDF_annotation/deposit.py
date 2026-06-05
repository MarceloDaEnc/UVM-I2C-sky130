import re
import sys

def generate_deposit_commands_by_instance(file_path):
    deposits = []

    with open(file_path, 'r') as f:
        lines = f.readlines()

    for line in lines:
        match = re.search(r'sky130_fd_sc_hd__(df[rx]tp)_\d+\s+(\S+)\s*\(', line)
        if match:
            instance_name = match.group(2).strip()
            deposits.append(f"$deposit(i2c_master_inst.{instance_name}.Q, 1'b0);")

    return deposits

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Uso: {sys.argv[0]} <netlist.v>")
        sys.exit(1)

    zap_file = sys.argv[1]

    deposit_cmds = generate_deposit_commands_by_instance(zap_file)

    print("// ---- Gerado automaticamente para uso na testbench ----")
    print("initial begin")
    for cmd in deposit_cmds:
        print(f"    {cmd}")
    print("end")