CC := gcc
CFLAGS := -O2 -Wall -Wextra -std=c11
LDFLAGS :=

SRC := main.c split.c
BIN := split

TEST_SRC := test_split.c split.c
TEST_BIN := test_split

COV_CFLAGS := -Wall -Wextra -std=c11 --coverage -g -O0
COV_LDFLAGS := -lm

all: $(BIN)

$(BIN): $(SRC)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

run: $(BIN)
	./$(BIN)

test: $(TEST_BIN)
	./$(TEST_BIN)

$(TEST_BIN): $(TEST_SRC)
	$(CC) $(CFLAGS) -o $@ $^ -lm

coverage:
	$(CC) $(COV_CFLAGS) -o $(TEST_BIN) $(TEST_SRC) $(COV_LDFLAGS)
	./$(TEST_BIN)
	lcov --capture --directory . --output-file coverage.info --rc branch_coverage=1
	lcov --remove coverage.info '/usr/*' --output-file coverage.info \
		--rc branch_coverage=1 --ignore-errors unused
	@LINE_PCT=$$(lcov --summary coverage.info 2>&1 | grep -oP 'lines\.*:\s*\K[0-9.]+'); \
	echo "Line coverage: $${LINE_PCT}%"; \
	if [ "$$(echo "$${LINE_PCT} < 100.0" | bc -l)" = "1" ]; then \
		echo "FAIL: Line coverage $${LINE_PCT}% is below 100%"; \
		exit 1; \
	else \
		echo "OK: 100% line coverage achieved"; \
	fi

clean:
	rm -f $(BIN) $(TEST_BIN) *.gcda *.gcno *.gcov coverage.info
	rm -rf coverage_html

.PHONY: all run test coverage clean
