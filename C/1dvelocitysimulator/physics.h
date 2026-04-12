#ifndef PHYSICS_H
#define PHYSICS_H

#ifdef _WIN32
#include <windows.h>
#define SLEEP_MS(ms) Sleep(ms)
#define CLEAR_SCREEN() system("CLS")
#define PAUSE()                                                                                    \
    do                                                                                             \
    {                                                                                              \
        printf("Press Enter to continue...");                                                      \
        getchar();                                                                                 \
    } while (0)
#else
#include <unistd.h>
#ifdef TESTING
#define SLEEP_MS(ms) ((void)0)
#define CLEAR_SCREEN() ((void)0)
#define PAUSE() ((void)0)
#else
#define SLEEP_MS(ms) usleep((ms) * 1000U)
#define CLEAR_SCREEN() system("clear")
#define PAUSE()                                                                                    \
    do                                                                                             \
    {                                                                                              \
        printf("Press Enter to continue...");                                                      \
        getchar();                                                                                 \
    } while (0)
#endif
#endif

#define LINE_LENGTH 100

void  C(void);
void  printAcceleration(int acceleration);
void  pauseSystem(void);
void  clearScreen(void);
void  pauseForASecond(void);
void  pauseForGivenTime(float given_time);
float calculateVelocity(float starting_velocity, unsigned int physics_time, int *acceleration);
int   calculateDisplacement(float starting_velocity, int *acceleration, unsigned int physics_time);
void  printXPosition(int position);
void  printClock(unsigned int *time);
float calculateStopTime(float velocity);
void  printLine(int position);
void  printVelocity(float velocity);
int   calculateTimePassed(float velocity);
void  printAllInfo(int position, unsigned int *time, float *velocity);
float chooseVelocity(void);
int   chooseAcceleration(void);
int   outOfLine(int position);
void  moveUntillOutOfLine(int position, unsigned int *time);
void  moveUntillOutOfVelocity(int position, int *acceleration, unsigned int *time);

#endif /* PHYSICS_H */
