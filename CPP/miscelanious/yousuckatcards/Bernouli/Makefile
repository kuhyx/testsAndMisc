CXX := g++
CXXFLAGS := -O2 -Wall -Wextra -std=c++17
LDFLAGS :=

BINS := bernouli test

all: $(BINS)

bernouli: bernouli.cpp
	$(CXX) $(CXXFLAGS) -o $@ $^ $(LDFLAGS)

test: test.cpp
	$(CXX) $(CXXFLAGS) -o $@ $^ $(LDFLAGS)

run: all
	./bernouli
	./test

clean:
	rm -f $(BINS)

.PHONY: all run clean
