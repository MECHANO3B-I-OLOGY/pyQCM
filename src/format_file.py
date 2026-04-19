import pandas as pd
import numpy as np
import os
import sys
import re
from . import Exceptions

from src.format_qsd import read_qsd, extract_sensor_data

'''lists of col names for frequency and dissipation to be formatted to'''
freqs = ['fundamental_freq', '3rd_freq', '5th_freq', '7th_freq', '9th_freq', '11th_freq', '13th_freq']
disps = ['fundamental_dis', '3rd_dis', '5th_dis', '7th_dis', '9th_dis', '11th_dis', '13th_dis']
    

# using the user defn file name and path (if provided) open file as dataframe
def open_df_from_file(file):
    """opens the file as a dataframe

    Args:
        file (str): global path and name of data file

    Returns:
        pd.DataFrame: dataframe of opened spreadsheet file
    """    
    fn = os.path.basename(file)
    print(fn)
    fn, ext = os.path.splitext(fn)
    
    try:
        if ext == '.csv':
            df = pd.read_csv(file)
        elif ext == '.txt':
            df = pd.read_csv(file, sep='\t')
        elif ext == '.xls':
            df = pd.read_excel(file, engine='xlrd')
        elif ext =='.xlsx' or ext == '.xlsm':
            df = pd.read_excel(file, engine='openpyxl')
        elif ext =='.qsd':
            df = extract_sensor_data(*read_qsd(file))
        else:
            print("invalid file format or path, please use either .csv, .xls, .xlsx, or .txt (with tab delimiter)")
    except AssertionError as ae:
        msg = f"Error occurred, ensure data file is not protected, and that it is less than 1 million rows.\n"+\
              "if file is protected, create new file and copy data to it"
        print(msg)
        Exceptions.error_popup(msg)
    
    return df

def extract_num_from_string(string):
    """takes string of column header and returns the overtone number it is associated with


    Args:
        string (str): string to convert to number

    Returns:
        int: integer found and cast from string
    """    
    if string.__contains__('fundamental'):
        return 1
    else:
        pattern = r'\d+'
        return int(re.search(pattern, string).group())


def rename_cols(df, cols_dict):
    """changes all column headers to one standard format using a specified dict containing old and new cols

    Args:
        df (pd.DataFrame): experimental data as dataframe to change column names of
        cols_dict (dictionary): dictionary with keys being original column name and value being new

    Returns:
        pd.DataFrame: dataframe post column name formatting
    """
    relevant_cols = []
    for col in list(cols_dict.keys()):
        if col in df.columns:
            relevant_cols.append(col)
        else:
            del cols_dict[col]
    if not relevant_cols:
        msg = "Found no column headers corresponding to the selected device in data file.\n"+\
                "Please ensure that the correct device was selected (e.g. QSense, QCMi, etc.).\n"+\
                "And the column headers in your data file are the default output headers."
        Exceptions.error_popup(msg)
        return None
    slim_df = df[relevant_cols]
    fmt_df = slim_df.rename(columns=cols_dict)
    return fmt_df

def add_offsets(calibration_df, fmt_df):
    """takes offset values and adds them to all data values in corresponding columns
    will take into account that some columns may not be recorded

    Args:
        calibration_df (pd.DataFrame): dataframe of offset values, entered by user in window or directly into file
        fmt_df (pd.DataFrame): experimental data dataframe that has had column renaming a priori

    Returns:
        pd.Dataframe: dataFrame after offset adding
    """
    for col in calibration_df.columns:
        if col in fmt_df.columns:
            fmt_df[col] += calibration_df[col].iloc[0]
            print(calibration_df[col].iloc[0])

    return fmt_df

def unnormalize(df):
    """multiplies frequency values in all columns by their respective overtone number
    certain devices record their data normalized, data analysis relies on non-normalized frequency
    dissipation is not recorded as normalized by these devices, so need not unnormalize it

    Args:
        df (pd.DataFrame): dataframe that contains normalized frequency values

    Returns:
        pd.DataFrame: dataframe containing now unnormalized frequency values
    """    
    #overtones = np.asarray([i if i%2 == 1 else i-1 for i in range(1,15)])
    #overtones = np.insert(overtones, 0,0)
    for col in enumerate(df.columns):
        if col[1].__contains__("freq"): # only frequency needs un-normalization
            # get number prepending column header
            overtone_num = extract_num_from_string(col[1])
            df.loc[:, col[1]] *= overtone_num

    return df

def dissipation_magnitude_adjustment(df, full_columns=False):
    """adjust the magnitude of dissipation data to report values on the order of 1e^-6

    Args:
        df (pd.Dataframe): dataframe containing dissipation data to adjust

    Returns:
        pd.Dataframe: dissipation magnitude adjusted data
    """    
    if not full_columns:
        local_disps = [dissipation in disps for dissipation in df.columns] # account for cols not recorded in df
    else:
        local_disps = disps
    df.loc[:, local_disps] = df.loc[:, local_disps].apply(lambda x: x*1e-6)

    return df


