#ifndef BASIC_CPP
#define BASIC_CPP

#include <string>
#include <vector>
#include <iostream>
#include <fstream>

void print(const std::string s) { std::cout << s << std::endl; }

int charToInt(const char c) { return c - '0'; }

void e() { print("Poor man breakboint"); }

bool charIsNumber(const char c) { return c >= '0' && c <= '9'; }

void printStringNewLine(const std::string s)
{
	std::cout << "string: " << std::endl;
	std::cout << "\"" << s << "\"" << std::endl;
}

void printStringContainsNotNumbers(const std::string s, const int position)
{
	printStringNewLine(s);
	std::cout << "contains character different than number at position: " << position
	<< "; this character is: " << s.at(position) << std::endl;
}

void printStringContainsNumbers(const std::string s, const int position)
{
	printStringNewLine(s);
	std::cout << "contains number at postion: " << position
	<< "; this number is: " << s.at(position) << std::endl;
}

void printNumberTooLow(const int number, const int min)
{
	std::cout << "number: " << number
	<< " is too low. Minimal number is: " << min << std::endl;
}

void printNumberTooHigh(const int number, const int max)
{
	std::cout << "number: " << number
	<< " is too high. Maximal number is: " << max << std::endl;
}

void printNotValidStringLength(const std::string s, const int desiredLength)
{
	printStringNewLine(s);
	std::cout << "is too short/too long, it is: "
	<< s.length() << " characters long but should be: " << desiredLength
	<< " characters long " << std::endl;
}

void printInvalidCharacter(const char c, const char desiredCharacter)
{
	std::cout << "[ " << c << " ] Is invalid character, expected: [ "
	<< desiredCharacter << " ]" << std::endl;
}

void printContainsIllegalCharacter(	const std::string s,
									const char illegalCharacter )
{
	printStringNewLine(s);
	std::cout << " consists of illegal sign: ["
	<< illegalCharacter << "]!" << std::endl;
}


bool numberTooLow(const int number, const int min)
{
	if(number < min)
	{
		printNumberTooLow(number, min);
		return 1;
	}
	return 0;
}

bool numberTooHigh(const int number, const int max)
{
	if(number > max)
	{
		printNumberTooHigh(number, max);
		return 1;
	}
	return 0;
}

bool containsIllegalCharacter(const std::string s, const char illegalCharacter)
{
	if(	s.find(illegalCharacter) != std::string::npos)
	{
		printContainsIllegalCharacter(s, illegalCharacter);
		return 1;
	}
	return 0;
}

void printStringVector(const std::vector <std::string> vector)
{
	for(unsigned int i = 0; i < vector.size(); i++) print(vector.at(i));
}

bool stringContainsNotNumbers(const std::string s)
{
	for(unsigned int i = 0; i < s.length(); i++)
	{
		if(!charIsNumber(s.at(i)))
		{
			printStringContainsNotNumbers(s, i);
			return 1;
		}
	}
	return 0;
}

bool stringContainsNumbers(const std::string s)
{
	for(unsigned int i = 0; i < s.length(); i++)
	{
		if(charIsNumber(s.at(i)))
		{
			printStringContainsNumbers(s, i);
			return 1;
		}
	}
	return 0;
}

bool validStringLength(const std::string s, const int desiredLength)
{
	int stringLength = s.length();
	if(stringLength != desiredLength)
	{
		printNotValidStringLength(s, desiredLength);
		return 0;
	}
	return 1;
}

bool validCharacter(const char inputC, const char desiredC)
{
	if(inputC != desiredC)
	{
		printInvalidCharacter(inputC, desiredC);
		return 0;
	}
	return 1;
}

void vectorToFile(const std::vector <std::string> strings, std::ofstream &file)
{
	for(unsigned int i = 0; i < strings.size(); i++)
	{
		file << strings.at(i) << std::endl;
	}
}

std::vector <std::string> fileToVector(std::ifstream &file,
									   std::vector <std::string> strings)
{
	std::string line;
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

#endif
