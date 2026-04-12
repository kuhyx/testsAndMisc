#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "physics.h"

static void test_calculateVelocity(void)
{
    int   accel = 2;
    float v     = calculateVelocity(5.0f, 3, &accel);
    assert(fabsf(v - 11.0f) < 0.001f);

    /* acceleration=0: velocity unchanged */
    int   accel2 = 0;
    float v2     = calculateVelocity(10.0f, 5, &accel2);
    assert(fabsf(v2 - 10.0f) < 0.001f);

    int   accel3 = 0;
    float v3     = calculateVelocity(3.0f, 10, &accel3);
    assert(fabsf(v3 - 3.0f) < 0.001f);

    /* time=0: velocity equals starting velocity regardless of accel */
    int   accel4 = 100;
    float v4     = calculateVelocity(7.0f, 0, &accel4);
    assert(fabsf(v4 - 7.0f) < 0.001f);
}

static void test_calculateDisplacement(void)
{
    int accel = 2;
    int d     = calculateDisplacement(5.0f, &accel, 3);
    /* With integer division (1/2)==0, result is starting_velocity * time + 0 */
    assert(d == 15);

    int accel2 = 0;
    int d2     = calculateDisplacement(0.0f, &accel2, 10);
    assert(d2 == 0);
}

static void test_calculateStopTime(void)
{
    float t = calculateStopTime(2.0f);
    assert(fabsf(t - 0.5f) < 0.001f);

    float t2 = calculateStopTime(0.5f);
    assert(fabsf(t2 - 2.0f) < 0.001f);
}

static void test_calculateTimePassed_fast(void)
{
    int t = calculateTimePassed(2.0f);
    assert(t == 1);

    int t2 = calculateTimePassed(-5.0f);
    assert(t2 == 1);

    int t3 = calculateTimePassed(1.0f);
    assert(t3 == 1);

    int t4 = calculateTimePassed(-1.0f);
    assert(t4 == 1);
}

static void test_calculateTimePassed_slow(void)
{
    /* velocity between -1 and 1 (exclusive) takes the else branch */
    int t = calculateTimePassed(0.5f);
    assert(t == (int)fabsf(1.0f / 0.5f));

    int t2 = calculateTimePassed(0.25f);
    assert(t2 == (int)fabsf(1.0f / 0.25f));

    int t3 = calculateTimePassed(-0.5f);
    assert(t3 == (int)fabsf(1.0f / -0.5f));
}

static void test_outOfLine(void)
{
    assert(outOfLine(0) == 0);
    assert(outOfLine(10) == 0);
    assert(outOfLine(-10) == 0);
    assert(outOfLine(49) == 0);
    assert(outOfLine(-49) == 0);

    /* at boundary and beyond */
    assert(outOfLine(50) == 1);
    assert(outOfLine(-50) == 1);
    assert(outOfLine(100) == 1);
    assert(outOfLine(-100) == 1);
}

static void test_C_function(void)
{
    {
        FILE *_redir = freopen("/dev/null", "w", stdout);
        assert(_redir != NULL);
        (void)_redir;
    }
    C();
    {
        FILE *_restore = freopen("/dev/tty", "w", stdout);
        assert(_restore != NULL);
        (void)_restore;
    }
}

static void test_printAcceleration(void)
{
    {
        FILE *_redir = freopen("/dev/null", "w", stdout);
        assert(_redir != NULL);
        (void)_redir;
    }
    printAcceleration(5);
    printAcceleration(-3);
    {
        FILE *_restore = freopen("/dev/tty", "w", stdout);
        assert(_restore != NULL);
        (void)_restore;
    }
}

static void test_pauseSystem(void)
{
    {
        FILE *_redir = freopen("/dev/null", "w", stdout);
        assert(_redir != NULL);
        (void)_redir;
    }
    pauseSystem();
    {
        FILE *_restore = freopen("/dev/tty", "w", stdout);
        assert(_restore != NULL);
        (void)_restore;
    }
}

static void test_clearScreen(void) { clearScreen(); }

static void test_pauseForASecond(void) { pauseForASecond(); }

static void test_pauseForGivenTime(void)
{
    pauseForGivenTime(0.5f);
    pauseForGivenTime(-0.5f);
    pauseForGivenTime(0.0f);
}

