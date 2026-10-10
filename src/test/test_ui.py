'''
THIS SCRIPT IS A WORK IN PROGRESS
Currently only tests UI, will implement others soon
'''

import pytest
from unittest.mock import patch
import sys
import os
import tkinter as tk
from tkinter import ttk

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from main import App, Col1, Col2, Col3, Col4
from src.ui_text import ui_text, ascii_equivalent, can_render
import tkinter.font as tkfont

@pytest.fixture
def app():
    print("Testing UI functionality")
    app = App()
    app.update()  # Process any pending events
    yield app
    print("UI tests are done, closing the app...")
    app.quit()
    app.update_idletasks()
    app.destroy()

def test_ui_spawns(app):
    # Ensure title is correct
    assert app.title() == "BraTaDio - pyQCM-D Analyzer"
        
    # Check if random intvar is correctly initialized
    assert isinstance(app.int_plot_data_fmt_var, tk.IntVar)
    assert app.int_plot_data_fmt_var.get() == -1
    
    # Check if main container frame exists
    container = app.nametowidget(app.children['!frame'])
    assert isinstance(container, tk.Frame)

    # Check if the scrollbars exist and are configured correctly
    assert isinstance(app.scrollbarX, ttk.Scrollbar)
    assert str(app.scrollbarX.cget('orient')) == 'horizontal'
    assert isinstance(app.scrollbarY, ttk.Scrollbar)
    assert str(app.scrollbarY.cget('orient')) == 'vertical'

    # Check if Col1 is correctly initialized
    col1 = app.frames[Col1]
    assert isinstance(col1, Col1)
    assert col1.is_visible == True
    assert col1.col_position == 0
    assert col1.filename_label.cget('text') == "Data file"

    # Check btn of Col1
    assert hasattr(col1, 'browse_files_button')
    assert isinstance(col1.browse_files_button, tk.Button)
    assert col1.browse_files_button.cget('text') == "Select data file"

    # Simulate button click and check the file dialog
    with patch('tkinter.filedialog.askopenfilename', return_value="test_file.txt"):
        col1.browse_files_button.invoke()
        col1.update()
        assert col1.filename_label.cget('text').__contains__("test_file.txt")
    
    # Check if Col2 is correctly initialized
    col2 = app.frames[Col2]
    assert isinstance(col2, Col2)
    assert col2.is_visible == True
    assert col2.col_position == 1
    assert col2.which_raw_channels_label.cget('text') == "Select overtones for full data"
    
    # Simulate checkbox click and check if other boxes show
    assert isinstance(col2.plot_raw_data_check, tk.Checkbutton)
    assert col2.plot_raw_data_check.cget('text') == 'Raw Data Overtone Selection\n(f and D)'
    col2.plot_raw_data_var.set(True)
    assert col2.raw_checks[0].checkbutton.cget('text') == '1st frequency'

    # Check if Col3 is correctly initialized
    col3 = app.frames[Col3]
    assert isinstance(col3, Col3)
    assert col3.is_visible == True
    assert col3.col_position == 2
    assert col3.which_clean_channels_label.cget('text') == "Select overtones for\nbaseline corrected data"
    
    # Simulate checkbox click and check if other boxes show
    assert isinstance(col3.plot_clean_data_check, tk.Checkbutton)
    assert col3.plot_clean_data_check.cget('text') == ui_text('Shifted Data Overtone Selection\n(Δf and ΔD)')
    col3.plot_clean_data_var.set(True)
    assert col3.clean_checks[0].checkbutton.cget('text') == '1st frequency'
    
    # Check if Col4 is correctly initialized
    col4 = app.frames[Col4]
    assert isinstance(col4, Col4)
    assert col4.is_visible == True
    assert col4.col_position == 3
    assert col4.plot_options_label.cget('text') == "Options For Plots"
    assert isinstance(col4.plot_temp_v_time_check, tk.Checkbutton)
    assert col4.plot_temp_v_time_check.cget('text') == "Plot temperature vs time"
    assert isinstance(col4.open_model_window_button, tk.Button)
    assert col4.open_model_window_button.cget('text') == "Modelling"

    # test button opens new window
    col4.open_model_window_button.invoke()
    col4.update()
    col4.modelling_window.test_modelling_window() # will fail if modelling window didn't open


def test_special_chars_drawable_or_ascii(app):
    # every special character used in the UI must either be drawable by this Tk, or be replaced with ASCII
    # (some Linux Tk builds can only use X11 core fonts and would otherwise show e.g. 'Δf' for 'Δf')
    font = tkfont.nametofont('TkDefaultFont')
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
    ui_sources = [os.path.join(root_dir, 'main.py'), os.path.join(root_dir, 'src', 'Exceptions.py')]
    special_chars = {ch for fp in ui_sources for ch in open(fp, encoding='utf-8').read() if not ch.isascii()}
    for ch in special_chars:
        shown = ui_text(ch)
        if can_render(ch, font):
            assert shown == ch
        else:
            assert shown.isascii(), f"{ch!r} cannot be drawn by this Tk and has no ASCII fallback"

def test_ascii_equivalents():
    assert ascii_equivalent('Δ') == 'Delta '
    assert ascii_equivalent('²') == '^2'
    assert ascii_equivalent('é') == 'e'
    assert ascii_equivalent('☃') == '?'


if __name__ == "__main__":
    pytest.main()