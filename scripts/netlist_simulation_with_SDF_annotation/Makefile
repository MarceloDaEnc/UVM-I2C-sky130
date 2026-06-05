# Makefile
export PYTHONPATH := $(CURDIR)/../../uvm/:$(CURDIR)/../../uvm/wrapper:$(PYTHONPATH)
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

VERILOG_SOURCES += 	$(CURDIR)/../../postlayout/nl/i2c_master_axil_nl_refactored.v \
					$(CURDIR)/../../rtl/i2c_slave.v \
					$(CURDIR)/../../uvm/wrapper/i2c_netlist_wrapper.v\
					$(CURDIR)/../../postlayout/tech/*.v

TOPLEVEL = i2c_netlist_wrapper
COCOTB_TEST_MODULES = components.test_i2c

# Compilation arguments for Icarus Verilog
COMPILE_ARGS += -gspecify -ginterconnect
COMPILE_ARGS += -DUNIT_DELAY=\#1 -DSKY130_FD_SC_HD__LPFLOW_BLEEDER_1_TIMING_V -DSDF_DELAYS

# Specify log file for simulation output
SIM_LOG_FILE = $(CURDIR)/testbench.log

# Enable VCD waveform dump
# export WAVES = 1

# Include Cocotb simulation rules
include $(shell cocotb-config --makefiles)/Makefile.sim