static void test_printXPosition(void)
{
    {
        FILE *_redir = freopen("/dev/null", "w", stdout);
        assert(_redir != NULL);
        (void)_redir;
    }
    printXPosition(0);
    printXPosition(42);
    printXPosition(-10);
    {
        FILE *_restore = freopen("/dev/tty", "w", stdout);
        assert(_restore != NULL);
        (void)_restore;
    }
}

static void test_printClock(void)
{
    {
        FILE *_redir = freopen("/dev/null", "w", stdout);
        assert(_redir != NULL);
        (void)_redir;
    }
    unsigned int t = 10;
    printClock(&t);
    t = 0;
    printClock(&t);
    {
        FILE *_restore = freopen("/dev/tty", "w", stdout);
        assert(_restore != NULL);
        (void)_restore;
    }
}

static void test_printVelocity(void)
{
    {
        FILE *_redir = freopen("/dev/null", "w", stdout);
        assert(_redir != NULL);
        (void)_redir;
    }
    printVelocity(3.14f);
    printVelocity(-1.0f);
    {
        FILE *_restore = freopen("/dev/tty", "w", stdout);
        assert(_restore != NULL);
        (void)_restore;
    }
}

static void test_printLine(void)
{
    /* Capture output to a temp file to verify content */
    FILE *tmp = tmpfile();
    assert(tmp != NULL);
    int   fd  = fileno(tmp);
    FILE *cap = fdopen(fd, "w+");
    /* Redirect stdout to tmp */
    FILE *saved = stdout;
    stdout      = cap;

    printLine(0);
    fflush(stdout);

    stdout = saved;

    /* Read back and verify "x" at the correct position */
    fseek(cap, 0, SEEK_END);
    long len = ftell(cap);
    fseek(cap, 0, SEEK_SET);
    char *buf = malloc(len + 1);
    assert(buf != NULL);
    fread(buf, 1, len, cap);
    buf[len] = '\0';

    /* The output is LINE_LENGTH characters. Position 0 maps to index 50 */
    assert(len == LINE_LENGTH);
    assert(buf[50] == 'x');
    for (int i = 0; i < LINE_LENGTH; i++)
    {
        if (i != 50)
            assert(buf[i] == '-');
    }
    free(buf);
    fclose(cap);
}

static void test_printLine_edge(void)
{
    FILE *saved = stdout;
    FILE *tmp   = tmpfile();
    assert(tmp != NULL);
    stdout = tmp;
    printLine(-50);
    fflush(stdout);
    stdout = saved;

    fseek(tmp, 0, SEEK_END);
    long len = ftell(tmp);
    fseek(tmp, 0, SEEK_SET);
    char *buf = malloc(len + 1);
    assert(buf != NULL);
    fread(buf, 1, len, tmp);
    buf[len] = '\0';

    /* position -50 maps to index 0 */
    assert(buf[0] == 'x');
    free(buf);
    fclose(tmp);
}

static void test_printAllInfo(void)
{
    {
        FILE *_redir = freopen("/dev/null", "w", stdout);
        assert(_redir != NULL);
        (void)_redir;
    }
    unsigned int t   = 0;
    float        vel = 2.0f;
    printAllInfo(0, &t, &vel);
    assert(t > 0);

    /* slow velocity branch */
    float        vel2 = 0.5f;
    unsigned int t2   = 0;
    printAllInfo(10, &t2, &vel2);
    assert(t2 > 0);
    {
        FILE *_restore = freopen("/dev/tty", "w", stdout);
        assert(_restore != NULL);
        (void)_restore;
    }
}

static void test_chooseVelocity(void)
{
    /* Redirect stdin to provide input */
    FILE *tmp_in = tmpfile();
    assert(tmp_in != NULL);
    fprintf(tmp_in, "3.5\n");
    fseek(tmp_in, 0, SEEK_SET);

    FILE *saved_in = stdin;
    stdin          = tmp_in;

    {
        FILE *_redir = freopen("/dev/null", "w", stdout);
        assert(_redir != NULL);
        (void)_redir;
    }

    float v = chooseVelocity();
    assert(fabsf(v - 3.5f) < 0.001f);

    stdin = saved_in;
    fclose(tmp_in);
    {
        FILE *_restore = freopen("/dev/tty", "w", stdout);
        assert(_restore != NULL);
        (void)_restore;
    }
}

