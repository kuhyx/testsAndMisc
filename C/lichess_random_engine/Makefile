CC := gcc
CFLAGS := -O2 -std=c11 -Wall -Wextra -Wno-unused-parameter
COV := -O0 -g --coverage -std=c11 -Wall -Wextra -Wno-unused-parameter -Wno-return-type
LDFLAGS :=

SRC := main.c movegen.c search.c
BIN := random_engine

# Perft driver
PERFT_SRC := perft.c movegen.c
PERFT_BIN := perft

.PHONY: all clean rebuild test coverage

all: $(BIN)

$(BIN): $(SRC)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

$(PERFT_BIN): $(PERFT_SRC)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

# ---- tests ------------------------------------------------------------------

test_movegen: test_movegen.c movegen.c movegen.h
	$(CC) $(COV) -o test_movegen test_movegen.c movegen.c

test_search: test_search.c search.c movegen.c movegen.h search.h
	$(CC) $(COV) -o test_search test_search.c search.c movegen.c

test: test_movegen test_search
	./test_movegen
	./test_search

# ---- coverage ---------------------------------------------------------------

coverage: test_movegen test_search
	./test_movegen
	./test_search
	lcov --capture --directory . --output-file coverage.info \
		--rc branch_coverage=1 --ignore-errors inconsistent,mismatch,unused
	lcov --extract coverage.info \
		"$(CURDIR)/movegen.c" "$(CURDIR)/search.c" \
		--output-file coverage.info \
		--ignore-errors unused,inconsistent
	@echo "--- Coverage Summary ---"
	lcov --summary coverage.info --rc branch_coverage=1 2>&1 | tee /tmp/lcov_engine_summary.txt
	@LINE_COV=$$(grep "lines" /tmp/lcov_engine_summary.txt | grep -oP '[0-9]+\.[0-9]+(?=%)'); \
	echo "Line coverage: $${LINE_COV}%"; \
	if [ "$$(echo "$${LINE_COV} < 100.0" | bc)" = "1" ]; then \
		echo "FAIL: line coverage below 100%"; exit 1; \
	fi
	@echo "OK: 100% line coverage achieved"

run: $(BIN)
	./$(BIN)

clean:
	rm -f $(BIN) $(PERFT_BIN) test_movegen test_search \
		*.gcda *.gcno *.gcov coverage.info

rebuild: clean all

.PHONY: perft
perft: $(PERFT_BIN)
