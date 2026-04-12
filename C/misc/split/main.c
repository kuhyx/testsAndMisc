#include <stdio.h>

#include "split.h"

// Example usage
int main(void)
{
    int    N            = 5;
    double X            = 100;
    double middle_value = 5.0;
    double distances[5];

    // Example usage for split_x_into_n_middle
    split_x_into_n_middle(X, N, middle_value, distances);

    printf("Split values (with middle value = %.2f):\n", middle_value);
    for (int i = 0; i < N; i++)
    {
        printf("%.2f ", distances[i]);
    }
    printf("\n");

    // Example usage for split_x_into_n_symmetrically
    double factors[2] = {1.0, 2.0};
    split_x_into_n_symmetrically(X, N, factors, distances);

    printf("Split values (symmetric with factors):\n");
    for (int i = 0; i < N; i++)
    {
        printf("%.2f ", distances[i]);
    }
    printf("\n");

    return 0;
}