def format_QCM_next(df):
    """format data from openQCM-Next to fit BraTaDio execution
    renames columns
    
    Args:
        df (pd.DataFrame): dataframe containing experimental data recorded from openQCM-next

    Returns:
        pd.DataFrame: dataframe formatted to BraTaDio standard
    """    
    renamed_cols_dict = {'Time':'abs_time', 'Relative_time':'Time',
            'Frequency_0':freqs[0],'Dissipation_0':disps[0],
            'Frequency_1':freqs[1], 'Dissipation_1':disps[1],
            'Frequency_2':freqs[2], 'Dissipation_2':disps[2],
            'Frequency_3':freqs[3], 'Dissipation_3':disps[3],
            'Frequency_4':freqs[4], 'Dissipation_4':disps[4],
            'Temperature':'Temp'}

    fmt_df = rename_cols(df, renamed_cols_dict)
    
    return fmt_df

def format_QCMi(df):
    """format data from QCM-i to fit BraTaDio execution
    renames columns
    
    Args:
        df (pd.DataFrame): dataframe containing experimental data recorded from QCM-i

    Returns:
        pd.DataFrame: dataframe formatted to BraTaDio standard
    """    
    print("QCM-i selected")
    renamed_cols_dict = {'Channel A QCM Time [sec]':'Time',
            'Channel A Fundamental Frequency [Hz]':freqs[0],'Channel A Fundamental Dissipation [ ]':disps[0],
            'Channel A 3. Overtone [Hz]':freqs[1], 'Channel A 3. Dissipation  [ ]':disps[1],
            'Channel A 5. Overtone [Hz]':freqs[2], 'Channel A 5. Dissipation  [ ]':disps[2],
            'Channel A 7. Overtone [Hz]':freqs[3], 'Channel A 7. Dissipation  [ ]':disps[3],
            'Channel A 9. Overtone [Hz]':freqs[4], 'Channel A 9. Dissipation  [ ]':disps[4],
            'Channel A 11. Overtone [Hz]':freqs[5], 'Channel A 11. Dissipation  [ ]':disps[5],
            'Channel A 13. Overtone [Hz]':freqs[6], 'Channel A 13. Dissipation  [ ]':disps[6],
            'Channel A Temp [Celsius]':'Temp'}
    
    fmt_df = rename_cols(df, renamed_cols_dict)

    return fmt_df

def format_Qsense(df, calibration_df=pd.DataFrame({})):
    """format data from QSense to fit BraTaDio execution
    renames columns, converts dissipation magnitude, unnormalizes, adds offsets
    
    Args:
        df (pd.DataFrame): dataframe containing experimental data recorded from QSense
        calibration_df (pd.DataFrame): dataframe containing offset data recorded by user

    Returns:
        pd.DataFrame: dataframe formatted to BraTaDio standard
    """    
    print("Qsense selected")

    renamed_cols_dict = {'Time_1':'Time',
        'F_1:1':freqs[0], 'D_1:1':disps[0],
        'F_1:3':freqs[1], 'D_1:3':disps[1],
        'F_1:5':freqs[2], 'D_1:5':disps[2],
        'F_1:7':freqs[3], 'D_1:7':disps[3],
        'F_1:9':freqs[4], 'D_1:9':disps[4],
        'F_1:11':freqs[5], 'D_1:11':disps[5],
        'F_1:13':freqs[6], 'D_1:13':disps[6],
        'Meas. Temp. Time':'Temp_Time', 'Tact':'Temp'}

    df = rename_cols(df, renamed_cols_dict)

    if calibration_df.empty:
        print("Opting for theoretical values, calibration values will NOT be added to data")
        return df
    
    df = dissipation_magnitude_adjustment(df)    
    df = unnormalize(df)
    df = add_offsets(calibration_df, df)

    return df

def format_AWSensors(df, calibration_df):
    """format data from AWSensors to fit BraTaDio execution
    renames columns, converts dissipation magnitude, unnormalizes, adds offsets
    
    Args:
        df (pd.DataFrame): dataframe containing experimental data recorded from AWSensors

    Returns:
        pd.DataFrame: dataframe formatted to BraTaDio standard
    """    
    print("AWSensors selected")

    renamed_cols_dict = {'Time_(s)':'Time',
        'Delta_F/n_n=3_(Hz)':freqs[1], 'Delta_D_n=3_()':disps[1],
        'Delta_F/n_n=5_(Hz)':freqs[2], 'Delta_D_n=5_()':disps[2],
        'Delta_F/n_n=7_(Hz)':freqs[3], 'Delta_D_n=7_()':disps[3],
        'Delta_F/n_n=9_(Hz)':freqs[4], 'Delta_D_n=9_()':disps[4],
        'Delta_F/n_n=11_(Hz)':freqs[5], 'Delta_D_n=11_()':disps[5]}

    fmt_df = rename_cols(df, renamed_cols_dict)

    if calibration_df.empty:
        print("Opting for theoretical values, calibration values will NOT be added to data")
        return fmt_df
    

    fmt_df = dissipation_magnitude_adjustment(fmt_df)    
    fmt_df = unnormalize(fmt_df)
    fmt_df = add_offsets(calibration_df, fmt_df)

    return fmt_df


