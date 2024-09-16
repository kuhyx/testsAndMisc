#include <stdio.h>
#include <stdlib.h>

// Function to calculate symmetric weights for both even and odd N
void calculate_symmetric_weights(int N, double middle_weight, double* factors, double* weights) {
    int half_N = N / 2;
    int i;
    weights[half_N] = middle_weight;  // Middle value for symmetry

    // Calculate left side weights
    if (factors) {
        for (i = 0; i < half_N; i++) {
            if (i == 0) {
                weights[half_N - i - 1] = middle_weight + factors[i];
            } else {
                weights[half_N - i - 1] = weights[half_N - i] + factors[i];
            }
        }
    } else {
        for (i = 0; i < half_N; i++) {
            weights[half_N - i - 1] = middle_weight - (i + 1);
        }
    }

    // Mirror left side weights to right side
    for (i = 0; i < half_N; i++) {
        weights[half_N + i + 1] = weights[half_N - i - 1];
    }
}

// Function to scale the weights so that their sum is proportional to X
void scale_to_total(double X, double* weights, int N, double* distances) {
    double total_weight = 0;
    int i;

    // Calculate the total weight
    for (i = 0; i < N; i++) {
        total_weight += weights[i];
    }

    double base_unit = X / total_weight;

    // Scale weights
    for (i = 0; i < N; i++) {
        distances[i] = base_unit * weights[i];
    }
}

// Function to split X into N parts symmetrically
void split_x_into_n_symmetrically(double X, int N, double* factors, double* distances) {
    double* weights = (double*)malloc(N * sizeof(double));

    calculate_symmetric_weights(N, 1.0, factors, weights);
    scale_to_total(X, weights, N, distances);

    free(weights);
}

// Function to split X into N parts, with a specific middle value
void split_x_into_n_middle(double X, int N, double middle_value, double* distances) {
    double* weights = (double*)malloc(N * sizeof(double));

    calculate_symmetric_weights(N, middle_value, NULL, weights);
    scale_to_total(X, weights, N, distances);

    free(weights);
}

// Example usage
int main() {
    int N = 5;
    double X = 100;
    double middle_value = 5.0;
    double distances[5];

    // Example usage for split_x_into_n_middle
    split_x_into_n_middle(X, N, middle_value, distances);

    printf("Split values (with middle value = %.2f):\n", middle_value);
    for (int i = 0; i < N; i++) {
        printf("%.2f ", distances[i]);
    }
    printf("\n");

    // Example usage for split_x_into_n_symmetrically
    double factors[2] = {1.0, 2.0};
    split_x_into_n_symmetrically(X, N, factors, distances);

    printf("Split values (symmetric with factors):\n");
    for (int i = 0; i < N; i++) {
        printf("%.2f ", distances[i]);
    }
    printf("\n");

    return 0;
}
