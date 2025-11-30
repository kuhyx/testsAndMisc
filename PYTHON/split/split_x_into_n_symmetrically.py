"""Distribute values symmetrically across N parts."""


def calculate_symmetric_weights(
    n: int, middle_weight: float, factors: list[float] | None = None
) -> list[float]:
    """Calculate symmetric weights for both even and odd N.

    Args:
        n: Number of parts to split into.
        middle_weight: The middle value for symmetry.
        factors: If provided, controls the difference in weights.
            Must have length n // 2 or n // 2 - 1 depending on n.

    Returns:
        List of symmetric weights.
    """
    half_n = n // 2
    weights_left: list[float] = [middle_weight]

    if factors:
        for factor in factors:
            next_weight = weights_left[-1] + factor
            weights_left.append(next_weight)
    else:
        weights_left.extend(middle_weight - (i + 1) for i in range(half_n - 1))

    if n % 2 == 0:
        weights = weights_left[::-1] + weights_left
    else:
        weights = [*weights_left[::-1], middle_weight, *weights_left]

    return weights


def scale_to_total(x: float, weights: list[float]) -> list[float]:
    """Scale the weights so that their sum is proportional to X.

    Args:
        x: Total value to distribute.
        weights: The list of weights to be scaled.

    Returns:
        List of scaled values summing to x.
    """
    total_weight = sum(weights)
    base_unit = x / total_weight
    return [base_unit * weight for weight in weights]


def split_x_into_n_symmetrically(x: float, n: int, factors: list[float]) -> list[float]:
    """Split X into N parts with symmetric weights controlled by factors."""
    weights = calculate_symmetric_weights(n, middle_weight=1, factors=factors)
    return scale_to_total(x, weights)


def split_x_into_n_middle(x: float, n: int, middle_value: float) -> list[float]:
    """Split X into N parts with symmetric weights using middle_value as peak."""
    weights = calculate_symmetric_weights(n, middle_weight=middle_value)
    return scale_to_total(x, weights)
