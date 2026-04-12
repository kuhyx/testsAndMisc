#ifndef SPLIT_H
#define SPLIT_H

void calculate_symmetric_weights(int N, double middle_weight, const double *factors,
                                 double *weights);

void scale_to_total(double X, const double *weights, int N, double *distances);

void split_x_into_n_symmetrically(double X, int N, double *factors, double *distances);

void split_x_into_n_middle(double X, int N, double middle_value, double *distances);

#endif
