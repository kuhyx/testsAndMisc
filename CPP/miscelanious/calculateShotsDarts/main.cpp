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

// Darts checkout finder: find combinations of up to 3 darts that reduce
// pointsLeft to exactly 0, finishing on a double (standard 501 rules).
std::vector<int> requiredShoots(const int pointsLeft) {
  // All valid dart scores with labels
  std::vector<std::pair<int, std::string>> all_darts;
  for (int i = MIN_SPOT; i <= MAX_SPOT; i++)
    all_darts.push_back({i, std::to_string(i)});
  all_darts.push_back({25, "Bull"});
  for (int i = MIN_SPOT; i <= MAX_SPOT; i++)
    all_darts.push_back({i * 2, "D" + std::to_string(i)});
  all_darts.push_back({50, "D-Bull"});
  for (int i = MIN_SPOT; i <= MAX_SPOT; i++)
    all_darts.push_back({i * 3, "T" + std::to_string(i)});

  // Doubles only (valid finishing darts)
  std::vector<std::pair<int, std::string>> doubles;
  for (int i = MIN_SPOT; i <= MAX_SPOT; i++)
    doubles.push_back({i * 2, "D" + std::to_string(i)});
  doubles.push_back({50, "D-Bull"});

  std::vector<std::vector<std::string>> checkouts;
  const int MAX_RESULTS = 5;

  // 1-dart checkouts
  for (auto &d : doubles)
    if (d.first == pointsLeft)
      checkouts.push_back({d.second});

  // 2-dart checkouts
  for (auto &d1 : all_darts) {
    for (auto &d2 : doubles) {
      if (d1.first + d2.first == pointsLeft) {
        checkouts.push_back({d1.second, d2.second});
        if ((int)checkouts.size() >= MAX_RESULTS)
          goto done;
      }
    }
  }

  // 3-dart checkouts (stop early once we have enough results)
  for (auto &d1 : all_darts) {
    for (auto &d2 : all_darts) {
      for (auto &d3 : doubles) {
        if (d1.first + d2.first + d3.first == pointsLeft) {
          checkouts.push_back({d1.second, d2.second, d3.second});
          if ((int)checkouts.size() >= MAX_RESULTS)
            goto done;
        }
      }
    }
  }
done:
  if (checkouts.empty()) {
    print("No checkout possible for " + std::to_string(pointsLeft) +
          " points.");
    return {};
  }

  print("Possible checkouts (showing up to " + std::to_string(MAX_RESULTS) +
        "):");
  std::vector<int> firstCheckout;
  for (auto &combo : checkouts) {
    std::string line;
    for (unsigned int i = 0; i < combo.size(); i++) {
      if (i > 0)
        line += " \u2192 ";
      line += combo[i];
    }
    print(line);
  }
  return firstCheckout;
}

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
