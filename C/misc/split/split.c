#include <stdlib.h>

#include "split.h"

void calculate_symmetric_weights(int N, double middle_weight, const double *factors,
                                 double *weights)
{
    int half_N      = N / 2;
    int i           = 0;
    weights[half_N] = middle_weight;

    if (factors)
    {
        for (i = 0; i < half_N; i++)
        {
            if (i == 0)
            {
                weights[half_N - i - 1] = middle_weight + factors[i];
            }
            else
            {
                weights[half_N - i - 1] = weights[half_N - i] + factors[i];
            }
        }
    }
    else
    {
        for (i = 0; i < half_N; i++)
        {
            weights[half_N - i - 1] = middle_weight - (i + 1);
        }
    }

    for (i = 0; i < half_N; i++)
    {
        weights[half_N + i + 1] = weights[half_N - i - 1];
    }
}

void scale_to_total(double X, const double *weights, int N, double *distances)
{
    double total_weight = 0;
    int    i            = 0;

    for (i = 0; i < N; i++)
    {
        total_weight += weights[i];
    }

    double base_unit = X / total_weight;

    for (i = 0; i < N; i++)
    {
        distances[i] = base_unit * weights[i];
    }
}

void split_x_into_n_symmetrically(double X, int N, double *factors, double *distances)
{
    double *weights = (double *)malloc((size_t)N * sizeof(double));
    if (!weights)
        return;

    calculate_symmetric_weights(N, 1.0, factors, weights);
    scale_to_total(X, weights, N, distances);

    free(weights);
}

void split_x_into_n_middle(double X, int N, double middle_value, double *distances)
{
    double *weights = (double *)malloc((size_t)N * sizeof(double));
    if (!weights)
        return;

    calculate_symmetric_weights(N, middle_value, NULL, weights);
    scale_to_total(X, weights, N, distances);

    free(weights);
}
