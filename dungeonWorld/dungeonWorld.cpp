#include <iostream>
#include <fstream>
#include <vector>
#include <string>
const int STAT_LENGTH = 3;
const int NUMBER_OF_ATTRIBUTES_IN_DUNGEON_WORLD = 6;
const int NUMBER_OF_STATS_IN_DUNGEON_WORLD = 5;
const char STAT_SEPARATOR = ' ';

const int STR_POSITION = 0;
const int DEX_POSITION = 1;
const int CON_POSITION = 2;
const int INT_POSITION = 3;
const int WIS_POSITION = 4;
const int CHA_POSITION = 5;

const int HP_POSITION = 0;
const int ARMOR_POSITION = 1;
const int LVL_POSITION = 2;
const int XP_POSITION = 3;
const int XPNEEDED_POSITION = 4;

const int QUIT = 0;
const int CHANGE_HP_CODE = 1;
const std::string MENU = "What do you want to do? \n 0. QUIT \n 1. Change HP";



void print(const std::string s)
{
  std::cout << s << std::endl;
}

void printNoEndline(const std::string s)
{
  std::cout << s << " ";
}

void printInt(const int i)
{
  std::cout << i << std::endl;
}

void printIntInfo(const std::string s, const int i)
{
  printNoEndline(s);
  printInt(i);
}

void showHP(const int hp)
{
  printIntInfo("Current HP:", hp);
}

std::string enterString()
{
  std::string s;
  std::cin >> s;
  return s;
}

std::string printAndEnterString(const std::string s)
{
  print(s);
  return enterString();
}

void printStringVector(const std::vector <std::string> v)
{
  for(unsigned int i = 0; i < v.size(); i++) print(v[i]);
}

bool isNumber(const char c)
{
  return (c >= '0' && c <= '9');
}

int changeHpLogic(const std::string changeS)
{
  char c = changeS[0];
  if(!isNumber(c))
  {
    if(c == '+') return std::stoi(changeS);
    else return -std::stoi(changeS.substr(1, changeS.length()));
  }else return -std::stoi(changeS);

}

int changeHp(int hp)
{
  return hp + changeHpLogic(printAndEnterString("Enter hp change: ('+' for positive, '' or '-' for negative):"));
}

int calculateHp(int constitution) { return constitution + 8; }

std::vector <std::string> fileToVector(std::ifstream &file)
{
	std::string line;
  std::vector <std::string> strings;
	if(file.is_open())
	{
		while(getline(file, line))
		{
			strings.push_back(line);
		}
		file.close();
	}
	return strings;
}

void vectorToFile(const std::vector <std::string> strings, std::ofstream &file)
{
	for(unsigned int i = 0; i < strings.size(); i++)
	{
		file << strings.at(i) << std::endl;
	}
}

std::vector <std::pair <std::string, int> > stringToAttributes(const std::vector <std::string> stats)
{
  std::vector <std::pair <std::string, int> > statsAndValues(NUMBER_OF_ATTRIBUTES_IN_DUNGEON_WORLD);
  for(int i = 0; i < NUMBER_OF_ATTRIBUTES_IN_DUNGEON_WORLD; i++)
  {

    std::string currentString = stats[i];
    statsAndValues[i].first = currentString.substr(0, STAT_LENGTH);
    std::size_t findSpace = currentString.find(STAT_SEPARATOR);
    statsAndValues[i].second = std::stoi(currentString.substr(findSpace + 1));
  }
  return statsAndValues;
}

std::vector <std::pair <std::string, int> > stringToStats(const std::vector <std::string> stats)
{
  std::vector <std::pair <std::string, int> > statsAndValues(NUMBER_OF_STATS_IN_DUNGEON_WORLD);

  for(int i = NUMBER_OF_ATTRIBUTES_IN_DUNGEON_WORLD; i < NUMBER_OF_ATTRIBUTES_IN_DUNGEON_WORLD + NUMBER_OF_STATS_IN_DUNGEON_WORLD; i++)
  {

    std::string currentString = stats[i];
    std::size_t findSpace = currentString.find(STAT_SEPARATOR);
    statsAndValues[i - NUMBER_OF_ATTRIBUTES_IN_DUNGEON_WORLD].first = currentString.substr(0, findSpace);
    statsAndValues[i - NUMBER_OF_ATTRIBUTES_IN_DUNGEON_WORLD].second = std::stoi(currentString.substr(findSpace + 1));
  }
  return statsAndValues;
}

