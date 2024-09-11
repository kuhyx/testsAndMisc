def split_x_into_n_symmetrically(X, N, factors):
    """
    X: Total value to distribute
    N: Number into which we split
    factors: List controlling the difference in weights between consecutive days
             Must have length of N // 2 (if N is odd) or (N // 2 - 1) (if N is even)
    """
    
    # Calculate the mid-point index (for both even and odd N)
    half_N = N // 2
    
    # Generate the base weights symmetrically around the middle
    if N % 2 == 0:  # Even number of days
        middle_weight = 1
        weights_left = [middle_weight]
        for factor in factors:
            next_weight = weights_left[-1] + factor
            weights_left.append(next_weight)
        weights = weights_left[::-1] + weights_left
    else:  # Odd number of days
        middle_weight = 1
        weights_left = [middle_weight]
        for factor in factors:
            next_weight = weights_left[-1] + factor
            weights_left.append(next_weight)
        weights = weights_left[::-1] + [middle_weight] + weights_left

    total_weight = sum(weights)

    # Calculate the base unit
    base_unit = X / total_weight

    # Calculate the distance for each day
    distances = [base_unit * weight for weight in weights]

    return distances

def split_x_into_n_middle(X, N, middle_value):
    """
    X: Total value to distribute
    N: Number in which we split
    middle_value: Value of the middle number (the biggest weight)
    """
    
    # Calculate the mid-point index
    half_N = N // 2

    # Initialize the weights list
    weights = [0] * N

    # Set the middle value
    if N % 2 == 0:  # Even number of days
        weights[half_N - 1] = middle_value
        weights[half_N] = middle_value
    else:  # Odd number of days
        weights[half_N] = middle_value

    # Fill in the decreasing values symmetrically
    for i in range(half_N):
        # Decrease the weight by 1 for each step toward the edges
        if N % 2 == 0:
            weights[half_N - 1 - i - 1] = middle_value - (i + 1)
            weights[half_N + i + 1] = middle_value - (i + 1)
        else:
            weights[half_N - i - 1] = middle_value - (i + 1)
            weights[half_N + i + 1] = middle_value - (i + 1)

    # Sum the weights and calculate the base unit
    total_weight = sum(weights)
    
    # Calculate the base unit
    base_unit = X / total_weight

    # Calculate the distance for each day
    distances = [base_unit * weight for weight in weights]

    return distances
