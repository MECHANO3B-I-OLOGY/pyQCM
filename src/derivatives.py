"""
Derivative calculation utilities for pyQCM.

This module provides `calculate_derivative`, which uses Savitzky-Golay
filtering to smooth the signal and estimate the derivative in one step.
Returns both the smoothed data and its derivative.
"""
from typing import Sequence, Tuple, Optional

import numpy as np


def seconds_to_window_length(seconds: float, x_arr: np.ndarray, y_len: int, min_window: int = 3) -> int:
    """Convert a window length given in seconds to an odd integer sample window.

    Args:
        seconds: desired window size in seconds (must be > 0)
        x_arr: the time/sample axis as a numpy array
        y_len: length of the signal (used to cap the window)
        min_window: minimum window length in samples (odd)

    Returns:
        An odd integer window length suitable for Savitzky-Golay.
    """
    if seconds is None:
        return min_window
    try:
        if len(x_arr) > 1:
            delta = float(np.median(np.diff(x_arr)))
        else:
            delta = 1.0
    except Exception:
        delta = 1.0

    if delta <= 0:
        delta = 1.0

    # approximate number of samples for the requested seconds
    window = int(max(min_window, round(float(seconds) / delta)))
    if window % 2 == 0:
        window += 1
    # cap to available data length
    if window > y_len:
        window = y_len if (y_len % 2 == 1) else max(3, y_len - 1)
    if window < min_window:
        window = min_window
    return int(window)


def calculate_derivative(y: Sequence, x: Sequence = None, method: str = 'savgol', smooth_window_seconds: Optional[float] = 3) -> Tuple[np.ndarray, np.ndarray]:
    """Calculate smoothed data and derivative using Savitzky-Golay.

    Returns:
        Tuple of (smoothed_data, derivative) where both are np.ndarray.

    Savitzky-Golay derivative estimate:
        f'(x_i) is estimated by fitting a local polynomial of degree `polyorder`
        over a moving window and analytically differentiating that polynomial.
        The smoothed signal is also returned for visualization.

    This is usually a good choice for noisy, smooth data because it reduces
    noise while computing the derivative directly.
    """
    try:
        y_arr = np.asarray(y, dtype=float)
    except Exception:
        y_arr = np.array([])

    if len(y_arr) == 0:
        return np.array([]), np.array([])

    if x is None:
        x_arr = np.arange(len(y_arr), dtype=float)
    else:
        try:
            x_arr = np.asarray(x, dtype=float)
        except Exception:
            x_arr = np.arange(len(y_arr), dtype=float)

    x_len = len(x_arr)
    y_len = len(y_arr)

    # determine window in samples either from seconds or fallback to default samples
    if smooth_window_seconds is not None:
        smooth_window = seconds_to_window_length(smooth_window_seconds, x_arr, y_len)
    else:
        smooth_window = 15

    print(
        f"derivatives.calculate_derivative called (y_len={y_len}, x_len={x_len}, method={method}, smooth_window_seconds={smooth_window_seconds}, smooth_window={smooth_window})"
    )

    if method != 'savgol':
        raise ValueError(f"Unsupported derivative method: {method}")

    if y_len < 3:
        if y_len < 2:
            return np.zeros_like(y_arr), np.zeros_like(y_arr)
        dx = x_arr[1] - x_arr[0]
        deriv = np.array([(y_arr[1] - y_arr[0]) / dx, (y_arr[1] - y_arr[0]) / dx])
        return y_arr, deriv

    polyorder = min(3, smooth_window - 1)
    if x_len > 1:
        delta = float(np.median(np.diff(x_arr)))
    else:
        delta = 1.0

    try:
        from scipy.signal import savgol_filter
        # Compute smoothed data (deriv=0)
        y_smooth = savgol_filter(
            y_arr,
            window_length=smooth_window,
            polyorder=polyorder,
            deriv=0,
            mode='interp',
        )
        # Compute derivative (deriv=1)
        dy = savgol_filter(
            y_arr,
            window_length=smooth_window,
            polyorder=polyorder,
            deriv=1,
            delta=delta,
            mode='interp',
        )
        return y_smooth, dy
    except Exception as exc:
        print(f"derivatives.calculate_derivative falling back to np.gradient because Savitzky-Golay failed: {exc}")
        # Fallback: try to smooth with gradient
        y_smooth = y_arr  # Just return raw if smoothing fails
        dy = np.gradient(y_arr, x_arr)
        return y_smooth, dy
