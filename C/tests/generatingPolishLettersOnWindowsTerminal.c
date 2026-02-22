#include <stdio.h>
#include <stdlib.h>

#ifdef _WIN32
#include <windows.h>
#define SLEEP_S(s) Sleep((s) * 1000)
#else
#include <unistd.h>
#define SLEEP_S(s) sleep(s)
#endif

int main(void)
{
    printf("Henlo\n");
    SLEEP_S(20);
    return 0;
}
