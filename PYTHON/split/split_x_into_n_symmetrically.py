def calculate_symmetric_weights(N, middle_weight, factors=None):
    """Calculate symmetric weights for both even and odd N.

    N: Number in which to split.
    middle_weight: The middle value for symmetry.
    factors: If provided, controls the difference in weights (used for the `split_x_into_n_symmetrically` function).
             Must have length N // 2 or N // 2 - 1 depending on N.
    """
    half_N = N // 2
    weights_left = [middle_weight]

    if factors:
        for factor in factors:
            next_weight = weights_left[-1] + factor
            weights_left.append(next_weight)
    else:
        for i in range(half_N - 1):
            weights_left.append(middle_weight - (i + 1))

    if N % 2 == 0:
        weights = weights_left[::-1] + weights_left
    else:
        weights = weights_left[::-1] + [middle_weight] + weights_left

    return weights


def scale_to_total(X, weights):
    """Scale the weights so that their sum is proportional to X.

    X: Total value to distribute.
    weights: The list of weights to be scaled.
    """
    total_weight = sum(weights)
    base_unit = X / total_weight
    distances = [base_unit * weight for weight in weights]

    return distances


def split_x_into_n_symmetrically(X, N, factors):
    """X: Total value to distribute.
    N: Number in which we split.
    factors: List controlling the difference in weights between consecutive days.
             Must have length of N // 2 (if N is odd) or (N // 2 - 1) (if N is even).
    """
    weights = calculate_symmetric_weights(N, middle_weight=1, factors=factors)
    return scale_to_total(X, weights)


def split_x_into_n_middle(X, N, middle_value):
    """X: Total value to distribute.
    N: Number in which we split.
    middle_value: Value of the middle number (the biggest weight).
    """
    weights = calculate_symmetric_weights(N, middle_weight=middle_value)
    return scale_to_total(X, weights)
