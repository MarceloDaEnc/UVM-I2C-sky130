export PYTHONPATH := $(CURDIR)/../../uvm/:$(CURDIR)/../../uvm/wrapper:$(PYTHONPATH)

SIM ?= verilator
TOPLEVEL_LANG ?= verilog

VERILOG_SOURCES +=  $(CURDIR)/../../rtl/*.v \
                    $(CURDIR)/../../uvm/wrapper/i2c_rtl_wrapper.v

TOPLEVEL = i2c_rtl_wrapper
COCOTB_TEST_MODULES = components.test_i2c

# Specify log file for simulation output
SIM_LOG_FILE = $(CURDIR)/testbench.log

# Enable VCD waveform dump
# export WAVES = 1

EXTRA_ARGS += --coverage --trace --trace-fst --trace-structs -Wno-fatal

# Include Cocotb simulation rules
include $(shell cocotb-config --makefiles)/Makefile.sim