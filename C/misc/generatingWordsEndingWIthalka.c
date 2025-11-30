#include <stdio.h>

const int NUMBER_FOR_POLISH_SMALL_L = 136;

int main(void)
{
    for (char i = 'a'; i < 'z' + 1; ++i)
    {
        printf("%ca%cka\n", i, NUMBER_FOR_POLISH_SMALL_L);
    }
    return 0;
}
