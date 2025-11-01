#include "engine.h"
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static void sleep_millis(unsigned int milliseconds)
{
    struct timespec req = {
        .tv_sec  = milliseconds / 1000,
        .tv_nsec = (long)(milliseconds % 1000) * 1000000L,
    };
    (void)nanosleep(&req, NULL);
}

static bool spawn_process(const char *path, Engine *e)
{
    int inpipe[2], outpipe[2];
    if (pipe(inpipe) < 0 || pipe(outpipe) < 0)
        return false;
    pid_t pid = fork();
    if (pid < 0)
        return false;
    if (pid == 0)
    {
        dup2(inpipe[0], STDIN_FILENO);   // child stdin from inpipe[0]
        dup2(outpipe[1], STDOUT_FILENO); // child stdout to outpipe[1]
        dup2(outpipe[1], STDERR_FILENO);
        close(inpipe[0]);
        close(inpipe[1]);
        close(outpipe[0]);
        close(outpipe[1]);
        execlp(path, path, (char *)NULL);
        _exit(127);
    }
    // parent
    close(inpipe[0]);
    close(outpipe[1]);
    e->pid    = pid;
    e->in_fd  = inpipe[1];
    e->out_fd = outpipe[0];
    e->ready  = false;
    // make out_fd non-blocking for reads with polling
    int flags = fcntl(e->out_fd, F_GETFL, 0);
    fcntl(e->out_fd, F_SETFL, flags | O_NONBLOCK);
    return true;
}

static bool try_start(Engine *e, const char *name)
{
    if (!spawn_process(name, e))
        return false;
    // send UCI init
    engine_cmd(e, "uci\n");
    char buf[4096];
    int  attempts = 50; // ~5s total
    while (attempts--)
    {
        sleep_millis(100);
        ssize_t n = read(e->out_fd, buf, sizeof(buf) - 1);
        if (n > 0)
        {
            buf[n] = '\0';
            if (strstr(buf, "uciok"))
            {
                e->ready = true;
                break;
            }
        }
    }
    if (!e->ready)
    {
        engine_stop(e);
        return false;
    }
    engine_cmd(e, "isready\n");
    attempts = 50;
    while (attempts--)
    {
        sleep_millis(100);
        ssize_t n = read(e->out_fd, buf, sizeof(buf) - 1);
        if (n > 0)
        {
            buf[n] = '\0';
            if (strstr(buf, "readyok"))
                break;
        }
    }
    return e->ready;
}

bool engine_start(Engine *e)
{
    memset(e, 0, sizeof(*e));
    e->pid    = -1;
    e->in_fd  = -1;
    e->out_fd = -1;
    e->ready  = false;
    if (try_start(e, "stockfish"))
        return true;
    if (try_start(e, "asmfish"))
        return true;
    return false;
}

void engine_stop(Engine *e)
{
    if (e->in_fd != -1)
    {
        write(e->in_fd, "quit\n", 5);
        close(e->in_fd);
    }
    if (e->out_fd != -1)
        close(e->out_fd);
    if (e->pid > 0)
    {
        int status;
        waitpid(e->pid, &status, 0);
    }
    e->pid   = -1;
    e->in_fd = e->out_fd = -1;
    e->ready             = false;
}

bool engine_cmd(Engine *e, const char *cmd)
{
    if (e->in_fd == -1)
        return false;
    size_t  len = strlen(cmd);
    ssize_t n   = write(e->in_fd, cmd, len);
    if (n < 0)
    {
        return false;
    }
    return n == (ssize_t)len;
}

static void position_to_uci(const Position *pos, char *out, size_t outsz)
{
    // Send starting position and moves list by comparing with startpos; for simplicity, use FEN
    // always.
    char fen[256];
    chess_to_fen(pos, fen, sizeof(fen));
    (void)snprintf(out, outsz, "position fen %s\n", fen);
}

