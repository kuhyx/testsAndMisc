#include "physics.h"

int main()
{
    int           position = 0, acceleration = -1;
    int          *Pacceleration = &acceleration;
    unsigned int  time          = 0;
    unsigned int *Ptime         = &time;
    moveUntillOutOfLine(position, Ptime);
    // moveUntillOutOfVelocity(position, Pacceleration, Ptime);
    return 0;
}
