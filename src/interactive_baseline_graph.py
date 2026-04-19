import numpy as np
import time
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


def display_interactive_plot(parent, figure=None, on_selection=None, initial_t0=0, initial_tf=1, width=6, height=4, dpi=100, motion_interval_ms=16, selection_min_x=None, selection_max_x=None):
    """Create and display an interactive matplotlib plot for selecting baseline range.

    Args:
        parent: parent Tkinter widget or window where plot will be embedded.
        figure (matplotlib.figure.Figure, optional): existing Figure object to plot.
            If None, a blank figure will be created.
        on_selection (callable, optional): callback function called with (t0, tf)
            when range is selected.
        initial_t0 (float, optional): initial x position for t0 bar.
        initial_tf (float, optional): initial x position for tf bar.
        width (int, optional): figure width in inches.
        height (int, optional): figure height in inches.
        dpi (int, optional): figure DPI (dots per inch).
        motion_interval_ms (int, optional): minimum time between processed drag
            motion events in milliseconds.
        selection_min_x (float, optional): lower x bound allowed for baseline handles.
            Defaults to minimum plotted data x value.
        selection_max_x (float, optional): upper x bound allowed for baseline handles.
            Defaults to maximum plotted data x value.

    Returns:
        tuple: (fig, ax, canvas, selected_range_dict)
    """
    if figure is None:
        fig = Figure(figsize=(width, height), dpi=dpi)
        ax = fig.add_subplot(111)
    else:
        fig = figure
        ax = fig.gca()

    # Keep bars within the plotted data x-range.
    x_starts = []
    x_ends = []
    for line in ax.lines:
        x_data = line.get_xdata()
        if len(x_data) > 0:
            x_starts.append(float(np.min(x_data)))
            x_ends.append(float(np.max(x_data)))
    min_data_x = min(x_starts) if x_starts else 0.0
    max_data_x = max(x_ends) if x_ends else min_data_x + 1.0

    min_select_x = min_data_x if selection_min_x is None else float(selection_min_x)
    max_select_x = max_data_x if selection_max_x is None else float(selection_max_x)

    # Ensure configured selector bounds include the plotted range edges when needed.
    min_select_x = min(min_select_x, min_data_x)
    max_select_x = max(max_select_x, max_data_x)

    # Guard against invalid ranges.
    if max_select_x <= min_select_x:
        max_select_x = min_select_x + 1.0

    start_value = min(max(float(min(initial_t0, initial_tf)), min_select_x), max_select_x)
    end_value = min(max(float(max(initial_t0, initial_tf)), min_select_x), max_select_x)

    # Store selected baseline points and drag state.
    selected_range = {
        "t0": start_value,
        "tf": end_value,
        "active": None,
        "span": None,
        "last_motion_time": 0.0,
    }

    t0_line = ax.axvline(x=start_value, color="green", linestyle="--", alpha=0.8, linewidth=2, zorder=3, label="t0")
    # tf should be above t0 for easier selection.
    tf_line = ax.axvline(x=end_value, color="red", linestyle="--", alpha=0.95, linewidth=2.5, zorder=4, label="tf")
    selected_range["span"] = ax.axvspan(start_value, end_value, alpha=0.2, color="blue", zorder=1)
    data_line = None
    for line in ax.lines:
        if line not in (t0_line, tf_line):
            label = line.get_label()
            if label and not label.startswith("_"):
                data_line = line
                break

    t0_line.set_label(f"t0: {int(round(start_value))} s")
    tf_line.set_label(f"tf: {int(round(end_value))} s")
    legend_handles = [t0_line, tf_line]
    if data_line is not None:
        legend_handles.insert(0, data_line)
    legend_obj = ax.legend(handles=legend_handles, loc="best", framealpha=0.75)

    def set_span_bounds(x0, x1):
        left = float(min(x0, x1))
        right = float(max(x0, x1))
        selected_range["span"].set_xy([
            [left, 0.0],
            [left, 1.0],
            [right, 1.0],
            [right, 0.0],
            [left, 0.0],
        ])

    def apply_plot_margins():
        fig.subplots_adjust(left=0.12, right=0.98, top=0.92, bottom=0.22)

    def redraw_selection(trigger_callback=False):
        selected_range["t0"] = float(min(t0_line.get_xdata()[0], tf_line.get_xdata()[0]))
        selected_range["tf"] = float(max(t0_line.get_xdata()[0], tf_line.get_xdata()[0]))
        set_span_bounds(selected_range["t0"], selected_range["tf"])
        t0_label = f"t0: {int(round(selected_range['t0']))} s"
        tf_label = f"tf: {int(round(selected_range['tf']))} s"
        t0_line.set_label(t0_label)
        tf_line.set_label(tf_label)
        if legend_obj is not None:
            texts = legend_obj.get_texts()
            t0_idx = 1 if data_line is not None else 0
            if len(texts) > t0_idx + 1:
                texts[t0_idx].set_text(t0_label)
                texts[t0_idx + 1].set_text(tf_label)
        canvas.draw_idle()
        if trigger_callback and on_selection:
            on_selection(selected_range["t0"], selected_range["tf"])

    def nearest_handle(event):
        # Use pixel distance so handle selection stays easy regardless of x-axis range.
        if event.x is None:
            return None
        tolerance_px = 12.0
        t0_value = t0_line.get_xdata()[0]
        tf_value = tf_line.get_xdata()[0]
        t0_px = ax.transData.transform((t0_value, 0.0))[0]
        tf_px = ax.transData.transform((tf_value, 0.0))[0]
        d_t0 = abs(float(event.x) - t0_px)
        d_tf = abs(float(event.x) - tf_px)
        if min(d_t0, d_tf) > tolerance_px:
            return None
        if abs(d_t0 - d_tf) <= 0.5:
            # If both handles overlap at a boundary, select the one that can move inward.
            if abs(t0_value - max_select_x) <= 1e-9 and abs(tf_value - max_select_x) <= 1e-9:
                return "t0"
            if abs(t0_value - min_select_x) <= 1e-9 and abs(tf_value - min_select_x) <= 1e-9:
                return "tf"
        # tie-break in favor of tf (above t0)
        if d_tf <= d_t0:
            return "tf"
        return "t0"

    def on_plot_press(event):
        if event.inaxes != ax or event.xdata is None:
            return
        selected_range["active"] = nearest_handle(event)
        selected_range["last_motion_time"] = 0.0

    def on_plot_motion(event):
        if selected_range["active"] is None or event.inaxes != ax or event.xdata is None:
            return

        now = time.perf_counter()
        if motion_interval_ms > 0:
            min_interval_s = motion_interval_ms / 1000.0
            if now - selected_range["last_motion_time"] < min_interval_s:
                return
        selected_range["last_motion_time"] = now

        x_value = event.xdata
        if selected_range["active"] == "t0":
            # Keep t0 <= tf
            tf_value = tf_line.get_xdata()[0]
            x_value = max(min_select_x, min(x_value, tf_value, max_select_x))
            t0_line.set_xdata([x_value, x_value])
        else:
            # Keep tf >= t0
            t0_value = t0_line.get_xdata()[0]
            x_value = min(max_select_x, max(x_value, t0_value, min_select_x))
            tf_line.set_xdata([x_value, x_value])

        redraw_selection(trigger_callback=False)

    def on_plot_release(event):
        if selected_range["active"] is not None:
            redraw_selection(trigger_callback=True)
        selected_range["active"] = None

    # Create canvas widget to embed the figure in Tkinter.
    canvas = FigureCanvasTkAgg(fig, master=parent)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.grid(row=0, column=0, sticky="nsew")

    apply_plot_margins()
    x_span = max(max_select_x - min_select_x, 1.0)
    x_padding = max(x_span * 0.02, 0.5)
    ax.set_xlim(min_select_x - x_padding, max_select_x + x_padding)
    canvas.draw()
    redraw_selection(trigger_callback=False)

    def resize_canvas(event):
        if event.width > 1 and event.height > 1:
            fig.set_size_inches(event.width / dpi, event.height / dpi, forward=True)
            apply_plot_margins()
            canvas.draw_idle()

    parent.bind("<Configure>", resize_canvas)

    # Connect drag events.
    canvas.mpl_connect("button_press_event", on_plot_press)
    canvas.mpl_connect("motion_notify_event", on_plot_motion)
    canvas.mpl_connect("button_release_event", on_plot_release)

    return fig, ax, canvas, selected_range
