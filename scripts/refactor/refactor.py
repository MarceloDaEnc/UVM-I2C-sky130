import re
import sys
from argparse import ArgumentParser
from pathlib import Path

def clean_verilog_identifier(match):
    """
    Trata identificadores Verilog.
    Remove a contrabarra inicial e substitui ., [ e ] por _
    """
    word = match.group(1)
    return word.replace('.', '_').replace('[', '_').replace(']', '_')

def sanitize_content(target_path: Path, debug_mode: bool) -> None:
    if not target_path.is_file():
        sys.exit(f"Falha: O caminho '{target_path}' é inválido ou não existe.")

    raw_data = None
    for enc in ['utf-8', 'latin-1']:
        try:
            raw_data = target_path.read_text(encoding=enc)
            break
        except UnicodeDecodeError:
            continue

    if raw_data is None:
        sys.exit("Falha: Não foi possível decodificar o arquivo.")

    patterns = [
        (re.compile(r'\\(\S+)'), clean_verilog_identifier),
        (re.compile(r'\\\]\\\.'), '__'),
        (re.compile(r'\\\]'), '_'),
        (re.compile(r'\\\['), '_'),
        (re.compile(r'([a-zA-Z0-9])\\\.([a-zA-Z0-9])'), r'\1__\2')
    ]

    rows = raw_data.splitlines(keepends=True)
    modification_tally = 0
    final_buffer = []

    for row in rows:
        if '\\' not in row:
            final_buffer.append(row)
            continue

        mutated_row = row
        for pat, repl in patterns:
            mutated_row = pat.sub(repl, mutated_row)

        if mutated_row != row:
            modification_tally += 1
            if debug_mode:
                print(f"Modificação: {mutated_row.strip()}")

        final_buffer.append(mutated_row)

    dest_name = f"{target_path.stem.replace('.', '_')}_refactored{target_path.suffix}"
    dest_path = target_path.with_name(dest_name)

    dest_path.write_text("".join(final_buffer), encoding='utf-8')
    
    print(f"\nFinalizado com sucesso. Salvo em: {dest_path}")
    print(f"Linhas impactadas: {modification_tally}")

def run_cli():
    cli = ArgumentParser()
    cli.add_argument('file_loc')
    cli.add_argument('-d', '--debug', action='store_true')
    params = cli.parse_args()

    sanitize_content(Path(params.file_loc), params.debug)

if __name__ == '__main__':
    run_cli()