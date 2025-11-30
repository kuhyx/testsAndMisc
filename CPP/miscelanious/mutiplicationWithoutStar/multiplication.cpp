#include <iostream>


int multiplication(int a, int b)
{
	int answer = 0;
	for(int i = 0; i < a; i++)
	{
		answer += b;
	}
	if(answer != a*b)
	{
		std::cout << "There is a mistake in your code!" << std::endl;
		return -1;
	} else return answer;
}

int main()
{
	int a,b;
	std::cout << "Enter number a" << std::endl;
	std::cin >> a;
	std::cout << "Enter number b" << std::endl;
	std::cin >> b;
	std::cout << multiplication(a, b) << std::endl;
	return 0;
}