def build_formatted_df(src_type, data_file, will_use_theoretical_vals):
    """format a data file into BraTaDio's dataframe shape without writing it to disk."""
    file_name, ext = os.path.splitext(data_file)
    file_name = os.path.basename(file_name)

    # check if file has already been formatted previously
    if data_file.__contains__("Formatted"):
        print(f"{file_name} has been formatted previously, using previously formatted file...")
        return open_df_from_file(data_file)

    data_df = open_df_from_file(data_file)

    # check if column headers match BraTaDio fmt
    is_preformatted = check_file_previously_formatted(data_df, ext)
    if is_preformatted:
        formatted_df = data_df
    else:
        print(f"*** Before formatting\n{data_df}")
        if src_type == 'QCM-d':
            formatted_df = format_QCM_next(data_df)
        elif src_type == 'QCM-i':
            formatted_df = format_QCMi(data_df)
        elif src_type == 'Qsense' and ext == '.qsd':
            calibration_df = open_df_from_file("offset_data/COPY-PASTE_OFFSET_VALUES_HERE.csv")
            formatted_df = data_df
        elif src_type == 'Qsense' or src_type == 'AWSensors':
            if not will_use_theoretical_vals:
                calibration_df = open_df_from_file("offset_data/COPY-PASTE_OFFSET_VALUES_HERE.csv")
            else:
                calibration_df = pd.DataFrame()
            formatted_df = format_Qsense(data_df, calibration_df) if src_type == 'Qsense' else format_AWSensors(data_df, calibration_df)
        else:
            print("invalid option selected")

    print(file_name)
    print(f"*** After formatting\n{formatted_df}")
    return formatted_df


def check_file_previously_formatted(df, ext):
    """checks column headers to see if it has been previously formatted by software
    warns user if True

    Args:
        df (pd.Dataframe): data frame from recently opened file
        ext (str): data file extension

    Returns:
        bool: returns True if column headers match BraTaDio fmt, False if not or if qsd
    """    
    if ext == '.qsd': # if file is qsd it will not have been preprocessed
        return False

    column_header_match_flag = False
    for header in freqs:
        if header in df.columns:
            column_header_match_flag = True
            break
    
    if column_header_match_flag:
        msg = "WARNING: Column headers indicate data file has already been processed by pyQCM.\n" +\
                "If this is incorrect, please double check the correct file was selected and that it has the original column headers.\n" +\
                "Otherwise, pyQCM will proceed with file as is."
        print(msg)
        Exceptions.warning_popup(msg)
        return True
    else:
        return False


def format_raw_data(src_type, data_file, will_use_theoretical_vals):
    """main function for data formatting/column header renaming
    determines which file is being worked with and calls functions appropriately

    Args:
        src_type (str): indicates selection from UI regarding which device recorded the given data
        data_file (str): data file path/name
        will_use_theoretical_vals (bool): indicates to use experimental (from user) or theoretical (from file) offset values
    """    
    file_name, ext = os.path.splitext(data_file)
    file_name = os.path.basename(file_name)
    # check if file has already been formatted previously
    if data_file.__contains__("Formatted"):
        print(f"{file_name} has been formatted previously, using previously formatted file...")
        return
    
    data_df = open_df_from_file(data_file)

    # check if column headers match BraTaDio fmt
    is_preformatted = check_file_previously_formatted(data_df, ext)
    if is_preformatted:
        formatted_df = data_df

    else:
        print(f"*** Before formatting\n{data_df}")
        if src_type == 'QCM-d':
            formatted_df = format_QCM_next(data_df)
        elif src_type == 'QCM-i':
            formatted_df = format_QCMi(data_df)
        elif src_type == 'Qsense' and ext == '.qsd':
            calibration_df = open_df_from_file("offset_data/COPY-PASTE_OFFSET_VALUES_HERE.csv")
            formatted_df = data_df
        elif src_type == 'Qsense' or src_type == 'AWSensors':
            if not will_use_theoretical_vals:
                calibration_df = open_df_from_file("offset_data/COPY-PASTE_OFFSET_VALUES_HERE.csv")
            else:
                calibration_df = pd.DataFrame()
            formatted_df = format_Qsense(data_df, calibration_df) if src_type == 'Qsense' else format_AWSensors(data_df, calibration_df)
        else:
            print("invalid option selected")

    
    print(file_name)
    print(f"*** After formatting\n{formatted_df}")
    formatted_df.to_csv(f"raw_data/Formatted-{file_name}.csv", index=False)


if __name__ == '__main__':
    format_raw_data('Qsense', 'sample_generations/2020-02-05-Col-I only with wash.qsd', False)
