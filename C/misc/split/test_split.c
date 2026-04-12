#include <assert.h>
#include <math.h>
#include <stdio.h>

#include "split.h"

#define EPSILON 1e-9

static void assert_close(double a, double b) { assert(fabs(a - b) < EPSILON); }

static double sum_array(const double *arr, int n)
{
    double s = 0;
    for (int i = 0; i < n; i++)
    {
        s += arr[i];
    }
    return s;
}

/* calculate_symmetric_weights: with factors, odd N */
static void test_symmetric_weights_with_factors_odd(void)
{
    double weights[5];
    double factors[2] = {1.0, 2.0};

    calculate_symmetric_weights(5, 1.0, factors, weights);

    /* middle = 1.0 */
    assert_close(weights[2], 1.0);
    /* i=0: weights[1] = middle + factors[0] = 2.0 */
    assert_close(weights[1], 2.0);
    /* i=1: weights[0] = weights[1] + factors[1] = 4.0 */
    assert_close(weights[0], 4.0);
    /* mirror: weights[3] = weights[1] = 2.0, weights[4] = weights[0] = 4.0 */
    assert_close(weights[3], 2.0);
    assert_close(weights[4], 4.0);
}

/* calculate_symmetric_weights: with factors, even N */
static void test_symmetric_weights_with_factors_even(void)
{
    double weights[4];
    double factors[2] = {0.5, 1.5};

    calculate_symmetric_weights(4, 3.0, factors, weights);

    /* half_N = 2, middle index = 2 */
    assert_close(weights[2], 3.0);
    /* i=0: weights[1] = 3.0 + 0.5 = 3.5 */
    assert_close(weights[1], 3.5);
    /* i=1: weights[0] = weights[1] + 1.5 = 5.0 */
    assert_close(weights[0], 5.0);
    /* mirror: weights[3] = weights[1] = 3.5 */
    assert_close(weights[3], 3.5);
}

/* calculate_symmetric_weights: without factors (NULL), odd N */
static void test_symmetric_weights_null_factors_odd(void)
{
    double weights[5];

    calculate_symmetric_weights(5, 5.0, NULL, weights);

    /* middle = 5.0 */
    assert_close(weights[2], 5.0);
    /* i=0: weights[1] = 5.0 - 1 = 4.0 */
    assert_close(weights[1], 4.0);
    /* i=1: weights[0] = 5.0 - 2 = 3.0 */
    assert_close(weights[0], 3.0);
    /* mirror */
    assert_close(weights[3], 4.0);
    assert_close(weights[4], 3.0);
}

/* calculate_symmetric_weights: without factors, even N */
static void test_symmetric_weights_null_factors_even(void)
{
    double weights[6];

    calculate_symmetric_weights(6, 10.0, NULL, weights);

    /* half_N = 3, middle index = 3 */
    assert_close(weights[3], 10.0);
    /* i=0: weights[2] = 10.0 - 1 = 9.0 */
    assert_close(weights[2], 9.0);
    /* i=1: weights[1] = 10.0 - 2 = 8.0 */
    assert_close(weights[1], 8.0);
    /* i=2: weights[0] = 10.0 - 3 = 7.0 */
    assert_close(weights[0], 7.0);
    /* mirror */
    assert_close(weights[4], 9.0);
    assert_close(weights[5], 8.0);
}

/* calculate_symmetric_weights: N=1 (half_N=0, loops don't execute) */
static void test_symmetric_weights_n1(void)
{
    double weights[1];

    calculate_symmetric_weights(1, 42.0, NULL, weights);
    assert_close(weights[0], 42.0);

    double factors[1] = {99.0};
    calculate_symmetric_weights(1, 7.0, factors, weights);
    assert_close(weights[0], 7.0);
}

/* scale_to_total: verify distances sum to X */
static void test_scale_to_total(void)
{
    double weights[3]   = {1.0, 2.0, 1.0};
    double distances[3] = {0};

    scale_to_total(100.0, weights, 3, distances);

    assert_close(sum_array(distances, 3), 100.0);
    /* total_weight = 4, base_unit = 25 */
    assert_close(distances[0], 25.0);
    assert_close(distances[1], 50.0);
    assert_close(distances[2], 25.0);
}

/* scale_to_total: single element */
static void test_scale_to_total_single(void)
{
    double weights[1]   = {5.0};
    double distances[1] = {0};

    scale_to_total(200.0, weights, 1, distances);
    assert_close(distances[0], 200.0);
}

/* split_x_into_n_symmetrically: N=5 with factors */
static void test_split_symmetrically(void)
{
    double factors[2]   = {1.0, 2.0};
    double distances[5] = {0};

    split_x_into_n_symmetrically(100.0, 5, factors, distances);

    /* weights: [4, 2, 1, 2, 4] => total=13, base_unit=100/13 */
    assert_close(sum_array(distances, 5), 100.0);
    /* symmetry */
    assert_close(distances[0], distances[4]);
    assert_close(distances[1], distances[3]);
    /* middle is smallest */
    assert(distances[2] < distances[1]);
    assert(distances[1] < distances[0]);
}

/* split_x_into_n_symmetrically: N=3 with factors */
static void test_split_symmetrically_n3(void)
{
    double factors[1]   = {2.0};
    double distances[3] = {0};

    split_x_into_n_symmetrically(60.0, 3, factors, distances);

    assert_close(sum_array(distances, 3), 60.0);
    assert_close(distances[0], distances[2]);
}

/* split_x_into_n_middle: N=5 with middle value */
static void test_split_middle(void)
{
    double distances[5] = {0};

    split_x_into_n_middle(100.0, 5, 5.0, distances);

    assert_close(sum_array(distances, 5), 100.0);
    /* symmetry */
    assert_close(distances[0], distances[4]);
    assert_close(distances[1], distances[3]);
}

/* split_x_into_n_middle: N=3 with middle value */
static void test_split_middle_n3(void)
{
    double distances[3] = {0};

    split_x_into_n_middle(90.0, 3, 10.0, distances);

    assert_close(sum_array(distances, 3), 90.0);
    assert_close(distances[0], distances[2]);
}

/* split_x_into_n_middle: N=1 */
static void test_split_middle_n1(void)
{
    double distances[1] = {0};

    split_x_into_n_middle(50.0, 1, 7.0, distances);
    assert_close(distances[0], 50.0);
}

int main(void)
{
    test_symmetric_weights_with_factors_odd();
    test_symmetric_weights_with_factors_even();
    test_symmetric_weights_null_factors_odd();
    test_symmetric_weights_null_factors_even();
    test_symmetric_weights_n1();
    test_scale_to_total();
    test_scale_to_total_single();
    test_split_symmetrically();
    test_split_symmetrically_n3();
    test_split_middle();
    test_split_middle_n3();
    test_split_middle_n1();

    printf("All tests passed.\n");
    return 0;
}