static void test_chooseAcceleration(void)
{
    FILE *tmp_in = tmpfile();
    assert(tmp_in != NULL);
    fprintf(tmp_in, "7\n");
    fseek(tmp_in, 0, SEEK_SET);

    FILE *saved_in = stdin;
    stdin          = tmp_in;

    {
        FILE *_redir = freopen("/dev/null", "w", stdout);
        assert(_redir != NULL);
        (void)_redir;
    }

    int a = chooseAcceleration();
    assert(a == 7);

    stdin = saved_in;
    fclose(tmp_in);
    {
        FILE *_restore = freopen("/dev/tty", "w", stdout);
        assert(_restore != NULL);
        (void)_restore;
    }
}

static void test_moveUntillOutOfLine_already_out(void)
{
    /* Position already out of line: while loop body never executes */
    {
        FILE *_redir = freopen("/dev/null", "w", stdout);
        assert(_redir != NULL);
        (void)_redir;
    }
    unsigned int t = 0;
    moveUntillOutOfLine(999, &t);
    assert(t == 0);
    {
        FILE *_restore = freopen("/dev/tty", "w", stdout);
        assert(_restore != NULL);
        (void)_restore;
    }
}

static void test_moveUntillOutOfLine_exits(void)
{
    /*
     * Position starts in-line (0). Feed a large velocity via stdin so
     * calculateDisplacement moves position out of line in one step.
     * chooseVelocity reads a float; we feed "100\n".
     */
    FILE *tmp_in = tmpfile();
    assert(tmp_in != NULL);
    fprintf(tmp_in, "100\n");
    fseek(tmp_in, 0, SEEK_SET);

    FILE *saved_in = stdin;
    stdin          = tmp_in;

    {
        FILE *_redir = freopen("/dev/null", "w", stdout);
        assert(_redir != NULL);
        (void)_redir;
    }

    unsigned int t = 0;
    moveUntillOutOfLine(0, &t);

    stdin = saved_in;
    fclose(tmp_in);
    {
        FILE *_restore = freopen("/dev/tty", "w", stdout);
        assert(_restore != NULL);
        (void)_restore;
    }
}

static void test_moveUntillOutOfVelocity_already_out(void)
{
    {
        FILE *_redir = freopen("/dev/null", "w", stdout);
        assert(_redir != NULL);
        (void)_redir;
    }
    int          accel = 5;
    unsigned int t     = 0;
    moveUntillOutOfVelocity(999, &accel, &t);
    assert(t == 0);
    {
        FILE *_restore = freopen("/dev/tty", "w", stdout);
        assert(_restore != NULL);
        (void)_restore;
    }
}

static void test_moveUntillOutOfVelocity_runs(void)
{
    /*
     * Start at position 49 (near boundary) with positive acceleration.
     * velocity starts at 0, first iteration: displacement = 0*1 + 0 = 0, position
     * stays 49. velocity becomes accel*1+0 = 10. Second iteration: displacement =
     * 10*1 + 0 = 10, position = 59 -> out of line. We need at most a few iterations.
     * Since chooseVelocity/chooseAcceleration are NOT called in this function, no
     * stdin redirect needed.
     */
    {
        FILE *_redir = freopen("/dev/null", "w", stdout);
        assert(_redir != NULL);
        (void)_redir;
    }
    int          accel = 10;
    unsigned int t     = 0;
    moveUntillOutOfVelocity(49, &accel, &t);
    assert(t > 0);
    {
        FILE *_restore = freopen("/dev/tty", "w", stdout);
        assert(_restore != NULL);
        (void)_restore;
    }
}

int main(void)
{
    test_calculateVelocity();
    test_calculateDisplacement();
    test_calculateStopTime();
    test_calculateTimePassed_fast();
    test_calculateTimePassed_slow();
    test_outOfLine();
    test_C_function();
    test_printAcceleration();
    test_pauseSystem();
    test_clearScreen();
    test_pauseForASecond();
    test_pauseForGivenTime();
    test_printXPosition();
    test_printClock();
    test_printVelocity();
    test_printLine();
    test_printLine_edge();
    test_printAllInfo();
    test_chooseVelocity();
    test_chooseAcceleration();
    test_moveUntillOutOfLine_already_out();
    test_moveUntillOutOfLine_exits();
    test_moveUntillOutOfVelocity_already_out();
    test_moveUntillOutOfVelocity_runs();

    printf("All tests passed!\n");
    return 0;
}
