#ifndef MAIN_CPP
#define MAIN_CPP

#include "basic.cpp"
#include <iostream>
#include <string>
#include <vector>

std::vector<int> fillVector(const int min, const int max) {
  std::vector<int> newVector;
  for (int i = min; i <= max; i++) {
    newVector.push_back(i);
  }
  return newVector;
}

const int MAX_SPOT = 20;
const int MIN_SPOT = 1;
const std::vector<int> NORMAL_POINTS = fillVector(MIN_SPOT, MAX_SPOT);

std::vector<int> multiplyVector(const std::vector<int> v, int multiplyBy) {
  std::vector<int> newVector;
  for (unsigned int i = 0; i < v.size(); i++) {
    newVector.push_back(v.at(i) * multiplyBy);
  }
  return newVector;
}

const std::vector<int> DOUBLE_POINTS = multiplyVector(NORMAL_POINTS, 2);
const std::vector<int> TRIPLE_POINTS = multiplyVector(NORMAL_POINTS, 3);
const int MAX_ONE_HIT = TRIPLE_POINTS.at(TRIPLE_POINTS.size() - 1);
const int THROWS_IN_ONE_HIT = 3;
const int MAX_POINTS_TURN = THROWS_IN_ONE_HIT * MAX_ONE_HIT;
const int STARTING_POINTS = 501;
const int FINAL_POINTS = 0;

bool validString(const std::string s) {
  for (unsigned int i = 0; i < s.length(); i++) {
    if (!charIsNumber(s.at(i))) {
      printErrorStringContainsNotNumber(s);
      return 0;
    }
  }
  return 1;
}

bool validNumberInput(const std::string input, const int min, const int max) {
  if (!validString(input))
    return 0;
  int inputInt = std::stoi(input);
  if (numberTooLow(inputInt, min))
    return 0;
  if (numberTooHigh(inputInt, max))
    return 0;
  return 1;
}

bool validInput(const std::string s) {
  if (s.length() > 3)
    return 0;
  if (!validNumberInput(s, FINAL_POINTS, STARTING_POINTS))
    return 0;
  return 1;
}

// cppcheck-suppress missingReturn
std::vector<int> requiredShoots(const int pointsLeft) {}

int main() {
  print("Enter points left: ");
  std::string pointsLeft;
  do {
    getline(std::cin, pointsLeft);
  } while (!validInput(pointsLeft));
  int pointsLeftInt = std::stoi(pointsLeft);
  requiredShoots(pointsLeftInt);
  return 0;
}

#endif
