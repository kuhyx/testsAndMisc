#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <fstream>

#ifndef CHECK_ISBN_CPP
#define CHECK_ISBN_CPP


const bool DEBUG = 0;
const int ISBN_LENGTH = 10;
const int CHECK_NUMBER = 11;
const unsigned long long int HIGHEST_ISBN = 9999999999;


void printVector(std::vector <int> v)
{
	for(unsigned int i = 0; i < v.size(); i++)
	{
		std::cout << v[i] << "; ";
	}
}

void print(const std::string printMe)
{
	std::cout << printMe << std::endl;
}

void e()
{
	print("PRINT");
}

bool checkInput(const std::string input)
{
		if(input.length() != ISBN_LENGTH)
		{
			print("Your number is too short/too long");
			return 0;
		}
		for(int i = 0; i <= ISBN_LENGTH - 1; i++)
		{
			if(input.at(i) < '0' || input.at(i) > '9') 
			{
				print("Your number consists of illegal characters");
				return 0;
			}
		}
		return 1;
}

std::vector <int> stringToIntVector(const std::string input)
{
	std::vector <int> vector;
	for(int i = input.length() - 1; i >= 0; i--)
	{
		vector.push_back(input.at(i) - '0');
	}
	return vector;
}

std::vector <int> userISBN()
{
	std::string input;
	do{
	std::cout << "Enter the ISBN number (10 digits): ";
	getline(std::cin, input);
	}while(!checkInput(input));
	return stringToIntVector(input);
}




bool checkISBN(const std::vector <int> isbn)
{
	int sum = 0, t = 0;
	for(int i = 0; i < ISBN_LENGTH; i++)
	{
		t += isbn[i];
		sum += t;
	}
	
	/*if(DEBUG) 
	{
		if(!(sum % CHECK_NUMBER)) print("^^^ VALID NUMBER ^^^");
	} */
	
	return !(sum % CHECK_NUMBER);
}

std::vector <int> intToVector(unsigned long long int number)
{
	std::vector <int> numbers;
	while(number > 0)
	{
	   numbers.push_back(number % 10);
	   number /= 10;
	}
	std::reverse(numbers.begin(), numbers.end());
	
	return numbers;
}



int checkAll()
{
	int sum = 0;
	std::ofstream file;
	file.open("ISBN.txt");
	for(unsigned long long int i = HIGHEST_ISBN; i >= 1; i--) 
		{
			//if(DEBUG) std::cout << i << std::endl;
			if( checkISBN(intToVector(i)) )
			{
				++sum;
				file << std::to_string(i) << "\n";
			}
		}
	file << "There are " << sum << " valid ISBN numbers\n";
	file.close();
	return sum;
}

int main()
{
	checkAll();
	return 0;
}

#endif
