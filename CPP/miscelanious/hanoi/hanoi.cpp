#include <iostream>
#include <deque>
#include <math.h>

const int NUMBER_OF_FREE_STICKS = 3;

void drawSpaces(int &numberOfPlates, int currentPlate)
{
  for(int i = 0; i < numberOfPlates - currentPlate; i++)
  {
    std::cout << " ";
  }
}

void drawFreeSticks(int &numberOfPlates)
{
  for(int i = 0; i < NUMBER_OF_FREE_STICKS; i++)
  {
    std::cout << "|";
    drawSpaces(numberOfPlates, 0);
    std::cout << "|";
    drawSpaces(numberOfPlates, 0);
    std::cout << "|" << std::endl;
  }
}

void drawRod(std::deque<int> &rod, int &currentLevel)
{
  unsigned int currentLevelUnsinged = currentLevel;
  if(rod.size() > currentLevelUnsinged)
  {
    int j = rod[currentLevel];
    do
    {
      std::cout << "#";
      j--;
    }while (j != 0);
  }else std::cout << "|";
}

void drawRest(std::deque<int> &firstRod, std::deque<int> &secondRod, std::deque<int> &thirdRod, int &numberOfPlates)
{
  for(int i = 0; i < numberOfPlates; i++)
  {
    drawRod(firstRod, i);
    drawRod(secondRod, i);
    drawRod(thirdRod, i);
    std::cout << std::endl;
  }
}


void drawTheTowers(std::deque<int> &firstRod, std::deque<int> &secondRod, std::deque<int> &thirdRod, int &numberOfPlates)
{
  drawFreeSticks(numberOfPlates);
  drawRest(firstRod, secondRod, thirdRod, numberOfPlates);
}




void printDeque(const std::deque <int> deque)
{
  if(deque.size() != 0)
  {
    std::cout << "[";
    for(unsigned int i = 0; i < deque.size(); i++)
    {
      std::cout << deque[i] << "; ";
    }
    std::cout << "]" << std::endl;
  }else std::cout << "Deque is empty" << std::endl;
}

void onlyLegalMove(std::deque<int> &firstRod, std::deque<int> &secondRod)
{
  if((!firstRod.empty() && firstRod.front() == 0) || (!secondRod.empty() && secondRod.front() == 0))
  {
    printDeque(firstRod);
    printDeque(secondRod);
  }

  if(firstRod.empty() && secondRod.empty())
  {
    std::cout << "BOTH EMPTY!" << std::endl;
  }else if(secondRod.empty() || (!firstRod.empty() && firstRod.front() < secondRod.front()) )
  {
    secondRod.push_front(firstRod.front());
    firstRod.pop_front();
  }else if(firstRod.empty() || (!secondRod.empty() && firstRod.front() > secondRod.front()) )
  {
    firstRod.push_front(secondRod.front());
    secondRod.pop_front();
  }else
  {
    std::cout << "SOMETHING WENT TERRIBLY WRONG!" << std::endl;
    printDeque(firstRod);
    printDeque(secondRod);
  }
}

void doTheThingEven(std::deque<int> &firstRod, std::deque<int> &secondRod, std::deque<int> &thirdRod, const unsigned int numberOfPlates)
{
  int i = 0;
  do{
    onlyLegalMove(firstRod, secondRod);
    i++;
    onlyLegalMove(firstRod, thirdRod);
    i++;
    onlyLegalMove(secondRod, thirdRod);
    i++;
  }while(thirdRod.size() != numberOfPlates);
  printDeque(firstRod);
  printDeque(secondRod);
  printDeque(thirdRod);
  std::cout << i << std::endl;
}

void doTheThingOdd(std::deque<int> &firstRod, std::deque<int> &secondRod, std::deque<int> &thirdRod, const unsigned int numberOfPlates)
{
  int i = 0;
  do{
    onlyLegalMove(firstRod, thirdRod);
    i++;
    onlyLegalMove(firstRod, secondRod);
    i++;
    onlyLegalMove(secondRod, thirdRod);
    i++;
  }while(thirdRod.size() != numberOfPlates);
  printDeque(firstRod);
  printDeque(secondRod);
  printDeque(thirdRod);
  std::cout << i << std::endl;
}

/*
even:
AB AC BC
odd:
AC AB BC
*/

std::deque <int> fillDeque(const int maxNumber)
{
  std::deque <int> deque;
  for(int i = 1; i <= maxNumber; i++ )
  {
    deque.push_back(i);
  }
  return deque;
}

int main()
{
  unsigned int numberOfPlates;
  std::cout << "Enter number of plates: " << std::endl;
  std::cin >> numberOfPlates;
  std::deque<int> firstRod, secondRod, thirdRod;
  firstRod = fillDeque(numberOfPlates);
  secondRod = {};
  thirdRod = {};
  if(firstRod.size() % 2 == 0) doTheThingEven(firstRod, secondRod, thirdRod, numberOfPlates);
  else doTheThingOdd(firstRod, secondRod, thirdRod, numberOfPlates);


  return 0;
}
