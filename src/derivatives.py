"""
Derivative calculation utilities for pyQCM.

This module provides `calculate_derivative` which approximates the derivative
using the central difference formula
"""
from typing import Sequence
import numpy as np


def calculate_derivative(y: Sequence, x: Sequence = None, method: str = 'central_difference') -> np.ndarray:
    """Calculate approximate derivative using the central difference formula.

    Central Difference Formula:
        f'(x_i) ≈ (f(x_{i+1}) - f(x_{i-1})) / (2 * Δx)

    Where:
        - f(x_{i+1}) is the function value at the next point
        - f(x_{i-1}) is the function value at the previous point
        - Δx is the spacing between consecutive x-values

    For uniform spacing: Δx = x[i+1] - x[i]
    For non-uniform spacing: Δx = (x[i+1] - x[i-1]) / 2
    Args:
        y: sequence of y-values (array-like)
        x: sequence of x-values (array-like). If None, assumes uniform spacing (Δx=1)
        method: derivative method (currently 'central_difference' only)

    Returns:
        numpy.ndarray: approximate dy/dx with same length as input y.
        First and last points use forward/backward difference.
    """
    try:
        y_arr = np.asarray(y, dtype=float)
    except Exception:
        y_arr = np.array([])

    if len(y_arr) == 0:
        return np.array([])

    if x is None:
        x_arr = np.arange(len(y_arr), dtype=float)
    else:
        try:
            x_arr = np.asarray(x, dtype=float)
        except Exception:
            x_arr = np.arange(len(y_arr), dtype=float)

    x_len = len(x_arr)
    y_len = len(y_arr)
    print(f"derivatives.calculate_derivative called (y_len={y_len}, x_len={x_len}, method={method})")

    if method == 'central_difference':
        dy = np.zeros_like(y_arr)

        if y_len < 2:
            return dy

        if y_len == 2:
            dx = x_arr[1] - x_arr[0]
            dy[0] = (y_arr[1] - y_arr[0]) / dx
            dy[1] = dy[0]
            return dy

        for i in range(len(y_arr)):
            if i == 0:
                dx = x_arr[1] - x_arr[0]
                dy[i] = (y_arr[1] - y_arr[0]) / dx
            elif i == len(y_arr) - 1:
                dx = x_arr[i] - x_arr[i - 1]
                dy[i] = (y_arr[i] - y_arr[i - 1]) / dx
            else:
                dx = (x_arr[i + 1] - x_arr[i - 1]) / 2.0
                dy[i] = (y_arr[i + 1] - y_arr[i - 1]) / (2.0 * dx)

        return dy
    else:
        raise ValueError(f"Unsupported derivative method: {method}")
