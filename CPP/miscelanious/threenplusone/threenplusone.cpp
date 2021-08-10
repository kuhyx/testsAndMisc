#include <iostream>
#include <math.h>

int threeNLoop(int n)
{
  int steps = 0;
  do{
    if(n % 2 == 1)
    {
      n = (3*n + 1) / 2;
      steps += 2;
    }else
    {
      n /= 2;
      steps++;
    }
  }while(n != 1);
  return steps;
}

int main()
{
  int n;
  std::cout << "Enter n (where the numbers checked wil be at most 2 ^ n) value:" << std::endl;
  std::cin >> n;
  int maxSteps = 0;
  int maxN = 1;
  for(int i = 1; i <= pow(2, n); i++)
  {
    int currentSteps = threeNLoop(i);
    if(currentSteps > maxSteps)
    {
      maxSteps = currentSteps;
      maxN = i;
    }

  }
  std::cout << "max steps: " << maxSteps << std::endl;
  std::cout << "For n = " << maxN << std::endl;
  return 0;
}
