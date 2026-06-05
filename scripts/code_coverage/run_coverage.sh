#!/bin/bash

echo "Iniciando simulação Verilator (cobertura)!"

echo " " # Imprime uma linha em branco

make -f Makefile clean

echo " " # Imprime uma linha em branco

make -f Makefile

echo " " # Imprime uma linha em branco

verilator_coverage --write-info ./sim_build/coverage.info coverage.dat

echo " " # Imprime uma linha em branco

genhtml --branch-coverage -o ./relatorio_de_cobertura/ ./sim_build/coverage.info

echo " " # Imprime uma linha em branco

echo "Script finalizado."