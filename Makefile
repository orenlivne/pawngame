# Build the parallel pawn-game solver / move server.
#   make        -> build src/cpp/pawnsolver_par
#   make test   -> run the Python test suite
#   make clean  -> remove built binaries
CXX      ?= clang++
CXXFLAGS := -O3 -std=c++17 -pthread
LDLIBS   :=

# On x86-64 Linux, lock-free 128-bit atomics need cmpxchg16b + libatomic.
# Apple Silicon has them natively, so no extra flags there.
UNAME_S := $(shell uname -s)
UNAME_M := $(shell uname -m)
ifeq ($(UNAME_S),Linux)
  ifneq ($(filter x86_64 amd64,$(UNAME_M)),)
    CXXFLAGS += -mcx16
    LDLIBS   += -latomic
  endif
endif

SRC := src/cpp/pawnsolver_par.cpp
BIN := src/cpp/pawnsolver_par

.PHONY: all test clean
all: $(BIN)

$(BIN): $(SRC)
	$(CXX) $(CXXFLAGS) -o $@ $< $(LDLIBS)

test:
	PYTHONPATH=src pytest -q

clean:
	rm -f $(BIN) src/cpp/pawnsolver_srv
