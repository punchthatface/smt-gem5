PREFIX := ${PARSECDIR}/pkgs/apps/swaptions/inst/${PARSECPLAT}
# PHASE2 PATCH:
# Enable gem5 m5ops so swaptions can emit work markers.
# The actual L1D cleanup is performed by gem5 when the runner sees those markers.
DEF = -DUSE_M5OPS
INCLUDE = -I/users/akim2/smt-gem5/gem5/include
LIBS = /users/akim2/smt-gem5/gem5/util/m5/build/x86/out/libm5.a
# PHASE2 PATCH:
# Match the working domain_switch_probe build style so gem5 m5ops are recognized.
# Static/non-PIE also avoids dynamic-loader noise in gem5 SE mode.
LDFLAGS := $(LDFLAGS) -static -no-pie
CXXFLAGS := $(CXXFLAGS) -no-pie

EXEC = swaptions 

ifdef version
  ifeq "$(version)" "pthreads" 
    DEF := $(DEF) -DENABLE_THREADS
    CXXFLAGS := $(CXXFLAGS) -pthread
  endif
  ifeq "$(version)" "tbb"
    DEF := $(DEF) -DENABLE_THREADS -DTBB_VERSION
    LIBS := $(LIBS) -ltbb
  endif
endif

OBJS= CumNormalInv.o MaxFunction.o RanUnif.o nr_routines.o icdf.o \
	HJM_SimPath_Forward_Blocking.o HJM.o HJM_Swaption_Blocking.o  \
	HJM_Securities.o

all: $(EXEC)

$(EXEC): $(OBJS)
	$(CXX) $(CXXFLAGS) $(LDFLAGS) $(DEF) $(OBJS) $(INCLUDE) $(LIBS) -o $(EXEC)

.cpp.o:
	$(CXX) $(CXXFLAGS) $(DEF) $(INCLUDE) -c $*.cpp -o $*.o

.c.o:
	$(CXX) $(CXXFLAGS) $(DEF) $(INCLUDE) -c $*.c -o $*.o

clean:
	rm -f $(OBJS) $(EXEC)

install:
	mkdir -p $(PREFIX)/bin
	cp -f $(EXEC) $(PREFIX)/bin/$(EXEC)

