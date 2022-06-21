#include <stdio.h>
#include <windows.h>
#include <stdlib.h>
#include <math.h>
#define LINE_LENGTH 100

void C()
{
    printf("\nCheck\n");
    return;
}

void printAcceleration(int acceleration)
{
    printf("The value of acceleration is: %d\n", acceleration);
    system("PAUSE");
    return;
}

void pauseSystem()
{
    system("PAUSE");
}

void clearScreen()
{
    system("CLS");
    return;
}

void pauseForASecond()
{
    Sleep(1000);
    return;
}

void pauseForGivenTime(float given_time)
{
    Sleep(fabs(given_time * 1000));
    return;
}

float calculateVelocity(float starting_velocity, unsigned int physics_time, int *acceleration)
{
    return (*acceleration) * physics_time + starting_velocity;
}

int calculateDisplacement(float starting_velocity, int *acceleration, unsigned int physics_time)
{
    return starting_velocity * physics_time + ( (1 / 2) * (*acceleration) * (physics_time ^ 2) );
}

void printXPosition(int position)
{
    printf("\nx position is: %d\n", position);
    return;
}

void printClock(unsigned int *time)
{
    printf("%d seconds passed\n", *time);
    return;
}

float calculateStopTime(float velocity)
{
    return 1 / velocity;
}

void printLine(int position)
{
    clearScreen();
    for(int i = -(LINE_LENGTH / 2); i < LINE_LENGTH / 2; i++)
    {
        if(i == position) printf("x");
        else printf("-");
    }
    return;
}

void printVelocity(float velocity)
{
    printf("Velocity is: %f\n", velocity);
    return;
}

int calculateTimePassed(float velocity)
{
    if(velocity >= 1 || velocity <= -1) return 1;
    else
    {
    printf("Time passed is: %f\n", fabs(1 / velocity));
    return fabs(1 / velocity);
    }
}



void printAllInfo(int position, unsigned int *time, float *velocity)
{
    pauseForGivenTime(calculateStopTime(*velocity));
    printLine(position);
    printXPosition(position);
    *time += calculateTimePassed(*velocity);
    printClock(time);
    printVelocity(*velocity);
    //pauseForASecond();
    return;
}

float chooseVelocity()
{
    float velocity;
    printf("Write velocity of the object in m / s: ");
    scanf("%f", &velocity);
    return velocity;
}

int chooseAcceleration()
{
    int acceleration;
    printf("Choose acceleration of the object in m / (s ^ 2):");
    scanf("%d", &acceleration);
    return acceleration;
}

int outOfLine(int position)
{
    if((position < LINE_LENGTH / 2) && (position > -1 * (LINE_LENGTH / 2)))
    {
        return 0;
    }else return 1;
}

void moveUntillOutOfLine(int position, unsigned int *time)
{
    while(!outOfLine(position))
    {
        float velocity = chooseVelocity();
        float *Pvelocity = &velocity;
        position += calculateDisplacement(velocity, 0, 1);
        printAllInfo(position, time, Pvelocity);
    }
    return;
}

void moveUntillOutOfVelocity(int position, int *acceleration, unsigned int *time)
{
    float velocity = 0;
    float *Pvelocity = &velocity;
    while(!outOfLine(position))
    {
        position += calculateDisplacement(velocity, acceleration, 1);
        printXPosition(position);
        pauseSystem();
        velocity = calculateVelocity(velocity,  1, acceleration);
        printAllInfo(position, time, Pvelocity);
    }
    return;
}

int main()
{
    int position = 0, acceleration = -1;
    int *Pacceleration = &acceleration;
    unsigned int time = 0;
    unsigned int *Ptime = &time;
    moveUntillOutOfLine(position, Ptime);
    //moveUntillOutOfVelocity(position, Pacceleration, Ptime);
    return 0;
}
