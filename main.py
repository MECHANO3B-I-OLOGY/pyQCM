"""
Author: Brandon Pardi
Created: 9/7/2022, 1:53 pm
Last Modified: 1/4/2024
"""

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import sys
import os
from datetime import time
from tkinter import colorchooser
import json
import pandas as pd
import numpy as np
from pathlib import Path
import subprocess
import platform

import src.Exceptions as Exceptions
from src.analyze import analyze_data, ordinal
from src.format_file import format_raw_data
from src.modeling import thin_film_liquid_analysis, thin_film_air_analysis, sauerbrey, avgs_analysis, gordon_kanazawa, crystal_thickness

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller.
    Checks current working directory first (allows user-modified files to take precedence),
    then falls back to the PyInstaller bundle directory (sys._MEIPASS) or the source directory.
    """
    cwd_path = os.path.join(os.getcwd(), relative_path)
    if os.path.exists(cwd_path):
        return cwd_path
    try:
        base_path = sys._MEIPASS  # PyInstaller extracts bundled files here
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

'''Variable Initializations'''
class Input:
    """this object will contain all the input dictated by user, and any information needed by subsequent analysis/modelling functions
    """    
    def __init__(self): 
        self.file = ''
        self.calibration_file = ''
        self.will_plot_raw_data = False
        self.will_plot_clean_data = False
        self.will_overwrite_file = False # if user wants copy of data data saved after processing
        self.abs_base_t0 = time(0, 0, 0) # beginning of baseline time
        self.abs_base_tf = time(0, 0, 0) # end of baseline time
        self.rel_t0 = 0 # beginning of baseline time
        self.rel_tf = 0 # end of baseline time
        self.fig_format = 'png' # format to save figures that can be changed in the gui to tiff or pdf
        self.x_timescale = 's' # change scale of time of x axis of plots from seconds to either minutes or hours
        self.will_plot_dF_dD_together = False # indicates if user selected multi axis plot of dis and freq
        self.will_normalize_F = False # indicates if user selected to normalize frequency data
        self.will_plot_dD_v_dF = False # indicates if user selected to plot change in dis vs change in freq
        self.interactive_plot_data_fmt = {'raw': False, 'clean': False} # indicates which data user wants to interactive plot
        self.submit_pressed = False # submitting gui data the first time has different implications than if resubmitting
        self.enable_interactive_plot = False
        self.which_range_selecting = {'raw': '', 'clean': ''} # which range of the interactive plot is about to be selected
        self.interactive_plot_overtone = {'raw': 0, 'clean': 0} # which overtones for clean and raw
        self.range_frame_flag = False
        self.first_run = True
        self.latex_installed = False
        self.will_use_theoretical_vals = True
        self.calibration_data_from_file = False
        self.will_plot_temp_v_time = False
        self.will_correct_slope = False
        self.will_calculate_offset = False
        self.is_qsd = False # True if data file being processed is a raw qsd file
        self.is_relative_time = False # depending on file src input, some machines record time relatively (start at 0) or absolutely (start at current time of day)
        self.file_src_type = '' # different machines output data differently
        self.which_plot = {'raw': {'fundamental_freq': False, 'fundamental_dis': False, '3rd_freq': False, '3rd_dis': False,
                            '5th_freq': False, '5th_dis': False, '7th_freq': False, '7th_dis': False,
                            '9th_freq': False, '9th_dis': False, '11th_freq': False, '11th_dis': False,
                            '13th_freq': False, '13th_dis': False},

                    'clean': {'fundamental_freq': False, 'fundamental_dis': False, '3rd_freq': False, '3rd_dis': False,
                            '5th_freq': False, '5th_dis': False, '7th_freq': False, '7th_dis': False,
                            '9th_freq': False, '9th_dis': False, '11th_freq': False, '11th_dis': False,
                            '13th_freq': False, '13th_dis': False}}

input = Input()

INPUT_ALTERED_FLAG = False

def set_input_altered_flag(flag, notif=True):
    """function to set global flag when anything in UI has been altered
    this is used to avoid rerunning the same calculations if user didn't change anything in UI

    Args:
        flag (bool): bool for what to set the flag too
        notif (bool, optional): used to determine if user should be notified. Defaults to True.
    """    
    global input
    global INPUT_ALTERED_FLAG
    if not INPUT_ALTERED_FLAG and notif:
        print("Input altered, will run calculations")
    INPUT_ALTERED_FLAG = flag

def open_folder(folder_path):
    if platform.system() == 'Windows': # windows
        os.startfile(folder_path)
    elif platform.system() == 'Darwin':  # macOS
        subprocess.run(['open', folder_path])        
    elif platform.system() == 'Linux':  # Linux
        subprocess.run(['xdg-open', folder_path])

def validate_integer(P):
    # This function checks if the input is an integer
    if P == "" or P.isdigit():
        return True
    else:
        msg = "Warning: Please enter a valid positive integer"
        Exceptions.warning_popup(msg)
        return False

def validate_overtone_num(P):
    # Check if the input is an odd integer between 1 and 13
    if P == "":
        return True
    if P.isdigit():
        value = int(P)
        if 1 <= value <= 13 and value % 2 != 0:
            return True
    msg = "Warning: Please enter a valid overtone number\n(odd numbers 1-13)"
    Exceptions.warning_popup(msg)
    return False

def browse_files(file_dir, btn_title):
    """prompts user with file explorer window to select data file

    Args:
        file_dir (_type_): local file data path (relative to main.py)
        btn_title (_type_): title for btn: 'Select data file'

    Returns:
        _type_: returns global file path to where data file selected
    """    
    fp = filedialog.askopenfilename(initialdir=os.path.join(os.getcwd(), file_dir),
                                          title=btn_title,
                                          filetypes=(("Comma Separated Value files", "*.csv"),
                                                    ("Excel file 2007 and later", "*.xlsx"),
                                                    ("Excel file 1997-2003", "*.xls"),
                                                    ("Open XML", "*.xlsm"),
                                                    ("Text file", "*.txt"),
                                                    ("QSense Raw file", "*.qsd")))
    
    return fp

def select_data_file(label):
    """prompted when button clicked to browse for data file

    Args:
        label (tk.Label): tkinter label object to display the file path/name chosen
    """    
    global input
    fp = browse_files('raw_data', 'Select data file')
    input.file = fp
    input.is_qsd = True if os.path.splitext(fp)[1] == '.qsd' else False
    print(input.is_qsd)
    label.configure(text=f"File selected: {os.path.basename(fp)}")
    print(input.file)

def create_checkboxes(frame, cleanliness):
    """utility function to create all the checkboxes for columns 2 and 3 iteratively

    Args:
        frame (tk.Frame): tkinter frame for the column that the checkboxes will be put in
        cleanliness (str): indicates if this will be the raw or clean column

    Returns:
        list: list of tk.Checkbutton objects
    """    
    keys = list(input.which_plot[cleanliness].keys())
    checks = []
    for i in range(14):
        # assign correct overtone and determine if frequency or dissipation
        overtone = (i+1) % 2
        f_or_d = ''
        key = (cleanliness, keys[i])
        if overtone == 1:
            overtone = i+1
            f_or_d = 'frequency'
        else: 
            overtone = i
            f_or_d = 'dissipation'

        text = ordinal(overtone) + ' ' + f_or_d
        intvar = tk.IntVar()
        if cleanliness == 'raw':
            cb = tk.Checkbutton(frame, text=text, variable=intvar, onvalue=1, offvalue=0, command=frame.receive_raw_checkboxes)
        else:
            cb = tk.Checkbutton(frame, text=text, variable=intvar, onvalue=1, offvalue=0, command=frame.receive_clean_checkboxes)

        check = CheckBox(intvar, cb, key)
        checks.append(check)

    return checks

def generate_labelled_entries(frame):
    """similar to generate checboxes, but generates pairs of label and entry object
    primary use is for calibration value input window

    Args:
        frame (tk.Frame): tkinter Frame that these objects will be rendered to

    Returns:
        list of LabelledEntry objects: labelled entry objects are just convenient ways to represent the pairs of labels/entries
    """
    keys = list(input.which_plot['clean'].keys())
    labelled_entries = []
    for i in range(14): # 7 different overtones each with freq and dis
        overtone = (i+1) % 2
        key = keys[i]
        overtone = i+1 if overtone == 1 else i
        f_or_d = 'frequency' if overtone == i+1 else 'dissipation'
        text = ordinal(overtone) + ' ' + f_or_d
        label = tk.Label(frame, text=text)
        entry = tk.Entry(frame)
        labelled_entries.append(LabelledEntry(label, entry))

    return labelled_entries

def receive_int_plot_input(intvar):
    """receives input of the interactive plot Frame of the UI
    frame only visible upon click radiobutton for interactive plot in cols 2 or 3

    Args:
        int_plot_input (tuple): self (column class), frame containing inputs of int plot,
    intvar (Tk.IntVar holds status selected buttons),
    prev_frame (Tk.Frame) int plot input frame for column previously selected (if selecting int plot col2 this will be col3 if col3 int plot was previously selected)
    """    
    global input
    print(intvar.get(), input.enable_interactive_plot)
    if intvar.get() == 1: # if raw data curv
        input.interactive_plot_data_fmt['raw'] = True
        input.interactive_plot_data_fmt['clean'] = False
        input.range_frame_flag = True
    elif intvar.get() == 2:
        input.interactive_plot_data_fmt['clean'] = True
        input.interactive_plot_data_fmt['raw'] = False
        input.range_frame_flag = False
    print(input.interactive_plot_data_fmt)


# expects input in the form of a list with alternate freq, FWHM as depicted in the UI for selections
def convert_FWHM(calibration_vals):
    """DEPRECATED
    used to convert values entered by user from full width half max to dissipation if indicated by user

    Args:
        calibration_vals (list of floats): contains values entered by user in offset window

    Returns:
        (list of floats): converted values from FWHM to dissipation
    """
    converted_vals = []
    for i, val in enumerate(calibration_vals):
        if val == 0:
            converted_vals.append(0)
        if i % 2 == 1: # only need to adjust dissipation values from FWHM
            rf = calibration_vals[i-1]
            if rf == 0:
                calibration_vals.append(np.nan)
            fwhm = val
            dis = fwhm / rf
            converted_vals.append(dis)
        else:
            converted_vals.append(val)
    
    return converted_vals

def err_check():
    """checks as many errors as possible prior to calling analyze_data routine
    typically erroneous user inputs
    """    
    global input
    '''Verify File Info'''
    # make sure file name was inputted
    if (input.file == ''):
        msg = "WARNING: No data file was selected"
        print(msg)
        Exceptions.warning_popup(msg)

    # verify baseline time entered, if only raw data box checked, no need to base time
    if (not input.is_relative_time and input.will_plot_clean_data) and input.abs_base_t0 == time(0,0,0) and input.abs_base_tf == time(0,0,0):
        msg = "WARNING: No baseline time was entered"
        print(msg)
        Exceptions.warning_popup(msg)

    # verify data checks
    # find num channels tested
    clean_num_channels_tested = 0
    raw_num_channels_tested = 0

    for channel in input.which_plot['raw'].items():
        if channel[1] == True:
            raw_num_channels_tested += 1

    for channel in input.which_plot['clean'].items():
        if channel[1] == True:
            clean_num_channels_tested += 1

    total_num_channels_tested = raw_num_channels_tested + clean_num_channels_tested
    # check if any channels were selected to test
    if total_num_channels_tested == 0:
        msg = "WARNING: User indicated to plot raw channels,\ndid not indicate which"
        print(msg)
        Exceptions.error_popup(msg)

    # check if clean data was chosen, but no clean channels selected
    if input.will_plot_clean_data and clean_num_channels_tested == 0:
        msg = "WARNING: User indicated to plot clean channels,\ndid not indicate which"
        print(msg)
        Exceptions.error_popup(msg)

    # check if raw data was chosen, but no raw data was selected
    if input.will_plot_raw_data and raw_num_channels_tested == 0:
        msg = "WARNING: User indicated to plot raw channels,\ndid not indicate which"
        print(msg)
        Exceptions.error_popup(msg)

    # verify options
    if input.x_timescale == 'u':
        msg = "WARNING: User indicated to change timescale,\nbut did not specify what scale"
        print(msg)
        Exceptions.error_popup(msg)

    if input.fig_format == 'u':
        msg = "WARNING: User indicated to change fig format,\nbut did not specify which"
        print(msg)
        Exceptions.error_popup(msg)

class App(tk.Tk):
    """parent class of the UI

    Args:
        tk (TK): inherits the Tkinter class
    """    
    def __init__(self):
        super().__init__() # initialize parent class for the child

        self.title('BraTaDio - pyQCM-D Analyzer')
        try:
            self.iconphoto(False, tk.PhotoImage(file=resource_path("res/m3b_comp.png")))
        except:
            pass
        self.geometry("1200x800")
        #self.configure(bg=DARKEST)
        #self.tk_setPalette(background=DARKEST, foreground=WHITE)

        # Integer Variable for selecting radio button of interactive plot for either raw or clean data
        # 0 raw, 1 clean
        self.int_plot_data_fmt_var = tk.IntVar()
        self.int_plot_data_fmt_var.set(-1)

        # defining containers
        container = tk.Frame(self)
        container.pack(side='top', fill='both', expand=True)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

        # scrollbar
        self.app_canvas = tk.Canvas(container)
        self.scrollbarX = ttk.Scrollbar(container, orient='horizontal', command=self.app_canvas.xview)
        self.scrollbarX.pack(side='bottom', fill='x')
        self.scrollbarY = ttk.Scrollbar(container, orient='vertical', command=self.app_canvas.yview)
        self.scrollbarY.pack(side='right', fill='y')
        self.app_canvas.pack(side='left', fill='both', expand=True)
        self.app_canvas.configure(yscrollcommand=self.scrollbarY.set, xscrollcommand=self.scrollbarX.set)
        
        self.inner_frame = tk.Frame(self.app_canvas)
        self.inner_frame.bind("<Configure>", lambda event: self.update_app_scrollregion())
        self.app_canvas.create_window((0,0), window=self.inner_frame, anchor='nw')
        self.inner_frame.bind("<Enter>", self.bind_app_mousewheel)
        self.inner_frame.bind("<Leave>", self.unbind_app_mousewheel)
        
        # properly handle window closing
        self.protocol("WM_DELETE_WINDOW", self.on_exit)

        # Initialize frames
        self.frames = {}
        self.col1 = Col1(self, self.inner_frame)  # Pass self (App) as parent to Col1
        self.frames[Col1] = self.col1
        self.col2 = Col2(self, self.inner_frame)  # Pass self (App) as parent to Col2
        self.frames[Col2] = self.col2
        self.col3 = Col3(self, self.inner_frame)  # Pass self (App) as parent to Col3
        self.frames[Col3] = self.col3
        self.col4 = Col4(self, self.inner_frame)  # Pass self (App) as parent to Col4
        self.frames[Col4] = self.col4

        # Define and grid frames using grid (not pack)
        for f in [self.col1, self.col2, self.col3, self.col4]:
            frame = f
            frame.grid(row=0, column=frame.col_position, sticky='nw')
        
        # intialize calibration window to be opened later
        self.calibration_window = CalibrationWindow

        # intialize modeling window to be opened later
        #self.modeling_window = ModelingWindow

        # initialize plot customizations with previously saved values
        self.plot_opts_window = PlotOptsWindow

        with open(resource_path('plot_opts/plot_customizations.json'), 'r') as fp:
            self.options = json.load(fp)
        self.prev_opts = self.options

    def repack_frames(self):
        """used to refresh the frames when needed
        """        
        for frame in self.frames:
            frame = self.frames[frame]
            if frame.is_visible:
                print(frame)
                frame.grid(row=0, column=frame.col_position, sticky = 'nsew')
            else:
                frame.grid_forget()

    def on_exit(self):
        self.quit()
        self.destroy()
        sys.exit()

    def bind_app_mousewheel(self, event):
        self.app_canvas.bind_all("<MouseWheel>", self.on_app_mousewheel)
        
    def unbind_app_mousewheel(self, event):
        self.app_canvas.unbind_all("<MouseWheel>")

    def on_app_mousewheel(self, event):
        self.app_canvas.yview_scroll(int(-1*(event.delta/100)), "units")

    def update_app_scrollregion(self):
        self.app_canvas.configure(scrollregion=self.app_canvas.bbox("all"))

    def update_opts_scrollregion(self, event):
        self.plot_opts_window.update_opts_scrollregion(self, event)

    def update_calibration_scrollregion(self, event):
        self.calibration_window.update_calibration_scrollregion(self, event)

    def open_plot_opts_window(self):
        self.plot_opts_window.open_opts_window(self)
        self.plot_opts_window.fill_opts_window(self)

    def force_resize(self):
        self.plot_opts_window.force_resize(self)

    def open_calibration_window(self):
        self.calibration_window.open_calibration_window(self)
        self.calibration_window.fill_calibration_window(self)

    def handle_offset_radios(self):
        self.calibration_window.handle_offset_radios(self)

    def clear_selections(self):
        self.calibration_window.clear_selections(self)

    def confirm_values(self):
        self.calibration_window.confirm_values(self)

    def open_model_window(self):
        self.modeling_window.open_modeling_window(self)
        self.modeling_window.fill_modeling_window(self)

    def test_model_window(self):
        self.modeling_window.test_modelling_window(self)

    def choose_color(self, ov_num):
        self.plot_opts_window.choose_color(self, ov_num)

    def receive_scale_radios(self):
        self.plot_opts_window.receive_scale_radios(self)

    def receive_file_format_radios(self):
        self.plot_opts_window.receive_file_format_radios(self)

    def set_default_values(self):
        self.plot_opts_window.set_default_values(self)

    def confirm_opts(self):
        self.plot_opts_window.confirm_opts(self)

    def set_text(self, entry, text):
        self.plot_opts_window.set_text(self, entry, text)

    def confirm_range(self):
        self.modeling_window.confirm_range(self)

    def temp_v_time_check_state(self, file_src_type):
        print(file_src_type)
        if file_src_type in ['Qsense', 'AWSensors']:
            state = 'disable'
        else:
            state = 'enable'
        self.col4.set_plot_temp_v_time_check_state(state)

class srcFileFrame(tk.Frame):
    """Frame handling Tk objects for determing user's QCM-D device manufacturer

    Inherits from Tk.Frame
    """    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.file_src_types = ['QCM-d', 'QCM-i', 'Qsense', 'AWSensors']
        self.file_src_type = ''
        file_src_label = tk.Label(self, text="What is the source of the data file?")
        file_src_label.grid(row=0, column=0, columnspan=2, pady=(0,4), padx=6)
        self.file_src_var = tk.IntVar(value=5) # set value to one not in radios, so none selected by default
        self.opt1_radio = tk.Radiobutton(self, text="Open QCM Next", variable=self.file_src_var, value=0, command=self.handle_radios)
        self.opt1_radio.grid(row=1, column=0)
        self.opt2_radio = tk.Radiobutton(self, text="QCM-I ", variable=self.file_src_var, value=1, command=self.handle_radios)
        self.opt2_radio.grid(row=1, column=1)
        self.opt3_radio = tk.Radiobutton(self, text="QSense ", variable=self.file_src_var, value=2, command=self.handle_radios)
        self.opt3_radio.grid(row=2, column=0)
        self.opt4_radio = tk.Radiobutton(self, text="AWSensors ", variable=self.file_src_var, value=3, command=self.handle_radios)
        self.opt4_radio.grid(row=2, column=1)

        self.calibration_warning_label = tk.Label(self, text="WARNING: When using Qsense or AWSensors,\nif not calibration data entered,\nuser is limited to only basic visualizations.\n\nAdditionally 'Temperature' plotting is not currently supported.")

    def handle_radios(self):
        """handles what to do when this frame's radio buttons are clicked
        certain device options have more/less information attached with them,
        such as additional required information, warning labels, etc.
        """        
        global input
        self.file_src_type = self.file_src_types[self.file_src_var.get()]
        input.file_src_type = self.file_src_type

        
        if self.file_src_type == 'QCM-d':
            input.is_relative_time = False
            input.will_calculate_offset = True
            self.calibration_warning_label.grid_forget()
        elif self.file_src_type == 'QCM-i':
            input.is_relative_time = True
            input.will_calculate_offset = True
            self.calibration_warning_label.grid_forget()
        elif self.file_src_type == 'Qsense' or self.file_src_type == 'AWSensors':
            input.is_relative_time = True
            self.calibration_warning_label.grid(row=3, column=0, columnspan=2)
        print("***", self.file_src_type)
        self.parent.parent.temp_v_time_check_state(self.file_src_type)
        
        self.parent.blit_time_input_frame(input.is_relative_time)
        self.parent.calibration_vals_frame.handle_radios()


class calibrationValsFrame(tk.Frame):
    """frame to determine method of obtaining offset values
    not to be confused with calibrationValsWindow
    """    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        # prompt to use theoretical or calibration values for peak frequency
        self.theoretical_or_calibration_peak_freq_frame = tk.Frame(self)
        self.theoretical_or_calibration_peak_freq_frame.grid(row=7, column=0, columnspan=1, pady=(16,0))
        self.theoretical_or_calibration_peak_freq_var = tk.IntVar()
        self.theoretical_or_calibration_peak_freq_var.set(-1)
        theoretical_or_calibration_peak_freq_label = tk.Label(self.theoretical_or_calibration_peak_freq_frame,
                                                text="Use theoretical or offset\npeak frequency values for calculations")
        theoretical_or_calibration_peak_freq_label.grid(row=0, column=0, pady=(2,4), columnspan=2, padx=6)
        
        self.theoretical_peak_freq_radio = tk.Radiobutton(self.theoretical_or_calibration_peak_freq_frame, text='theoretical', variable=self.theoretical_or_calibration_peak_freq_var, value=1, command=self.handle_radios)
        self.theoretical_peak_freq_radio.grid(row=1, column=0, pady=(2,4))
        self.calibration_peak_freq_radio = tk.Radiobutton(self.theoretical_or_calibration_peak_freq_frame, text='offset', variable=self.theoretical_or_calibration_peak_freq_var, value=0, command=self.handle_radios)
        self.calibration_peak_freq_radio.grid(row=1, column=1, pady=(2,4))

        #self.filename_label = tk.Label(self.theoretical_or_calibration_peak_freq_frame, text="Calibration File")
        #self.browse_files_button = tk.Button(self.theoretical_or_calibration_peak_freq_frame, text="Select Calibration File", command=lambda: select_calibration_file(self.filename_label))
        
        self.calibration_file_label = tk.Label(self.theoretical_or_calibration_peak_freq_frame, text="Copy/paste values\ndirectly into file in \n'offset_data' folder\n\nOR")
        self.qcmi_warning_label = tk.Label(self.theoretical_or_calibration_peak_freq_frame, text="Will grab offsets automatically\nfrom baseline range for this file type")
        self.calibration_vals_window_button = tk.Button(self.theoretical_or_calibration_peak_freq_frame, text="Enter values here", command=self.open_calibration_window)

    def open_calibration_window(self):
        self.parent.parent.open_calibration_window()

    def handle_radios(self):
        """handles radio button selections for this frame
        updates labels and other options dependend on which radio selected
        """        
        global input
        set_input_altered_flag(True)
        is_qcmi = input.file_src_type == 'QCM-i'
        is_qcm_next = input.file_src_type == 'QCM-d'
        input.will_use_theoretical_vals = self.theoretical_or_calibration_peak_freq_var.get()
        if not input.will_use_theoretical_vals and (not is_qcmi and not is_qcm_next):
            self.calibration_file_label.grid(row=3, column=0, columnspan=2, pady=(2,4))
            self.calibration_vals_window_button.grid(row=4, column=0, columnspan=2, pady=(8,4))
            self.qcmi_warning_label.grid_forget()
        else:
            self.calibration_file_label.grid_forget()
            self.calibration_vals_window_button.grid_forget()

        if is_qcmi or is_qcm_next:
            self.qcmi_warning_label.grid(row=4, column=0, columnspan=2, pady=(8,4))
            

class numSensorsFrame(tk.Frame):
    """class to house frame for indicating 1 or 4 sensors"""
    def __init__(self, container):
        super().__init__(container)
        self.container = container
        self.num_sensors_label = tk.Label(self, text="Is data from 1 or 4 sensors?\n(Currently 4 sensor support only for QSense)")
        self.num_sensors_label.grid(row=0, column=0, columnspan=2)
        self.num_sensors_var = tk.IntVar()
        self.one_sensor_radio = tk.Radiobutton(self, text="1 sensor", variable=self.num_sensors_var, value=0, command=self.handle_radios)
        self.one_sensor_radio.grid(row=1, column=0)
        self.four_sensors_radio = tk.Radiobutton(self, text="4 sensors", variable=self.num_sensors_var, value=1, command=self.handle_radios)
        self.four_sensors_radio.grid(row=1, column=1)

    def handle_radios(self):
        # if not qsense selected, gray out 4 sensors, nothing changes
        # if qsense and 4 sensors, ask to plot only one sensor or all 4
            # if qsd, and plot only 1 sensor, nothing changes
            # if qsd and 4 sensors, adjust qsd formatting
            # if not qsd and 1 sensor, adjust format_QSense to have a column renaming dict read first sensors data
            # if not qsd and 4 sensors, adjust file formatting to save 4 indv files for each sensor, and adjust analyze.py to run on all 4
        # if qsense and 1 sensor, nothing changes
        
        pass

class absTimeInputFrame(tk.Frame):
    """Frame for input of absolute baseline time"""    
    def __init__(self, container):
        super().__init__(container)
        # validation cmd
        self.vcmd_int = (self.register(validate_integer), '%P')

        baseline_time_label = tk.Label(self, text="Enter absolute baseline time")
        baseline_time_label.grid(row=0, column=0, columnspan=6)
        self.hours_label_t0 = tk.Label(self, text="H0: ")
        self.hours_label_t0.grid(row=1, column=0)
        self.hours_entry_t0 = tk.Spinbox(self, width=5, from_=0, to=np.inf, increment=1, validate='focus', validatecommand=self.vcmd_int)
        self.hours_entry_t0.grid(row=1, column=1)
        self.minutes_label_t0 = tk.Label(self, text="M0: ")
        self.minutes_label_t0.grid(row=1, column=2)
        self.minutes_entry_t0 = tk.Spinbox(self, width=5, from_=0, to=np.inf, increment=5, validate='focus', validatecommand=self.vcmd_int)
        self.minutes_entry_t0.grid(row=1, column=3)
        self.seconds_label_t0 = tk.Label(self, text="S0: ")
        self.seconds_label_t0.grid(row=1, column=4)
        self.seconds_entry_t0 = tk.Spinbox(self, width=5, from_=0, to=np.inf, increment=10, validate='focus', validatecommand=self.vcmd_int)
        self.seconds_entry_t0.grid(row=1, column=5)

        self.hours_label_tf = tk.Label(self, text="Hf: ")
        self.hours_label_tf.grid(row=2, column=0)
        self.hours_entry_tf = tk.Spinbox(self, width=5, from_=0, to=np.inf, increment=1, validate='focus', validatecommand=self.vcmd_int)
        self.hours_entry_tf.grid(row=2, column=1)
        self.minutes_label_tf = tk.Label(self, text="Mf: ")
        self.minutes_label_tf.grid(row=2, column=2)
        self.minutes_entry_tf = tk.Spinbox(self, width=5, from_=0, to=np.inf, increment=5, validate='focus', validatecommand=self.vcmd_int)
        self.minutes_entry_tf.grid(row=2, column=3)
        self.seconds_label_tf = tk.Label(self, text="Sf: ")
        self.seconds_label_tf.grid(row=2, column=4)
        self.seconds_entry_tf = tk.Spinbox(self, width=5, from_=0, to=np.inf, increment=10, validate='focus', validatecommand=self.vcmd_int)
        self.seconds_entry_tf.grid(row=2, column=5)

    def get_abs_time(self):
        h0 = self.hours_entry_t0.get()
        m0 = self.minutes_entry_t0.get()
        s0 = self.seconds_entry_t0.get()
        hf = self.hours_entry_tf.get()
        mf = self.minutes_entry_tf.get()
        sf = self.seconds_entry_tf.get()

        try:
            return (time(int(h0),int(m0),int(s0)), time(int(hf),int(mf),int(sf)))
        except ValueError as exc:
            msg = f"Please enter integer values for time: {exc}"
            print(msg)
            Exceptions.error_popup(msg)

    def clear(self):
        self.hours_entry_t0.delete(0, tk.END)
        self.minutes_entry_t0.delete(0, tk.END)
        self.seconds_entry_t0.delete(0, tk.END)
        self.hours_entry_tf.delete(0, tk.END)
        self.minutes_entry_tf.delete(0, tk.END)
        self.seconds_entry_tf.delete(0, tk.END)

class relTimeInputFrame(tk.Frame):
    """frame for receiving input regarding the baseline time entered in relative time format
    """
    def __init__(self, container):
        super().__init__(container)
        baseline_time_label = tk.Label(self, text="Enter relative baseline time")
        baseline_time_label.grid(row=0, column=0, columnspan=2)

        # validation cmd
        self.vcmd_int = (self.register(validate_integer), '%P')

        self.t0_label = tk.Label(self, text="t0 (s): ")
        self.t0_label.grid(row=1, column=0)
        self.t0_entry = tk.Spinbox(self, width=5, from_=0, to=np.inf, increment=10, validate='focus', validatecommand=self.vcmd_int)
        self.t0_entry.grid(row=1, column=1)
        self.tf_label = tk.Label(self, text="tf (s): ")
        self.tf_label.grid(row=2, column=0)
        self.tf_entry = tk.Spinbox(self, width=5, from_=0, to=np.inf, increment=10, validate='focus', validatecommand=self.vcmd_int)
        self.tf_entry.grid(row=2, column=1)

    def get_rel_time(self):
        """retrieves the times from the Tk entry fields

        Returns:
            t0 (str): time=0 for baseline time entered by user
            tf (str): time=final for baseline time entered by user
        """        
        try:
            t0 = self.t0_entry.get()
            tf = self.tf_entry.get()
        except Exception as exc:
            msg = f"ERROR: please enter valid relative time input in seconds\n{exc}"
            print(msg)
            Exceptions.error_popup(msg)
        return t0, tf

    def clear(self):
        self.t0_entry.delete(0, tk.END)
        self.tf_entry.delete(0, tk.END)

class CheckBox:
    """class for making adding a plethora of checkboxes simpler
    attrs are all essential checkbox elements
    """    
    def __init__(self, intvar, checkbutton, key):
        self.intvar = intvar
        self.checkbutton = checkbutton
        self.key = key 
    
class LabelledEntry:
    """class for simplifying adding many pairs of labels/entries
    attrs are just the label and entry objects
    """    
    def __init__(self, label, entry):
        self.label = label
        self.entry = entry

class CalibrationWindow():
    """window for handling the entering of offset values
    required by devices that do not record the full values, just deltas
    """    
    def __init__(self, parent, container):
        super().__init__(container) # initialize parent class for the child
        self.parent = parent

    def open_calibration_window(self):
        calibration_window = tk.Toplevel(self)
        calibration_window.title('Input/Select Offset Data')
        calibration_window.geometry('400x650')

        self.wrapper_frame = tk.Frame(calibration_window)
        self.calibration_canv = tk.Canvas(self.wrapper_frame)

        scrollbarY = ttk.Scrollbar(self.wrapper_frame, orient='vertical', command=self.calibration_canv.yview)
        scrollbarY.pack(side='right', fill='y')
        self.calibration_canv.pack(side='left', fill='both', expand=True)

        self.calibration_canv.configure(yscrollcommand=scrollbarY.set)
        self.calibration_canv.bind("<Configure>", self.update_calibration_scrollregion)

        self.calibration_frame = tk.Frame(self.calibration_canv)
        self.calibration_canv.create_window((0,0), window=self.calibration_frame, anchor='nw')
        self.wrapper_frame.pack(fill='both', expand=True)

    def fill_calibration_window(self):
        self.calibration_label = tk.Label(self.calibration_frame, text="Offset Data", font=('TkDefaultFont', 12, 'bold'))
        self.calibration_label.grid(row=1, column=0, columnspan=2, padx=16, pady=12)
        instructions = "Input offset frequency values here\nthese values will be used for modelling purposes\n\n" +\
                        "Supports exponential format. i.e. 2.5e-6 or 1.34e7"
        self.instruction_label = tk.Label(self.calibration_frame, text=instructions)
        self.instruction_label.grid(row=2, column=0, columnspan=2, padx=16, pady=12)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)    
        # option for inputting FWHM instead of dissipation values
        self.calibration_vals_fmt_label = tk.Label(self.calibration_frame, text="Are you reporting dissipation values, or FWHM?")
        #self.calibration_vals_fmt_label.grid(row=3, column=0, columnspan=2, padx=16, pady=12)
        self.calibration_vals_fmt_var = tk.IntVar()
        self.dissipation_radio = tk.Radiobutton(self.calibration_frame, text="Dissipation", variable=self.calibration_vals_fmt_var, value=0, command=self.handle_offset_radios)
        #self.dissipation_radio.grid(row=4, column=0)
        self.FWHM_radio = tk.Radiobutton(self.calibration_frame, text="FWHM", variable=self.calibration_vals_fmt_var, value=1, command=self.handle_offset_radios)
        #self.FWHM_radio.grid(row=4, column=1)
        self.calibration_vals_fmt_var.set(0)

        self.labelled_entries = generate_labelled_entries(self.calibration_frame)
        print(self.labelled_entries)
        for i, labelled_entry in enumerate(self.labelled_entries):
            labelled_entry.label.grid(row=i+5, column=0)
            labelled_entry.entry.grid(row=i+5, column=1)

        self.clear_selections_button = tk.Button(self.calibration_frame, text="Clear all selections", padx=6, pady=4, width=20, command=self.clear_selections)
        self.clear_selections_button.grid(row=30, column=0, columnspan=2, pady=12)  
        self.confirm_selections_button = tk.Button(self.calibration_frame, text="Confirm selections", padx=6, pady=4, width=20, command=self.confirm_values)
        self.confirm_selections_button.grid(row=31, column=0, columnspan=2, pady=12)  

    def update_calibration_scrollregion(self, event):
        self.calibration_canv.configure(scrollregion=self.calibration_canv.bbox('all'))

    def handle_offset_radios(self):
        """handle radio buttons pertaining to offset
        updates labels for all labelled entries in window dependent on if user selects 'dissipation' or 'FWHM' to be entered
        """        
        label_text = 'dissipation' if self.calibration_vals_fmt_var.get() == 0 else 'FWHM'
        for i, labelled_entry in enumerate(self.labelled_entries):
            overtone = (i+1) % 2
            overtone = i+1 if overtone == 1 else i
            if overtone != i+1:
                text = ordinal(overtone) + ' ' + label_text
                labelled_entry.label.config(text=text)

    def clear_selections(self):
        for le in self.labelled_entries:
            le.entry.delete(0,tk.END)
        print("CLEARED")
        
    def confirm_values(self):
        """gets and saves all values entered by user
        also checks for if offset values file is present, if not makes new one
        """        
        calibration_vals = []
        warned_flag = False
        for le in self.labelled_entries:
            try:
                calibration_vals.append(float(le.entry.get()))
            except ValueError as ve:
                if not warned_flag:
                    msg = "WARNING: At least one entry exists with a missing or invalid input\nwill convert these entries to 0"
                    print(msg)
                    Exceptions.warning_popup(msg)
                    warned_flag = True
                calibration_vals.append(0.0)
        calibration_vals.insert(0,'index')
        print(calibration_vals)
        if self.calibration_vals_fmt_var.get() == 1: # if inputted FWHM
            calibration_vals = convert_FWHM(calibration_vals)
        print(calibration_vals)
        os.makedirs(os.path.join(os.getcwd(), 'offset_data'), exist_ok=True)
        try: # if file is removed for some reason, create a new one to fill values with
            calibration_df = pd.read_csv(resource_path("offset_data/COPY-PASTE_OFFSET_VALUES_HERE.csv"), index_col=None)
        except FileNotFoundError as fnfe:
            print("Offset values file not found, creating new one...")
            # empty first entry in headers for index column
            column_headers = " ,fundamental_freq,fundamental_dis,3rd_freq,3rd_dis,5th_freq,5th_dis,7th_freq,7th_dis,9th_freq,9th_dis,11th_freq,11th_dis,13th_freq,13th_dis\n"
            with open(os.path.join(os.getcwd(), "offset_data/COPY-PASTE_OFFSET_VALUES_HERE.csv"), 'w') as offset_file:
                offset_file.write(column_headers)
            calibration_df = pd.read_csv(os.path.join(os.getcwd(), "offset_data/COPY-PASTE_OFFSET_VALUES_HERE.csv"), index_col=None)
            print("Success")
        print(calibration_df)
        calibration_df.loc[0] = calibration_vals
        calibration_df.to_csv(os.path.join(os.getcwd(), "offset_data/COPY-PASTE_OFFSET_VALUES_HERE.csv"), index=False)
        print(f"Offset values written successfully\n: {calibration_df.head()}")


class ModelingWindow(tk.Frame):
    """class for the Tkinter window popup for user to run any of the modelling functions
    """    
    def __init__(self, parent):
        super().__init__(parent)
        self.is_visible = True  # Example flag
        self.parent = parent
        self.model_window = None

    def open_modeling_window(self):
        self.model_window = tk.Toplevel(self.parent)
        self.model_window.title('Modeling Options')
        self.models_frame = tk.Frame(self.model_window)
        self.models_frame.pack(side='left', anchor='n')
        self.fill_modeling_window()

    def fill_modeling_window(self):
        # first column contains most plot customizations
        self.customize_label = tk.Label(self.models_frame, text="Modelling Options", font=('TkDefaultFont', 12, 'bold'))
        self.customize_label.grid(row=0, column=0, columnspan=3, padx=16, pady=12)
        self.range_label = tk.Label(self.models_frame, text="NOTE: Visit this section AFTER submitting")
        self.range_label.grid(row=1, column=0, padx=10, pady=(0,8))

        # run linear regression button
        self.run_tf_liquid_analysis_button = tk.Button(self.models_frame, text="Run analysis of\nthin film in liquid", padx=6, pady=4, width=20,
                                             command=lambda: self.call_tf_liquid())
        self.run_tf_liquid_analysis_button.grid(row=10, column=0, pady=4)

        # run sauerbrey button
        self.run_sauerbrey_analysis_button = tk.Button(self.models_frame, text="Run Sauerbrey mass analysis", padx=6, pady=4, width=20,
                                             command=lambda: self.call_sauerbrey())
        self.run_sauerbrey_analysis_button.grid(row=9, column=0, pady=4)

        # avg change in freq and dis against overtone button
        self.avgs_analysis = tk.Button(self.models_frame, text="Plot average Δf and ΔD\n of overtones", padx=6, pady=4, width=20,
                                             command=lambda: self.call_averages())
        self.avgs_analysis.grid(row=8, column=0, pady=4)

        # avg change in freq against overtone button
        self.run_tf_air_analysis_button = tk.Button(self.models_frame, text="Run analysis of\nthin film in air", padx=6, pady=4, width=20,
                                             command=lambda: self.call_tf_air())
        self.run_tf_air_analysis_button.grid(row=11, column=0, pady=4)

        # Gordon-Kanazawa model
        ''' deprecated until future version
        self.run_GK_button = tk.Button(self.models_frame, text="Run Gordon-Kanazawa model", padx=6, pady=4, width=20,
                                             command=lambda: gordon_kanazawa((input.which_plot['clean'], input.will_use_theoretical_vals)))
        self.run_GK_button.grid(row=12, column=0, pady=4)
        '''
        # Quartz crystal thickness model
        self.run_crystal_thickness_button = tk.Button(self.models_frame, text="Run crystal thickness", padx=6, pady=4, width=20,
                                             command=lambda: self.call_crystal_thickness())
        self.run_crystal_thickness_button.grid(row=13, column=0, pady=4)

    def test_modelling_window(self):
        self.model_window.deiconify()

    def show_path_box(self, analysis_type_str):
        window = tk.Toplevel(self)
        window.title("Folder link")
        window.geometry("400x200")

        plot_dir = Path(os.path.join(os.getcwd(), 'qcmd-plots/modeling/'))
        
        link_label = tk.Label(window, text=f"{analysis_type_str} plot(s) Generated!\nPress the button to view them.", font=('TkDefaultFont', 10, 'bold'))
        link_label.pack(pady=20)

        open_folder_btn = tk.Button(window, text="Open plots folder", command=lambda: open_folder(plot_dir))
        open_folder_btn.pack(pady=20)

    def call_sauerbrey(self):
        try:
            sauerbrey(input.will_use_theoretical_vals)
            self.show_path_box("Sauerbrey")
        except Exception as exc:
            Exceptions.error_popup("Unknown error ocurred\n\n")
            print(exc)
    def call_averages(self):
        try:
            avgs_analysis()
            self.show_path_box("Averages")
        except Exception as exc:
            Exceptions.error_popup("Unknown error ocurred\n\n")
            print(exc)
    def call_tf_liquid(self):
        try:
            thin_film_liquid_analysis(input.which_plot['clean'], input.will_use_theoretical_vals, input.latex_installed)
            self.show_path_box("Thin film in liquid")
        except Exception as exc:
            Exceptions.error_popup("Unknown error ocurred\n\n")
            print(exc)
    def call_tf_air(self):
        try:
            thin_film_air_analysis(input.which_plot['clean'], input.will_use_theoretical_vals, input.latex_installed)
            self.show_path_box("Thin film in air")
        except Exception as exc:
            Exceptions.error_popup("Unknown error ocurred\n\n")
            print(exc)
    def call_crystal_thickness(self):
        try:
            crystal_thickness(input.which_plot['raw'], input.will_use_theoretical_vals)
            self.show_path_box("Crystal thickness")
        except Exception as exc:
            Exceptions.error_popup("Unknown error ocurred\n\n")
            print(exc)
class PlotOptsWindow():
    """window for handling all of the plot customization options
    """    
    def __init__(self, parent, container):
        super().__init__(container) # initialize parent class for the child
        self.parent = parent
        self.container = container

    def open_opts_window(self):
        self.opts_window = tk.Toplevel(self)
        self.opts_window.title('Customize Plots')
        self.init_width, self.init_height = 700, 800
        self.opts_window.geometry(f'{self.init_width}x{self.init_height}')

        self.wrapper_frame = tk.Frame(self.opts_window)        
        self.opts_canv = tk.Canvas(self.wrapper_frame)

        scrollbarY = ttk.Scrollbar(self.wrapper_frame, orient='vertical', command=self.opts_canv.yview)
        scrollbarY.pack(side='right', fill='y')
        self.opts_canv.pack(side='left', fill='both', expand=True)

        self.opts_canv.configure(yscrollcommand=scrollbarY.set)
        self.opts_canv.bind('<Configure>', self.update_opts_scrollregion)

        self.opts_frame = tk.Frame(self.opts_canv)
        self.opts_canv.create_window((0,0), window=self.opts_frame, anchor='nw')
        self.wrapper_frame.pack(fill='both', expand=True)
        
        self.vcmd_int = (self.register(validate_integer), '%P')

    def fill_opts_window(self):
        self.widgets = {}
        print(self.prev_opts)

        # first column contains most plot customizations
        self.customize_label = tk.Label(self.opts_frame, text="Plot Customization Options", font=('TkDefaultFont', 12, 'bold'))
        self.customize_label.grid(row=1, column=0, columnspan=6, padx=16, pady=12)

        self.font_choice_label = tk.Label(self.opts_frame, text="Enter font selection:")
        self.font_choice_label.grid(row=3, column=0, columnspan=3, pady=(20,4))
        self.font_choice_entry = tk.Entry(self.opts_frame, width=10)
        self.font_choice_entry.grid(row=3, column=3, columnspan=3, pady=(20,4))
        self.widgets['font'] = self.font_choice_entry

        self.label_text_size_label = tk.Label(self.opts_frame, text="Enter label font size:")
        self.label_text_size_label.grid(row=4, column=0, columnspan=3, pady=(16,0))
        self.label_text_size_entry = tk.Spinbox(self.opts_frame, width=10, from_=0, to=32, increment=2, validate='focus', validatecommand=self.vcmd_int)
        self.label_text_size_entry.grid(row=4, column=3, columnspan=3, pady=(16,0))
        self.widgets['label_text_size'] = self.label_text_size_entry

        self.title_text_size_label = tk.Label(self.opts_frame, text="Enter title font size:")
        self.title_text_size_label.grid(row=5, column=0, columnspan=3, pady=(16,0))
        self.title_text_size_entry = tk.Spinbox(self.opts_frame, width=10, from_=0, to=64, increment=2, validate='focus', validatecommand=self.vcmd_int)
        self.title_text_size_entry.grid(row=5, column=3, columnspan=3, pady=(16,0))
        self.widgets['title_text_size'] = self.title_text_size_entry

        self.value_text_size_label = tk.Label(self.opts_frame, text="Enter value font size:")
        self.value_text_size_label.grid(row=6, column=0, columnspan=3, pady=(16,0))
        self.value_text_size_entry = tk.Spinbox(self.opts_frame, width=10, from_=0, to=32, increment=2, validate='focus', validatecommand=self.vcmd_int)
        self.value_text_size_entry.grid(row=6, column=3, columnspan=3, pady=(16,0))
        self.widgets['value_text_size'] = self.value_text_size_entry

        self.legend_text_size_label = tk.Label(self.opts_frame, text="Enter legend font size:")
        self.legend_text_size_label.grid(row=7, column=0, columnspan=3, pady=(16,0))
        self.legend_text_size_entry = tk.Spinbox(self.opts_frame, width=10, from_=0, to=32, increment=2, validate='focus', validatecommand=self.vcmd_int)
        self.legend_text_size_entry.grid(row=7, column=3, columnspan=3, pady=(16,0))
        self.widgets['legend_text_size'] = self.legend_text_size_entry

        self.tick_direction_label = tk.Label(self.opts_frame, text="Choose tick direction:")
        self.tick_direction_label.grid(row=9, column=0, columnspan=6, pady=0)
        self.tick_direction_var = tk.IntVar()
        self.tick_direction_var.set(-1)
        self.tick_direction_in_radio = tk.Radiobutton(self.opts_frame, text="in", variable=self.tick_direction_var, value=0)
        self.tick_direction_in_radio.grid(row=10, column=0, columnspan=2)
        self.tick_direction_out_radio = tk.Radiobutton(self.opts_frame, text="out", variable=self.tick_direction_var, value=1)
        self.tick_direction_out_radio.grid(row=10, column=2, columnspan=2)
        self.tick_direction_inout_radio = tk.Radiobutton(self.opts_frame, text="both", variable=self.tick_direction_var, value=2)
        self.tick_direction_inout_radio.grid(row=10, column=4, columnspan=2)
        self.widgets['tick_dir'] = self.tick_direction_var

        # Options for changing the scale of x axis time
        self.scale_time_var = tk.IntVar()
        self.which_range_var = tk.IntVar()
        self.scale_time_check = tk.Checkbutton(self.opts_frame, text="Change scale of time? (default (s))", variable=self.scale_time_var, onvalue=1, offvalue=0, command=self.receive_scale_radios)
        self.scale_time_check.grid(row=12, column=0, columnspan=6, pady=(32,0))
        
        # default to seconds
        self.time_scale_frame = tk.Frame(self.opts_frame)
        self.which_time_scale_var = tk.IntVar()
        self.seconds_scale_check = tk.Radiobutton(self.time_scale_frame, text="Seconds", variable=self.which_time_scale_var, value=1, command=self.receive_scale_radios)
        self.seconds_scale_check.grid(row=0, column=0, columnspan=2)
        self.minutes_scale_check = tk.Radiobutton(self.time_scale_frame, text="Minutes", variable=self.which_time_scale_var, value=2, command=self.receive_scale_radios)
        self.minutes_scale_check.grid(row=0, column=2, columnspan=2)
        self.hours_scale_check = tk.Radiobutton(self.time_scale_frame, text="Hours", variable=self.which_time_scale_var, value=3, command=self.receive_scale_radios)
        self.hours_scale_check.grid(row=0, column=4, columnspan=2)
        self.widgets['time_scale'] = self.which_time_scale_var

        # Options for changing file format of saved scatter plot figures
        self.change_fig_format_var = tk.IntVar()
        self.change_fig_format_check = tk.Checkbutton(self.opts_frame, text="Change figure file format? (default .png)", variable=self.change_fig_format_var, onvalue=1, offvalue=0, command=self.receive_file_format_radios)
        self.change_fig_format_check.grid(row=16, column=0, columnspan=6, pady=(8,0))
        # default png
        self.file_format_frame = tk.Frame(self.opts_frame)
        self.which_file_format_var = tk.IntVar()
        self.png_check = tk.Radiobutton(self.file_format_frame, text=".png", variable=self.which_file_format_var, value=1, command=self.receive_file_format_radios)
        self.png_check.grid(row=0, column=0, columnspan=2)
        self.tiff_check = tk.Radiobutton(self.file_format_frame, text=".tiff", variable=self.which_file_format_var, value=2, command=self.receive_file_format_radios)
        self.tiff_check.grid(row=0, column=2, columnspan=2)
        self.pdf_check = tk.Radiobutton(self.file_format_frame, text=".pdf", variable=self.which_file_format_var, value=3, command=self.receive_file_format_radios)
        self.pdf_check.grid(row=0, column=4, columnspan=2)
        self.widgets['fig_format'] = self.which_file_format_var

        # option to change DPI (quality) of saved figures
        self.fig_dpi_label = tk.Label(self.opts_frame, text="Figure DPI (quality)")
        self.fig_dpi_label.grid(row=19, column=0, columnspan=3, pady=8)
        self.fig_dpi_entry = tk.Spinbox(self.opts_frame, width=10, from_=0, to=1000, increment=20, validate='focus', validatecommand=self.vcmd_int)
        self.fig_dpi_entry.grid(row=19, column=3, columnspan=3, pady=8)
        self.widgets['fig_dpi'] = self.fig_dpi_entry

        # option to index how many points user would like to plot (i.e. every 5th point)
        self.points_plotted_index_label = tk.Label(self.opts_frame, text="Points to plot index:\ni.e. plot every 5th point")
        self.points_plotted_index_label.grid(row=20, column=0, columnspan=3, pady=8)
        self.points_plotted_index_entry = tk.Entry(self.opts_frame, width=10)
        self.points_plotted_index_entry.grid(row=20, column=3, columnspan=3, pady=8)
        self.widgets['points_plotted_index'] = self.points_plotted_index_entry

        # option to set bounds of time, frequency, and dissipation
        self.bounds_frame = tk.Frame(self.opts_frame)
        bounds_label_text = "Enter bounds for data to be plotted\nenter 'auto' to use the default for that bound\n\n" \
        + "Note: units of time rely on units specified above,\n" \
        + "frequency bounds are in terms of Δf (Hz), not f,\n" \
        + "and dissipation bounds are in terms of (your number) E-6"
        self.bounds_label = tk.Label(self.bounds_frame, text=bounds_label_text)
        self.bounds_label.grid(row=0, column=0, columnspan=4, pady=8)
        self.time_lower_bound_label = tk.Label(self.bounds_frame, text="Time Lower: ")
        self.time_lower_bound_label.grid(row=1, column=0, padx=4, pady=4)
        self.time_lower_bound_entry = tk.Entry(self.bounds_frame, width=10)
        self.time_lower_bound_entry.grid(row=1, column=1, padx=4, pady=4)
        self.time_upper_bound_label = tk.Label(self.bounds_frame, text="Time Upper: ")
        self.time_upper_bound_label.grid(row=1, column=2, padx=4, pady=4)
        self.time_upper_bound_entry = tk.Entry(self.bounds_frame, width=10)
        self.time_upper_bound_entry.grid(row=1, column=3, padx=4, pady=4)
        self.widgets['time_lower_bound'] = self.time_lower_bound_entry
        self.widgets['time_upper_bound'] = self.time_upper_bound_entry

        self.frequency_lower_bound_label = tk.Label(self.bounds_frame, text="Frequency lower: ")
        self.frequency_lower_bound_label.grid(row=2, column=0, padx=4, pady=4)
        self.frequency_lower_bound_entry = tk.Entry(self.bounds_frame, width=10)
        self.frequency_lower_bound_entry.grid(row=2, column=1, padx=4, pady=4)
        self.frequency_upper_bound_label = tk.Label(self.bounds_frame, text="Frequency upper: ")
        self.frequency_upper_bound_label.grid(row=2, column=2, padx=4, pady=4)
        self.frequency_upper_bound_entry = tk.Entry(self.bounds_frame, width=10)
        self.frequency_upper_bound_entry.grid(row=2, column=3, padx=4, pady=4)
        self.widgets['frequency_lower_bound'] = self.frequency_lower_bound_entry
        self.widgets['frequency_upper_bound'] = self.frequency_upper_bound_entry

        self.dissipation_lower_bound_label = tk.Label(self.bounds_frame, text="Dissipation lower: ")
        self.dissipation_lower_bound_label.grid(row=3, column=0, padx=4, pady=4)
        self.dissipation_lower_bound_entry = tk.Entry(self.bounds_frame, width=10)
        self.dissipation_lower_bound_entry.grid(row=3, column=1, padx=4, pady=4)
        self.dissipation_upper_bound_label = tk.Label(self.bounds_frame, text="Dissipation upper: ")
        self.dissipation_upper_bound_label.grid(row=3, column=2, padx=4, pady=4)
        self.dissipation_upper_bound_entry = tk.Entry(self.bounds_frame, width=10)
        self.dissipation_upper_bound_entry.grid(row=3, column=3, padx=4, pady=4)
        self.widgets['dissipation_lower_bound'] = self.dissipation_lower_bound_entry
        self.widgets['dissipation_upper_bound'] = self.dissipation_upper_bound_entry
        
        self.bounds_frame.grid(row=21, column=0, columnspan=6, pady=(12,0))

        # second column color customizer
        self.ov_color_label = tk.Label(self.opts_frame, text="Customize Overtone Plot Colors", font=('TkDefaultFont', 12, 'bold'))
        self.ov_color_label.grid(row=1, column=6, padx=16, pady=12)
        
        self.ov1_color_button = tk.Button(self.opts_frame, text="1st overtone", width=10, command=lambda: self.choose_color(1))
        self.ov1_color_button.grid(row=3, column=6, pady=(16,4))
        self.ov3_color_button = tk.Button(self.opts_frame, text="3rd overtone", width=10, command=lambda: self.choose_color(3))
        self.ov3_color_button.grid(row=4, column=6, pady=4)
        self.ov5_color_button = tk.Button(self.opts_frame, text="5th overtone", width=10, command=lambda: self.choose_color(5))
        self.ov5_color_button.grid(row=5, column=6, pady=4)
        self.ov7_color_button = tk.Button(self.opts_frame, text="7th overtone", width=10, command=lambda: self.choose_color(7))
        self.ov7_color_button.grid(row=6, column=6, pady=4)
        self.ov9_color_button = tk.Button(self.opts_frame, text="9th overtone", width=10, command=lambda: self.choose_color(9))
        self.ov9_color_button.grid(row=7, column=6, pady=4)
        self.ov11_color_button = tk.Button(self.opts_frame, text="11th overtone", width=10, command=lambda: self.choose_color(11))
        self.ov11_color_button.grid(row=8, column=6, pady=4)
        self.ov13_color_button = tk.Button(self.opts_frame, text="13th overtone", width=10, command=lambda: self.choose_color(13))
        self.ov13_color_button.grid(row=9, column=6, pady=4)

        self.empty_entries_notif_label = tk.Label(self.opts_frame, text="WARNING: Empty entries to default to\npreviously entered options", font=('TkDefaultFont', 10, 'bold'))
        self.options_saved_label = tk.Label(self.opts_frame, text="Confirming selections\nsaves preferences\neven when software\nis closed")
        self.options_saved_label.grid(row=28, column=6, pady=(24,4))
        self.default_button = tk.Button(self.opts_frame, text="Default values", width=14, command=self.set_default_values)
        self.default_button.grid(row=29, column=6, pady=4)
        self.confirm_button = tk.Button(self.opts_frame, text="Confirm selections", width=14, command=self.confirm_opts)
        self.confirm_button.grid(row=30, column=6, pady=(4,16))

    def force_resize(self):
        """force a 1 pixel resize of the window
        called when anything in window is blitted
        this was the only way to get the scrollbar to work properly tkinter kinda dumb sometimes
        """        
        cur_width, cur_height = self.opts_window.winfo_width(), self.opts_window.winfo_height()
        print(self.opts_window.winfo_height())
        print(self.init_height)

        if cur_height == self.init_height:
            self.opts_window.geometry(f'{cur_width}x{cur_height+1}')
        else:
            self.opts_window.geometry(f'{self.init_width}x{self.init_height}')
        print(self.opts_window.winfo_width(), self.opts_window.winfo_height())
        print(self.init_height)


    def update_opts_scrollregion(self, event):
        self.opts_canv.update_idletasks()
        self.opts_canv.configure(scrollregion=self.opts_canv.bbox('all'))

    def choose_color(self, ov_num):
        self.color_code = colorchooser.askcolor(title="Choose color for overtone", parent=self)
        self.options['colors'][f'ov{ov_num}'] = self.color_code[1]

    def set_text(self, entry, text):
        entry.delete(0, tk.END)
        entry.insert(0, text)
        
    def receive_scale_radios(self):
        global input
        set_input_altered_flag(True)
        if self.scale_time_var.get() == 1:
            self.time_scale_frame.grid(row=13, column=0, columnspan=6)
            if self.which_time_scale_var.get() == 1:
                input.x_timescale = 's'
            elif self.which_time_scale_var.get() == 2:
                input.x_timescale = 'min'
            elif self.which_time_scale_var.get() == 3:
                input.x_timescale = 'hr'
            else:
                input.x_timescale= 'u'
        else:
            self.time_scale_frame.grid_forget()
            input.x_timescale = 's'
        self.force_resize()
        self.opts_canv.update_idletasks()

    def receive_file_format_radios(self):
        global input
        set_input_altered_flag(True)
        if self.change_fig_format_var.get() == 1:
            self.file_format_frame.grid(row=17, column=0, columnspan=6)
            if self.which_file_format_var.get() == 1:
                input.fig_format = 'png'
            elif self.which_file_format_var.get() == 2:
                input.fig_format = 'tiff'
            elif self.which_file_format_var.get() == 3:
                input.fig_format = 'pdf'
            else:
                input.fig_format = 'u'
        else:
            self.file_format_frame.grid_forget()
            input.fig_format = 'png'
        self.force_resize()
        self.opts_canv.update_idletasks()
    
    def set_default_values(self):
        with open(resource_path('plot_opts/default_opts.json'), 'r') as fp:
            default_opts = json.load(fp)

        for key in list(default_opts.keys())[1:]:
            if isinstance(self.widgets[key], tk.Entry):
                self.set_text(self.widgets[key], default_opts[key])

        self.tick_direction_var.set(1)
        self.time_scale_frame.grid(row=13, column=0, columnspan=6)
        if self.change_fig_format_var.get() == 0:
            self.change_fig_format_var.set(1)
        self.which_file_format_var.set(1)
        self.file_format_frame.grid(row=17, column=0, columnspan=6)
        if self.scale_time_var.get() == 0:
            self.scale_time_var.set(1)
        self.which_time_scale_var.set(1)
        
        self.options = default_opts
        self.wrapper_frame.update_idletasks()
        self.force_resize()

    def confirm_opts(self):
        '''confirm the options entered by user
        any values left blank are set to default values and user is warned
        '''
        set_input_altered_flag(True)
        print(self.prev_opts)
        
        # put widget values into dict
        warned_flag = False
        for key in list(self.options.keys())[1:]:
            if isinstance(self.widgets[key], tk.Entry):
                entry = self.widgets[key].get()
                if entry == '':
                    if not warned_flag:
                        self.empty_entries_notif_label.grid(row=31, column=6, pady=6)
                        warned_flag = True
                    self.options[key] = self.prev_opts[key]
                else:
                    try:
                        entry = int(entry)
                        self.options[key] = entry
                    except ValueError:
                        self.options[key] = entry

            elif isinstance(self.widgets[key], tk.IntVar):
                if key == 'time_scale':
                    if self.widgets[key].get() == 1:
                        self.options['time_scale'] = 's'
                    if self.widgets[key].get() == 2:
                        self.options['time_scale'] = 'min'
                    if self.widgets[key].get() == 3:
                        self.options['time_scale'] = 'hr'
                
                elif key == 'fig_format':
                    if self.widgets[key].get() == 1:
                        self.options['fig_format'] = 'png'
                    if self.widgets[key].get() == 2:
                        self.options['fig_format'] = 'tiff'
                    if self.widgets[key].get() == 3:
                        self.options['fig_format'] = 'pdf'

                elif key == 'tick_dir':
                    if self.widgets[key].get() == 0:
                        self.options['tick_dir'] = 'in'
                    if self.widgets[key].get() == 1:
                        self.options['tick_dir'] = 'out'
                    if self.widgets[key].get() == 2:
                        self.options['tick_dir'] = 'inout'

        if warned_flag:
            self.empty_entries_notif_label.after(5000, lambda: self.empty_entries_notif_label.grid_forget())
            warned_flag = False

        os.makedirs(os.path.join(os.getcwd(), 'plot_opts'), exist_ok=True)
        with open(os.path.join(os.getcwd(), 'plot_opts/plot_customizations.json'), 'w') as fp:
            json.dump(self.options, fp, indent=4)


class Col1(tk.Frame):
    '''parent column for all data file related UI entries'''
    def __init__(self, parent, container):
        super().__init__(container)
        self.container = container
        self.col_position = 0
        self.is_visible = True
        self.parent = parent
        file_name_label = tk.Label(self, text="Enter Data File Information", font=('TkDefaultFont', 12, 'bold'))
        file_name_label.grid(row=0, column=0, pady=(14,16), padx=(6,0))
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)          
        self.filename_label = tk.Label(self, text="Data file")
        self.filename_label.grid(row=2, column=0, pady=(8,4))
        self.browse_files_button = tk.Button(self, text="Select data file", command=lambda: select_data_file(self.filename_label))
        self.browse_files_button.grid(row=1, column=0)

        self.file_src_frame = srcFileFrame(self)
        self.file_src_frame.grid(row=4, column=0, pady=(16,8))

        #self.num_sensors_frame = numSensorsFrame(self)
        #self.num_sensors_frame.grid(row=5, column=0, pady=8)

        self.rel_time_input = relTimeInputFrame(self)
        self.abs_time_input = absTimeInputFrame(self)
        self.abs_time_input.grid(row=6, column=0)

        self.calibration_vals_frame = calibrationValsFrame(self)
        self.calibration_vals_frame.grid(row=7, column=0)

        self.cleared_label = tk.Label(self, text="Cleared!")
        self.submitted_label = tk.Label(self, text="Submitted!")
        self.err_label = tk.Label(self, text="Error occured,\nplease see terminal for details", font=("Arial",14))

        self.file_data_submit_button = tk.Button(self, text="Submit file information", padx=8, pady=6, width=20, command=self.col_names_submit)
        self.file_data_submit_button.grid(row=10, column=0, pady=(16,4))
        self.file_data_clear_button = tk.Button(self, text="Clear entries", padx=8, pady=6, width=20, command=self.clear_file_data)
        self.file_data_clear_button.grid(row=11, column=0, pady=4)

        self.open_plot_opts_button = tk.Button(self, text="Customize plot options", width=20, command=self.open_plot_opts)
        self.open_plot_opts_button.grid(row=14, pady=(16, 4)) 

    '''def temp_v_time_check_state(self):
        self.parent.parent.temp_v_time_check_state()'''  # Call the function from App

    def open_plot_opts(self):
        self.parent.open_plot_opts_window()

    def blit_time_input_frame(self, is_relative_time):
        if is_relative_time:
            self.abs_time_input.grid_forget()
            self.rel_time_input.grid(row=6, column=0)
        else:
            self.rel_time_input.grid_forget()
            self.abs_time_input.grid(row=6, column=0)

    def col_names_submit(self):
        global input
        input.first_run = True

        set_input_altered_flag(True)
        input.file_src_type = self.file_src_frame.file_src_type
        if input.is_relative_time:
            input.rel_t0, input.rel_tf = self.rel_time_input.get_rel_time()
        else:
            input.abs_base_t0, input.abs_base_tf = self.abs_time_input.get_abs_time()

        if input.first_run:
            print(f"formatting {input.file} to BraTaDio convention...")
            if input.file == '':
                Exceptions.error_popup("Please select a valid file.")
            if input.file_src_type == '':
                Exceptions.error_popup("Please select a file source type.")

            format_raw_data(input.file_src_type, input.file, input.will_use_theoretical_vals)
            print("Format completed")
        
        self.submitted_label.grid(row=13, column=0)
        self.submitted_label.after(5000, lambda: self.submitted_label.grid_forget())

    def clear_file_data(self):
        global input
        input.abs_base_t0 = time(0, 0, 0)
        input.abs_base_tf = time(0, 0, 0)
        self.cleared_label.grid(row=12, column=0)
        self.filename_label.configure(text="Data file")
        self.abs_time_input.clear()
        self.rel_time_input.clear()
        self.submitted_label.grid_forget()

class Col2(tk.Frame):
    '''parent column for any raw overtone selections'''
    def __init__(self, parent, container):
        super().__init__(container)
        self.parent = parent
        self.col_position = 1
        self.is_visible = True
        self.plot_raw_data_var = tk.IntVar()
        self.plot_raw_data_check = tk.Checkbutton(self, text="Raw Data Overtone Selection\n(f and D)", font=('TkDefaultFont', 12, 'bold'), variable=self.plot_raw_data_var, onvalue=1, offvalue=2, command=self.receive_raw_checkboxes)
        self.plot_raw_data_check.grid(row=0, column=0, pady=(12,8), padx=(16,32))
        self.which_raw_channels_label = tk.Label(self, text="Select overtones for full data")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)    
        # checkboxes for selecting which channels to plot for raw data
        self.raw_checks = create_checkboxes(self, 'raw')

        self.clear_raw_checks_button = tk.Button(self, text='Clear all', width=8, command=self.clear_raw_checks)
        self.select_all_raw_checks_button = tk.Button(self, text='Select all', width=8, command=self.select_all_raw_checks)

    def receive_raw_checkboxes(self):
        global input
        set_input_altered_flag(True)
        if self.plot_raw_data_var.get() == 1:
            input.will_plot_raw_data = True
            self.which_raw_channels_label.grid(row=1, column=0, pady=(0,26))
            self.select_all_raw_checks_button.grid(row=30, column=0, padx=(0,0), pady=(12,4))
            self.clear_raw_checks_button.grid(row=31, column=0, padx=(0,0), pady=(4,4))
            #self.calibration_data_button.grid(row=21, column=0, padx=(0,0), pady=(4,4))
            
            for i, cb in enumerate(self.raw_checks):
                cb.checkbutton.grid(row=i+2, column=0)

                if cb.intvar.get() == 1:
                    input.which_plot[cb.key[0]][cb.key[1]] = True
                else:
                    input.which_plot[cb.key[0]][cb.key[1]] = False

        else:
            input.will_plot_raw_data = False
            self.which_raw_channels_label.grid_forget()

            for cb in self.raw_checks:
                cb.checkbutton.grid_forget()

            self.select_all_raw_checks_button.grid_forget()
            self.clear_raw_checks_button.grid_forget()

        
    def clear_raw_checks(self):
        global input
        for cb in self.raw_checks:
            cb.intvar.set(0)

        for channel in input.which_plot['raw']:
            input.which_plot['raw'][channel] = False
                    
    def select_all_raw_checks(self):
        global input
        for cb in self.raw_checks:
            cb.intvar.set(1)

        for channel in input.which_plot['raw']:
            input.which_plot['raw'][channel] = True   
        print(input.which_plot)
        

class Col3(tk.Frame):
    '''parent column for any clean overtone selections'''
    def __init__(self, parent, container):
        super().__init__(container)
        self.parent = parent
        self.col_position = 2
        self.is_visible = True
        self.container = container
        self.plot_clean_data_var = tk.IntVar()
        self.plot_clean_data_check = tk.Checkbutton(self, text="Shifted Data Overtone Selection\n(Δf and ΔD)", font=('TkDefaultFont', 12, 'bold'), variable=self.plot_clean_data_var, onvalue=1, offvalue=0, command=self.receive_clean_checkboxes)
        self.plot_clean_data_check.grid(row=0, column=0, pady=(12,8), padx=(32,16))
        self.which_clean_channels_label = tk.Label(self, text="Select overtones for\nbaseline corrected data")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)    
        # checkboxes for selecting which channels to plot for clean data
        self.clean_checks = create_checkboxes(self, 'clean')

        self.clear_clean_checks_button = tk.Button(self, text='Clear all', width=8, command=self.clear_clean_checks)
        self.select_all_clean_checks_button = tk.Button(self, text='Select all', width=8, command=self.select_all_clean_checks)


    def receive_clean_checkboxes(self):
        global input
        set_input_altered_flag(True)
        if self.plot_clean_data_var.get() == 1:
            input.will_plot_clean_data = True
            self.which_clean_channels_label.grid(row=1, column=0, pady=(0,12))
            self.select_all_clean_checks_button.grid(row=30, column=0, padx=(0,0), pady=(12,4))
            self.clear_clean_checks_button.grid(row=31, column=0, padx=(0,0), pady=(4,4))
            
            for i, cb in enumerate(self.clean_checks):
                cb.checkbutton.grid(row=i+2, column=0)

                if cb.intvar.get() == 1:
                    input.which_plot[cb.key[0]][cb.key[1]] = True
                else:
                    input.which_plot[cb.key[0]][cb.key[1]] = False        

        else:
            input.will_plot_clean_data = False
            self.which_clean_channels_label.grid_forget()
            
            for cb in self.clean_checks:
                cb.checkbutton.grid_forget()

            self.select_all_clean_checks_button.grid_forget()
            self.clear_clean_checks_button.grid_forget()

    def clear_clean_checks(self):
        global input
        for cb in self.clean_checks:
            cb.intvar.set(0)

        for channel in input.which_plot['clean']:
            input.which_plot['clean'][channel] = False
        
    def select_all_clean_checks(self):
        global input

        for cb in self.clean_checks:
            cb.intvar.set(1)

        for channel in input.which_plot['clean']:
            input.which_plot['clean'][channel] = True
        print(input.which_plot)
        


class Col4(tk.Frame):
    '''parent column for any alternate plot options and submissions'''
    def __init__(self, parent, container):
        super().__init__(container)

        self.finished_window = None
        self.col_position = 3
        self.model_window_open_flag = False
        self.is_visible = True
        self.parent = parent
        self.container = container
        self.first_run = True
        self.plot_options_label = tk.Label(self, text="Options For Plots", font=('TkDefaultFont', 12, 'bold'))
        self.plot_options_label.grid(row=0, column=4, pady=(14,16), padx=(0,6))
        self.grid_rowconfigure(0, weight=0)
        self.grid_columnconfigure(0, weight=1)  

        # interactive plot opts frame
        self.int_plot_frame = tk.Frame(self)
        self.int_plot_dfmt_var = tk.IntVar()
        self.raw_int_plot_check = tk.Radiobutton(self.int_plot_frame, text="Raw data", variable=self.int_plot_dfmt_var, value=1,
                                                 command=lambda: receive_int_plot_input(self.int_plot_dfmt_var))
        self.raw_int_plot_check.grid(row=0, column=0)
        self.clean_int_plot_check = tk.Radiobutton(self.int_plot_frame, text="Shifted data", variable=self.int_plot_dfmt_var, value=2,
                                                 command=lambda: receive_int_plot_input(self.int_plot_dfmt_var))
        self.clean_int_plot_check.grid(row=0, column=1)
        
        # options for the int plot
        self.vcmd_overtone_num = (self.register(validate_overtone_num), '%P')

        self.interactive_plot_overtone_label = tk.Label(self.int_plot_frame, text="Select overtone to visualize:")
        self.interactive_plot_overtone_label.grid(row=1, column=0, columnspan=2, pady=12)
        self.interactive_plot_overtone_select = tk.Spinbox(self.int_plot_frame, width=10, from_=1, to=13, increment=2, validate='focus', validatecommand=self.vcmd_overtone_num)
        self.interactive_plot_overtone_select.grid(row=2, column=0, columnspan=2)

        # define and place entry for range options
        self.which_range_label = tk.Label(self.int_plot_frame, text="Enter which range being selected\n(use identifier of your choosing\ni.e. numbers or choice of label)" )
        self.which_range_label.grid(row=3, column=0, columnspan=2, pady=(2,4), padx=4)
        self.which_range_entry = tk.Entry(self.int_plot_frame, width=10)
        self.which_range_entry.grid(row=4, column=0, columnspan=2, pady=(2,4))

        # button to submit range selected
        self.which_range_submit = tk.Button(self.int_plot_frame, text='Confirm range', padx=10, pady=4, width=20, height=1, command=self.confirm_range)
        self.which_range_submit.grid(row=5, column=0, columnspan=2, pady=(4,12))
        input.range_frame_flag = True

        # miscellaneous plot options
        self.plot_dF_dD_together_var = tk.IntVar()
        self.plot_dF_dD_together_check = tk.Checkbutton(self, text="Plot Δf and ΔD together", variable=self.plot_dF_dD_together_var, onvalue=1, offvalue=0, command=self.receive_optional_checkboxes)
        self.plot_dF_dD_together_check.grid(row=2, column=4)
        self.normalize_F_var = tk.IntVar()
        self.normalize_F_check = tk.Checkbutton(self, text="Normalize Δf with its\nrespective overtone", variable=self.normalize_F_var, onvalue=1, offvalue=0, command=self.receive_optional_checkboxes)
        self.normalize_F_check.grid(row=3, column=4)
        self.plot_dD_v_dF_var = tk.IntVar()
        self.plot_dD_v_dF_check = tk.Checkbutton(self, text="Plot ΔD vs Δf", variable=self.plot_dD_v_dF_var, onvalue=1, offvalue=0, command=self.receive_optional_checkboxes)
        self.plot_dD_v_dF_check.grid(row=4, column=4)
        self.plot_temp_v_time_var = tk.IntVar()
        self.plot_temp_v_time_check = tk.Checkbutton(self, text="Plot temperature vs time", variable=self.plot_temp_v_time_var, onvalue=1, offvalue=0, command=self.receive_optional_checkboxes)
        self.plot_temp_v_time_check.grid(row=5, column=4)
        self.correct_slope_var = tk.IntVar()
        self.correct_slope_check = tk.Checkbutton(self, text="Drift correction", variable=self.correct_slope_var, onvalue=1, offvalue=0, command=self.receive_optional_checkboxes)
        #self.correct_slope_check.grid(row=6, column=4)
        self.enable_interactive_plot_var = tk.IntVar()
        self.enable_interactive_plot_check = tk.Checkbutton(self, text="Enable interactive plot", variable=self.enable_interactive_plot_var, onvalue=1, offvalue=0, command=self.receive_optional_checkboxes)
        self.enable_interactive_plot_check.grid(row=7, column=4, pady=(6,0))

        self.open_model_window_button = tk.Button(self, text="Modelling", padx=8, pady=6, width=20, command=self.model_window_button)
        self.open_model_window_button.grid(row=22, column=4, pady=4)

        self.submit_button = tk.Button(self, text="Generate plots", padx=8, pady=6, width=20, command=self.submit)
        self.submit_button.grid(row=20, column=4, pady=(16,4), padx=20)

        self.clear_range_data_button = tk.Button(self, text="Clear saved range data", padx=8, pady=6, width=20, command=self.clear_range_data)
        self.clear_range_data_button.grid(row=21, column=4, pady=4)

        self.exit_button = tk.Button(self, text="Exit", padx=8, pady=6, width=20, command=self.parent.on_exit)
        self.exit_button.grid(row=23, column=4, pady=4)

    def receive_optional_checkboxes(self):
        global input
        set_input_altered_flag(True)
        input.will_plot_dF_dD_together = True if self.plot_dF_dD_together_var.get() == 1 else False
        input.will_normalize_F = True if self.normalize_F_var.get() == 1 else False
        input.will_plot_dD_v_dF = True if self.plot_dD_v_dF_var.get() == 1 else False
        input.will_plot_temp_v_time = True if self.plot_temp_v_time_var.get() == 1 else False
        input.will_correct_slope = True if self.correct_slope_var.get() == 1 else False
        input.enable_interactive_plot = True if self.enable_interactive_plot_var.get() == 1 else False

        if self.enable_interactive_plot_var.get() == 1:
            self.int_plot_frame.grid(row=8, column=4)
        else:
            self.int_plot_frame.grid_forget()

    def set_plot_temp_v_time_check_state(self, state):
        if state == 'disable':
            self.plot_temp_v_time_check.config(state=tk.DISABLED)
        elif state == 'enable':
            self.plot_temp_v_time_check.config(state=tk.NORMAL)

    def confirm_range(self):
        global input
        print("ASDFASDF",int(self.int_plot_dfmt_var.get()), type(int(self.int_plot_dfmt_var.get())))
        if int(self.int_plot_dfmt_var.get()) == 1:
            input.interactive_plot_data_fmt['raw'] = True
            input.which_range_selecting['raw'] = self.which_range_entry.get()
            input.interactive_plot_data_fmt['clean'] = False
        elif int(self.int_plot_dfmt_var.get()) == 2:
            input.interactive_plot_data_fmt['raw'] = False
            input.which_range_selecting['clean'] = self.which_range_entry.get()
            input.interactive_plot_data_fmt['clean'] = True
        else:
            msg = "Error: Please select 'raw' or 'shifted' data before entering range."
            Exceptions.error_popup(msg)
        
        print(f"confirmed range: {input.which_range_selecting}")

    def model_window_button(self):
        try:
            self.modelling_window.test_modelling_window()
        except:
            self.modelling_window = ModelingWindow(self)
            self.modelling_window.open_modeling_window()

    def show_path_box(self):
        if self.finished_window and self.finished_window.winfo_exists():
            self.finished_window.lift()
        else:
            self.finished_window = tk.Toplevel(self)
            self.finished_window.title("Finished Generating Plots")
            self.finished_window.geometry("400x200")

            plot_dir = Path(os.path.join(os.getcwd(), 'qcmd-plots/'))
            
            link_label = tk.Label(self.finished_window, text="Plots Generated!\nPress the button to view them.", font=('TkDefaultFont', 10, 'bold'))
            link_label.pack(pady=20)

            open_folder_btn = tk.Button(self.finished_window, text="Open plots folder", command=lambda: open_folder(plot_dir))
            open_folder_btn.pack(pady=20)

    def submit(self):
        global input
        print("***FINAL",input.which_plot)
        # make sure modelling output folder exists
        os.makedirs(os.path.join(os.getcwd(), 'qcmd-plots', 'modeling'), exist_ok=True)
        err_check()
        try:
            input.interactive_plot_overtone['clean'] = int(self.interactive_plot_overtone_select.get())
        except:
            input.interactive_plot_overtone['clean'] = 0
        try:
            input.interactive_plot_overtone['raw'] = int(self.interactive_plot_overtone_select.get())
        except:
            input.interactive_plot_overtone['raw'] = 0

        global INPUT_ALTERED_FLAG
        analyze_data(input)

        self.show_path_box()
        
        set_input_altered_flag(False, False)
        input.first_run = False

    def clear_range_data(self):
        set_input_altered_flag(True)
        selected_ranges_dir = os.path.join(os.getcwd(), 'selected_ranges')
        os.makedirs(selected_ranges_dir, exist_ok=True)
        rf_clean_stats = open(os.path.join(selected_ranges_dir, "clean_all_stats_rf.csv"), 'w')
        dis_clean_stats = open(os.path.join(selected_ranges_dir, "clean_all_stats_dis.csv"), 'w')
        rf_raw_stats = open(os.path.join(selected_ranges_dir, "raw_all_stats_rf.csv"), 'w')
        dis_raw_stats = open(os.path.join(selected_ranges_dir, "raw_all_stats_dis.csv"), 'w')
        sauerbray_stats = open(os.path.join(selected_ranges_dir, "Sauerbrey_stats.csv"), 'w')
        sauerbrey_ranges = open(os.path.join(selected_ranges_dir, "Sauerbrey_ranges.csv"), 'w')
        tfa = open(os.path.join(selected_ranges_dir, "thin_film_air_output.csv"), 'w')
        tfl = open(os.path.join(selected_ranges_dir, "thin_film_liquid_output.csv"), 'w')
        files = [rf_clean_stats, dis_clean_stats, rf_raw_stats, dis_raw_stats, sauerbray_stats, sauerbrey_ranges, tfa, tfl]
        for file in files:
            file.write('')
            file.close()


if __name__ == '__main__':
    menu = App()
    menu.mainloop()