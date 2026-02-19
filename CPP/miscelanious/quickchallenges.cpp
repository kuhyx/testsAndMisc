#include <iostream>
#include <vector>

int sumStartEnd(int start, int end) {
  int sum = 0;
  for (int i = start; i <= end; i++) {
    sum += i;
  }
  return sum;
}

int main() {
  std::cout << "Krzysztof" << std::endl;
  for (int i = 700; i >= 200; i -= 13)
    std::cout << i << std::endl;
  std::vector<int> array = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};
  // if SECOND means 0, 1, TWO
  std::cout << array[2] << std::endl;
  // if SECOND means 1, TWO
  std::cout << array[1] << std::endl;
  std::cout << sumStartEnd(0, 1000);

  std::string userName;
  std::cout << std::endl;
  getline(std::cin, userName);
  if (userName == "Jack")
    std::cout << "Hi Jack!" << std::endl;
  else
    std::cout << "Hello, " << userName << std::endl;

  for (int i = 0; i <= 100; i++) {
    if (i % 2 == 0)
      std::cout << i << " is an even number" << std::endl;
    else
      std::cout << i << " is an odd number" << std::endl;
  }

  bool flag = 1;
  for (int i = 0; i <= 100; i++) {
    if (flag)
      std::cout << i << " is an even number" << std::endl;
    else
      std::cout << i << " is an odd number" << std::endl;
    flag = -flag;
  }

  for (int i = 0; i <= 100; i += 2)
    std::cout << i << " is an even number " << std::endl;
  for (int i = 1; i <= 99; i += 2)
    std::cout << i << " is an odd number " << std::endl;

  for (int i = 1, j = 1; j <= 12; i++) {
    std::cout << i * j << " ";

    if (i == 12) {
      i = 1;
      j++;
      std::cout << std::endl;
    }
  }

  std::cout << std::endl;
  std::string sentence;
  getline(std::cin, sentence);
  std::vector<std::string> words;
  std::string temp;
  for (unsigned int i = 0; i < sentence.length(); i++) {
    if (sentence.at(i) == ' ' || i + 1 == sentence.length()) {
      if (i + 1 == sentence.length())
        temp.push_back(sentence.at(i));
      words.push_back(temp);
      temp = "";
    } else
      temp.push_back(sentence.at(i));
  }

  for (unsigned int i = 0; i < words.size(); i++) {
    std::cout << words[i] << std::endl;
  }

  int score;
  char project;
  std::vector<char> GRADES = {'F', 'C', 'B', 'A'};
  std::cin >> score;
  std::cout << std::endl;
  std::cin >> project;
  std::cout << std::endl;
  bool doneProject = 0;
  if (project == 'Y')
    doneProject = 1;
  if (score < 50)
    std::cout << GRADES[0 + doneProject];
  else if (score < 70)
    std::cout << GRADES[1 + doneProject];
  else if (score < 90)
    std::cout << GRADES[2 + doneProject];
  else
    std::cout << GRADES[3];
}
