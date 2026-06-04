CC := gcc
CFLAGS := -O2 -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Wno-unused-parameter
COV := -O0 -g --coverage -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Wno-unused-parameter -DATOP_AGG_NO_MAIN

SRC := atop_agg.c
HDR := atop_agg.h
BIN := atop_agg

.PHONY: all clean rebuild test coverage

all: $(BIN)

$(BIN): $(SRC) $(HDR)
	$(CC) $(CFLAGS) -o $@ $(SRC)

test_atop_agg: test_atop_agg.c atop_agg.c atop_agg.h
	$(CC) $(COV) -o test_atop_agg test_atop_agg.c atop_agg.c

test: test_atop_agg
	./test_atop_agg

coverage: test_atop_agg
	./test_atop_agg
	lcov --capture --directory . --output-file coverage.info --no-external
	lcov --remove coverage.info '*/test_atop_agg.c' --output-file coverage.info
	genhtml coverage.info --output-directory coverage_html
	@echo "Coverage report at coverage_html/index.html"

clean:
	rm -f $(BIN) test_atop_agg *.o *.gcda *.gcno coverage.info
	rm -rf coverage_html

rebuild: clean all
