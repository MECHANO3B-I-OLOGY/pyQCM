"""
Placeholder derivative utilities for pyQCM.

This module provides a placeholder `calculate_derivative` function that
logs a debug message when called and returns an array of NaNs matching
the input length. Returning NaNs lets plots render with correct axes
but no visible data points.
"""
from typing import Sequence
import numpy as np


def calculate_derivative(y: Sequence, x: Sequence = None, method: str = 'placeholder') -> np.ndarray:
    """Placeholder derivative function.

    Logs a debug message and returns NaNs sized like `y`.
    """
    try:
        y_arr = np.asarray(y, dtype=float)
    except Exception:
        y_arr = np.array([])

    x_len = 0 if x is None else (len(x) if hasattr(x, '__len__') else 0)
    y_len = len(y_arr)
    print(f"derivatives.calculate_derivative called (y_len={y_len}, x_len={x_len}, method={method})")

    if y_len == 0:
        return np.array([])

    return np.full(y_arr.shape, np.nan)
