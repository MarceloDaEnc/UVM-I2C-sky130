verilator --binary --timing --trace -Wno-fatal \
  -Wno-BADSTDPRAGMA -Wno-WIDTHTRUNC -Wno-WIDTHEXPAND -Wno-TIMESCALEMOD \
  -Wno-PINMISSING -Wno-IMPLICIT -Wno-SELRANGE -Wno-CASEINCOMPLETE \
  --top-module tb_top \
  -I../../rtl \
  tb_i2c_uvm.sv ../wrapper/i2c_rtl_wrapper.v

./obj_dir/Vtb_top +UVM_TESTNAME=test_all_tests