void printPair(const std::pair <std::string, int> pair)
{
  printIntInfo(pair.first, pair.second);
}

void printPairVector(const std::vector <std::pair <std::string, int> > v)
{
  for(unsigned int i = 0; i < v.size(); i++) printPair(v[i]);
}

std::vector <std::pair <std::string, int> > attributesAndStatsTogether(const std::vector <std::pair <std::string, int> > attributesNumbers, const std::vector <std::pair <std::string, int> > statsNumbers)
{
  std::vector <std::pair <std::string, int> > v;
  v.reserve( attributesNumbers.size() + statsNumbers.size() );
  v.insert( v.end(), attributesNumbers.begin(), attributesNumbers.end() );
  v.insert( v.end(), statsNumbers.begin(), statsNumbers.end() );
  return v;
}

std::vector <std::string> pairToStringVector(const std::vector <std::pair <std::string, int> > v)
{
  std::vector <std::string> stringVector;
  stringVector.reserve(v.size());
   for(unsigned int i = 0; i < v.size(); i++)
   {
     stringVector.push_back(v[i].first + ' ' + std::to_string(v[i].second));
   }
   return stringVector;
}

int charToInt(const char c) { return c - '0'; }

bool charIsNumber(const char c) { return c >= '0' && c <= '9'; }

void printNotValidStringLength(const std::string s, const long unsigned int desiredLength)
{
	std::cout << "String: \"" << s << "\" is too short/too long, it is: "
	<< s.length() << " characters long but should be: " << desiredLength
	<< " characters long " << std::endl;
}

bool validStringLength(const std::string s, const long unsigned int desiredLength)
{
	if(s.length() != desiredLength)
	{
		printNotValidStringLength(s, desiredLength);
		return 0;
	}
	return 1;
}

bool checkMenu(const std::string input)
{
	if(!validStringLength(input, 1)) return 0;
	if(!charIsNumber(input.at(0))) return 0;
	return 1;
}

void printAttributesAndStats(const std::vector <std::pair <std::string, int> > attributesNumbers, const std::vector <std::pair <std::string, int> > statsNumbers)
{
  printPairVector(attributesNumbers);
  std::cout << std::endl;
  printPairVector(statsNumbers);
}

int inputMenu(const std::vector <std::pair <std::string, int> > attributesNumbers, const std::vector <std::pair <std::string, int> > statsNumbers)
{
	std::string choiceS;
	do{
		std::system("clear");
    printAttributesAndStats(attributesNumbers, statsNumbers);
		print(MENU);
		getline(std::cin, choiceS);
	}while(!checkMenu(choiceS));
	return charToInt(choiceS.at(0));;
}

bool menuLoop(std::vector <std::pair <std::string, int> > attributesNumbers, std::vector <std::pair <std::string, int> > &statsNumbers)
{
	int userChoice = inputMenu(attributesNumbers, statsNumbers);
	if(userChoice == QUIT) return 1;
  else if(userChoice == CHANGE_HP_CODE)
  {
    statsNumbers[HP_POSITION].second = changeHp(statsNumbers[HP_POSITION].second);
  }
	return 0;
}


int main()
{
  std::ifstream InputstatsFile ("stats.txt");

  std::vector <std::string> stats = fileToVector(InputstatsFile);
  InputstatsFile.close();
  std::vector <std::pair <std::string, int> > attributesNumbers = stringToAttributes(stats);
  std::vector <std::pair <std::string, int> > statsNumbers = stringToStats(stats);

  bool end = 0;
	while(!end) { end = menuLoop(attributesNumbers, statsNumbers); };


  std::vector <std::pair <std::string, int> > v = attributesAndStatsTogether(attributesNumbers, statsNumbers);
  std::vector <std::string> newStats = pairToStringVector(v);
  std::ofstream OutputstatsFile ("stats.txt");
  vectorToFile(newStats, OutputstatsFile);
  OutputstatsFile.close();


  return 0;
}
