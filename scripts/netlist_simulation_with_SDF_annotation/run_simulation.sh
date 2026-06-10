make clean

cd ../../postlayout/sdf/

python3 ../../scripts/refactor/refactor.py ./nom_tt_025C_1v80/i2c_master_axil__nom_tt_025C_1v80.sdf

cd ../nl

python3 ../../scripts/refactor/refactor.py i2c_master_axil.nl.v

cd ../../scripts/netlist_simulation_with_SDF_annotation

make