size_t engine_get_top_moves(Engine *e, const Position *pos, EngineMove *out, size_t max)
{
    if (!e->ready)
        return 0;
    char cmd[512];
    position_to_uci(pos, cmd, sizeof(cmd));
    engine_cmd(e, cmd);
    // ask multiPV up to max (cap at 5 as requested)
    size_t req = max;
    if (req > 5)
        req = 5;
    char go[128];
    (void)snprintf(go, sizeof(go), "setoption name MultiPV value %zu\n", req);
    engine_cmd(e, go);
    engine_cmd(e, "go movetime 400\n");
    char   buf[8192];
    size_t count    = 0;
    int    attempts = 50;
    while (attempts--)
    {
        sleep_millis(100);
        ssize_t n = read(e->out_fd, buf, sizeof(buf) - 1);
        if (n <= 0)
            continue;
        buf[n]     = '\0';
        char *line = strtok(buf, "\n");
        while (line)
        {
            if (strncmp(line, "info ", 5) == 0)
            {
                // parse "info ... multipv X score cp Y ... pv <uci>"
                char *mpv   = strstr(line, " multipv ");
                char *score = strstr(line, " score ");
                char *pv    = strstr(line, " pv ");
                if (mpv && score && pv)
                {
                    char *idx_end  = NULL;
                    long  idx_long = strtol(mpv + 9, &idx_end, 10);
                    if (idx_end == mpv + 9 || idx_long < 1 || (size_t)idx_long > req)
                    {
                        line = strtok(NULL, "\n");
                        continue;
                    }
                    size_t idx = (size_t)idx_long;
                    if (idx >= 1 && idx <= req)
                    {
                        int   cp     = 0;
                        char *cp_loc = strstr(score, "cp ");
                        if (cp_loc)
                        {
                            char *cp_end  = NULL;
                            long  cp_long = strtol(cp_loc + 3, &cp_end, 10);
                            if (cp_end != cp_loc + 3 && cp_long >= INT_MIN && cp_long <= INT_MAX)
                            {
                                cp = (int)cp_long;
                            }
                        }
                        char mv[8] = {0};
                        if (sscanf(pv + 4, "%7s", mv) != 1)
                        {
                            line = strtok(NULL, "\n");
                            continue;
                        }
                        size_t i = idx - 1;
                        if (i < req)
                        {
                            out[i].score_cp = cp;
                            (void)snprintf(out[i].uci, sizeof(out[i].uci), "%s", mv);
                            if (i + 1 > count)
                                count = i + 1;
                        }
                    }
                }
            }
            else if (strncmp(line, "bestmove ", 9) == 0)
            {
                attempts = 0;
                break;
            }
            line = strtok(NULL, "\n");
        }
    }
    // simple sort by score descending (best to worst), keeping empties at end
    for (size_t i = 0; i < count; i++)
    {
        for (size_t j = i + 1; j < count; j++)
        {
            if (out[j].score_cp > out[i].score_cp)
            {
                EngineMove tmp = out[i];
                out[i]         = out[j];
                out[j]         = tmp;
            }
        }
    }
    return count;
}

bool engine_get_best_move(Engine *e, const Position *pos, char out_uci[8])
{
    if (!e->ready)
        return false;
    char cmd[512];
    position_to_uci(pos, cmd, sizeof(cmd));
    engine_cmd(e, cmd);
    engine_cmd(e, "go movetime 300\n");
    char buf[4096];
    int  attempts = 50;
    while (attempts--)
    {
        sleep_millis(100);
        ssize_t n = read(e->out_fd, buf, sizeof(buf) - 1);
        if (n <= 0)
            continue;
        buf[n]     = '\0';
        char *line = strtok(buf, "\n");
        while (line)
        {
            if (strncmp(line, "bestmove ", 9) == 0)
            {
                return sscanf(line + 9, "%7s", out_uci) == 1;
            }
            line = strtok(NULL, "\n");
        }
    }
    return false;
}
