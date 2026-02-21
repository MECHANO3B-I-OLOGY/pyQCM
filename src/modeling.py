"""
Author: Brandon Pardi
Created: 12/30/2022
Last Modified: 1/5/2024
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit, least_squares
import os
import sys

import src.Exceptions as Exceptions
from src.analyze import get_plot_preferences, get_num_from_string, prepare_stats_file, range_statistics

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

PI = np.pi


def propogate_bandwidth_err(val, pair):
    """ proporgate the error for the bandwidth calculation -> delta_dis * rf / 2
    pass in the result of the multiplication to be propogated, and the original values w/ err
    inner most are individual values [val_x1, val_x2, ... val_xn]
    a pair is a len 2 list with the original value and its error [val_x, stddex_x],

    returns propogated multiplication error of set of average data
    main purpose is to find error in bandwidth calculation (delta_D * f_0 / 2)

    Args:
        val (np.array): array of values that are the result of the multiplication that is now being propagated
        pair (size 2 list of np.array): 2D array containing a pair of 2 arrs, the value used in the bandwidth mult, and its error

    Returns:
        np.array: array of error values corresponding to the values resulting from the bandwidth multiplication requiring this function
    """    
    comp = np.zeros(len(pair[0]), dtype=float)
    # pair[0] is the array of values, pair[1] is the array of errors corresponding with those values
    for i in range(len(pair[0])):
        if pair[0][i] == 0: # this is 0 for overtones not recorded/selected
            comp[i] = 0 # error for overtones with no data is 0
        else: # error propagation for multiplication
            comp[i] = np.power(float(( pair[1][i] / pair[0][i] )), 2) # (sigma_x / x_mu) ** 2

    err = val * np.sqrt( comp )
    return (err)

def propogate_mean_err(n_means, errs, n_srcs):
    """propagation of error for mean calculations
    we already have the error values assoc with the values we found the mean of,
    so the propagation is simply a sum of squares of these errors, div by n-1 (or n if just 1 mean)

    appears unnecessarily complicated, but this will work for multiple sources in one pass

    Args:
        n_means (int): number of mean values to have errors propagated
        errs (list): error values associated with mean calculations
        n_srcs (int): number of range selections made

    Returns:
        list: list of propagated error values associated with the means
    """    
    comp = 0
    sigmas = []
    # the new error is the square root of the sum of the squares of the errors and divide it by n_srcs
    for i in range(n_means):
        for j in range(n_srcs):
            comp += np.power( ( errs[j][i] ), 2 )
        if n_srcs == 1:
            sigmas.append(np.sqrt(comp))
        else:
            sigmas.append(np.sqrt( comp/( n_srcs-1 ) ))

    return sigmas

def linear(x, m, b):
    """linear equation y = mx + b used for linear regression"""
    return m * x + b

def elastic_modulus_stiffening(n):
    """sub component of the crystal thickness equation
    all values are constants and there is no fitting or solving here (consts defn below)

    Args:
        n (int): overtone number

    Returns:
        float: elastic modulus of quarts
    """    
    # constants
    mu_q = 2.93e10      # N/m^2 elastic modulus of quarts
    epsilon = -9.24e-2  # C/m^2 piezoelectric stress coefficient
    kappa = 3.982e-11   # F/m   effecting dielectric constant for quartz
    
    # variables
    # n is the overtone number

    # elastic modulus of quarts accounting for piezoelectric stiffening
    mu_qn = mu_q + ( epsilon ** 2 / kappa )\
            - ( (8 * epsilon ** 2) / (PI ** 2 * n ** 2 * kappa) )
    
    return mu_qn

def crystal_thickness_eqn(n, h_q):
    """equation for the linear fitting of the crystal thickness model

    Args:
        n (int): overtone number
        h_q (float): crystal thickness (fitting parameter)

    Returns:
        float: resonant frequency
    """    
    # constants
    rho_q = 2649.7      # kg/m^3 density of quarts

    # variables
    # f_Rn resonant frequency
    # n is overtone number
    mu_qn = elastic_modulus_stiffening(n)

    # fitting paramaters
    # h_q mm crystal thickness

    f_Rn = ( n / ( 2 * h_q )) * np.sqrt( mu_qn / rho_q )
    return f_Rn

def gk_eqn(mu_Df_n, f0):
    """Gordon-Kanazawa equation
    CURRENTLY NOT IN USE

    Args:
        mu_Df_n (float): average change in frequency of the given overtone
        f0 (float): resonant frequency of the fundamental overtone

    Returns:
        _type_: _description_
    """    
    # constants
    rhoQ = 2650 # (kg/m^3) density of quartz
    muQ = 3.3698e-4 # (m) thickness of quartz

    # fitting parameters
    ''' eta*rho = kinematic viscosity
        rhoL (kg/m^3) 
        etaL (Pa*s) dynamic viscosity
    '''
    kinematic_viscosity = ( np.power(mu_Df_n, 2) * PI * muQ * rhoQ ) / np.power(f0, 3)
    return kinematic_viscosity

def get_overtones_selected(which_plot):
    """simple util function to return list of overtones being selected
    given the dictionary of selections from the UI
    """
    overtones = []
    
    for ov in which_plot.items():
        if ov[1] and ov[0].__contains__('freq'):
            overtones.append([ov[0][:-5]]) # append the overtone
    
    return overtones

def get_calibration_values(which_plot, use_theoretical_vals):
    """obtain offset values from the file 'COPY_PASTE_OFFSET_VALUES_HERE.csv' if user opted for experimental,
    or 'theoretical_frequencies.csv' is user chose theoretical
    overtones not selected have entries filled with 0

    sigma_calibration_vals SHOULD BE REMOVED IT IS VESTIGIAL

    Args:
        which_plot (dict): dictionary of overtones with bools indicating if they were selected for analysis
        use_theoretical_vals (bool): indicates whether to use theoretical or offset (calibration) vals

    Returns:
        _type_: _description_
    """    
    which_freq_plots = {}
    calibration_freq = []
    print(use_theoretical_vals)

    # clean which_plot and remove the dis keys since we only need freq
    for key, val in which_plot.items():
        if key.__contains__('freq'):
            which_freq_plots[key] = val

    if use_theoretical_vals:        
        # theoretical calibration values for experiment, used in calculating bandwidth shift
        theoretical_values_df = pd.read_csv(resource_path("offset_data/theoretical_frequencies.csv"), index_col=False)
        theoretical_values = theoretical_values_df.filter(like="freq").values.flatten()
        print(f"theo vals: {theoretical_values}")

        for i, ov in enumerate(which_freq_plots.items()): # for items in which plot,
            if ov[1]:  # if true, insert the value from theoretical values
                calibration_freq.append(theoretical_values[i])
            else: # and 0 if false
                calibration_freq.append(0)

        print(f"*** Theoretical Calibration Frequencies: {calibration_freq}")
        
    else:
        # grab peak frequency values from calibration file as specified in gui
        all_overtones = [get_num_from_string(ov) for ov in which_freq_plots.keys()] # get all overtones to insert 0s into overtones not selected\
        selected_overtones = [get_num_from_string(ov[0]) if ov[1] else 0 for ov in which_freq_plots.items()]
        exp_vals_df = pd.read_csv(resource_path("offset_data/COPY-PASTE_OFFSET_VALUES_HERE.csv"), index_col=False).filter(like="freq")
        i = 0
        while(i < len(all_overtones)): # all ovs always >= selected overtones
            print(selected_overtones, all_overtones[i], selected_overtones[i])
            if i < len(selected_overtones) and all_overtones[i] == selected_overtones[i]:
                print(exp_vals_df.head())
                print(exp_vals_df.iloc[0,i])
                calibration_freq.append(exp_vals_df.iloc[0,i])
            else:
                calibration_freq.append(0)
            i+=1

        print(f"*** Experimental Calibration Frequencies: {calibration_freq}")
        
    return calibration_freq

def avg_and_propogate(label, sources, df, is_frequency):
    """group data, average it w.r.t. overtones, and propagate

    Args:
        label (str): user specified identifier of the range of data they selected
        source (str): file name that data originated from
        df (_type_): dataframe of statistical calculations of range selected by user
        is_frequency (bool): _description_

    Returns:
        _type_: _description_
    """    
    df_ranges = df.loc[df['range_name'] == label]

    # group data by range and then source
    # values get averaged across sources respective to their range
    # i.e. average( <num from range 'x' source1>, <num from range 'x' source2>, ... )
    delta_vals = []
    sigma_delta_vals = []
    if is_frequency:
        delta_col = 'Dfreq_average'
        sigma_delta_col = 'Dfreq_std_dev'
    else:
        delta_col = 'Ddis_average'
        sigma_delta_col = 'Ddis_std_dev'

    for source in sources: # grabs data grouped by label and further groups into source
        df_range = df_ranges.loc[df_ranges['data_source'] == source]
        delta_vals.append(df_range[delta_col].values)
        sigma_delta_vals.append(df_range[sigma_delta_col].values)
        
    # take average described above
    n_srcs = len(sources) # num sources -> number of ranges used for average
    mean_delta_vals = np.zeros(delta_vals[0].shape)
    for i in range(n_srcs):
        print(mean_delta_vals, delta_vals)
        mean_delta_vals += delta_vals[i]
    
    mean_delta_vals /= n_srcs
    sigma_mean_delta_vals = propogate_mean_err(len(mean_delta_vals), sigma_delta_vals, n_srcs)
    
    # make 0 for non selected overtones
    zero_idxs = np.where(mean_delta_vals == 0)[0].astype(int)
    sigma_mean_delta_vals = np.array(sigma_mean_delta_vals)
    sigma_mean_delta_vals[zero_idxs] = 0

    print(zero_idxs, sigma_mean_delta_vals)

    return mean_delta_vals, sigma_mean_delta_vals


def remove_zero_elements(arrs):
    """takes in a list of arrays of data, finds locations where elements are 0, and removes them from both

    Args:
        arrs (list of np.Array): list of arrays of data that need 0s removed

    Returns:
        (list of np.Array): list of arrays of data that have had 0s removed

    """
    cleaned_arrs = []
    for arr in arrs:
        indices = np.where(arr==0.)
        arr = np.delete(arr, indices[0])
        cleaned_arrs.append(arr)

    return cleaned_arrs

def plot_data(xdata, ydata, xerr, yerr, label, has_err, color='black'):
    """plot x and y data with or without error bars

    Args:
        xdata (_type_): x axis data to be plotted, can take any type that plt.plot() accepts
        ydata (_type_): y axis data to be plotted, can take any type that plt.plot() accepts
        xerr (_type_): error associated with x data, can take any type that plt.plot() accepts
        yerr (_type_): error associated with x data, can take any type that plt.plot() accepts
        label (_type_): legend label for plot
        has_err (bool): determines if there is error associated with the data, which dictates plotting of error bars
        color (str, optional): color of plot. Defaults to 'black'.

    Returns:
        plt.Figure, plt.Axes: figure and axes objects with the plotted data
    """    
    fig = plt.figure()
    plt.clf()
    plt.subplots_adjust(hspace=0.4)
    ax = fig.add_subplot(1,1,1)
    plt.cla()

    # plotting modeled data slightly different than range data
    if has_err:
        xerr = np.abs(xerr) if xerr is not None else xerr
        yerr = np.abs(yerr) if yerr is not None else yerr
        if label:
            ax.plot(xdata, ydata, 'o', markersize=4, label=label, color=color)
            ax.errorbar(xdata, ydata, xerr=xerr, yerr=yerr, fmt='.', label='std dev', color=color)
        else:
            ax.plot(xdata, ydata, 'o', markersize=4, color=color)
            print(f"\n***\n{xerr} \n\n {yerr} \n\n")
            ax.errorbar(xdata, ydata, xerr=xerr, yerr=yerr, fmt='.', color=color)
    else:
        ax.plot(xdata, ydata, 'o', markersize=4, label=label, color=color)

    return fig, ax

def linearly_analyze(x, y, ax, label_prefix='', label_postfix=''):
    """handles the linear fit and necessary operations surrounding it

    Args:
        x (_type_): x data for linear fit
        y (_type_): y data for fit
        ax (plt.Axes): axes for plotting fit
        label_prefix (str, optional): text to write to legend preceeding the slope value. Defaults to ''.
        label_postfix (str, optional): text to write to legend following the slope value. Defaults to ''.

    Returns:
        slope, y-intercept: results of the linear fit
    """    
    # performing the linear fit 
    params, cov = curve_fit(linear, x, y)
    m, b = params
    sign = '-' if b < 0 else '+' 

    # calculate linear fit data
    y_fit = linear(np.asarray(x), m, b)

    # determine quality of the fit
    squaredDiffs = np.square(y - y_fit)
    squaredDiffsFromMean = np.square(y - np.mean(y))
    rSquared = 1 - np.sum(squaredDiffs) / np.sum(squaredDiffsFromMean)
    print(f"R² = {rSquared}")

    # for reporting Sauerbrey mass given slope

    # put label together
    if label_prefix == '' and label_postfix == '':
        label = f'Linear fit:\ny = {m:.4f}x {sign} {np.abs(b):.4f}'
    else:
        label = label_prefix + f"{m:.4e} " + label_postfix
    
    # plot curve fit
    ax.plot(x, y_fit, 'r', label=label)

    return m, b

def format_plot(ax, x_label, y_label, title, xticks=np.asarray(None)):
    """apply formatting from plot customs and add labels and title
    """
    plot_customs = get_plot_preferences()
    font = plot_customs['font']
    if xticks.any():
        ax.set_xticks(xticks)
    plt.sca(ax)
    plt.legend(loc='best', fontsize=plot_customs['legend_text_size'], prop={'family': font}, framealpha=0.3)
    plt.xticks(fontsize=plot_customs['value_text_size'], fontfamily=font)
    plt.yticks(fontsize=plot_customs['value_text_size'], fontfamily=font) 
    plt.xlabel(x_label, fontsize=plot_customs['label_text_size'], fontfamily=font)
    plt.ylabel(y_label, fontsize=plot_customs['label_text_size'], fontfamily=font)
    plt.tick_params(axis='both', direction=plot_customs['tick_dir'])
    plt.title(title, fontsize=plot_customs['title_text_size'], fontfamily=font)


def get_labels(label, type, subtype='', usetex=False):
    """grab plot labels determined by which function modeling

    Args:
        label (str): user spec'd range identifier
        type (str): model that data is currently being applied to
        subtype (str, optional): subtype specific to certain models. Defaults to ''.
        usetex (bool, optional): will use latex formatting for plot. Defaults to False.

    Returns:
        list of strings: strings containing the determined, data (legend) label, plot title, and axis labels
    """
    if type == 'film_liquid':
        data_label = None
        title = "Thin Film in Liquid " + r"$\frac{\mathit{\Delta}\mathit{\Gamma}}{\mathit{-\Delta}f} \approx J^{\prime}_{f}\omega\eta_{bulk}$" + f"  for range: {label}"
        x = r"Overtone $\cdot$ Change in frequency, $\mathit{n\cdot\Delta}$$\mathit{f}$$_n$ (Hz)"
        y = r"Bandwidth shift, $\mathit{\Delta\Gamma}$$_n$"

    elif type == 'film_air':
        data_label = None
        title = "Thin Film in Air " + f"for range: {label}"
        x = r"$\mathit{n^2}$"
        if subtype == 'gamma': # $\frac{ng}{cm^2}$
            y = r"Normalized bandwidth shift, $\frac{\mathit{\Delta}\mathit{\Gamma_{n}}}{\mathit{n}}$ Hz"
        elif subtype == 'freq':
            y = r"Normalized change in frequency, $\frac{\mathit{\Delta}f_{n}}{\mathit{n}}$ Hz"
        else:
            y = 'placeholder'
    
    elif type == 'crystal':
        data_label = None
        title = "Crystal Thickness"
        y = r"Resonant frequency, $\it{f_{Rn}}$ (Hz)"
        x = 'Overtone order, $\it{n}$'

    elif type == 'sauerbrey':
        data_label = f"average"
        title = f"Average Change in Frequency for Sauerbrey Mass\nfor Range: {label}"
        x = 'Overtone order, $\it{n}$'
        if subtype == 'fit':
            y = r'Average change in frequency, $\it{Δf_{n}}$ ' + '(Hz)'
        if subtype == 'avgs':
            y = r'Sauerbrey mass, $\it{m_{n}}$ ($\frac{ng}{cm^2}$)'

    elif type == 'avgs':
        data_label = f"average"
        x = 'Overtone order, $\it{n}$'
        if subtype == 'freq':
            title = f"Average Change in Frequency\nfor Range: {label}"
            y = r'Average change in frequency, $\it{Δf_{n}}$ ' + '(Hz)'
        if subtype == 'dis':
            title = f"Average Change in Dissipation\nfor Range: {label}"
            y = r'Average change in dissipation, $\it{ΔD_{n}}$'
    
    else:
        return None

    return data_label, x, y, title

def process_bandwidth_calculations_for_linear_regression(which_plot, sources, rf_df, dis_df, label, use_theoretical_vals):
    """takes statistical data from user's interactive plot selection,
    and prepares it for linear regression calculations for thin film models
    this involves getting calibration values, averaging, propagating, and converting dissipation to bandwidth

    Args:
        which_plot (dict): dictionary of overtones where they value is a bool indicating if overtone is selected
        sources (list): list of strings indicating which files the data came from
        rf_df (pd.DataFrame): dataframe from 'selected_ranges/clean_all_stats_rf.csv'
        dis_df (pd.DataFrame): dataframe from 'selected_ranges/clean_all_stats_dis.csv'
        label (str): user spec'd identifier of range being selected and models being applied to
        use_theoretical_vals (bool): determines if offset values will be theoretical or experimental

    Returns:
        np.Arrays: experimental values and their errors post processing
    """    
    calibration_freq = get_calibration_values(which_plot, use_theoretical_vals)
    print(rf_df, dis_df)
    mean_delta_freqs, sigma_mean_delta_freqs = avg_and_propogate(label, sources, rf_df, True)
    print("###", mean_delta_freqs, sigma_mean_delta_freqs)
    n_mean_delta_freqs = [Df * (2*i+1) for i, Df in enumerate(mean_delta_freqs)] # 2i+1 corresponds to overtone number
    sigma_n_mean_delta_freqs = [sDf * (2*i+1) for i, sDf in enumerate(sigma_mean_delta_freqs)] 
    mean_delta_dis, sigma_mean_delta_dis = avg_and_propogate(label, sources, dis_df, False)        
    
    print(f"*** rf for label: {label}\n\tn*means: {n_mean_delta_freqs}\n\tstddev: {sigma_n_mean_delta_freqs}\n")
    print(f"*** dis for label: {label}:\n\tmeans: {mean_delta_dis}\n\tstddev: {sigma_mean_delta_dis}\n")

    # calculate bandwidth shift and propogate error for this calculation
    #dis_w_err = [np.array(mean_delta_dis), np.array(sigma_mean_delta_dis)]
    delta_gamma = np.array(mean_delta_dis * calibration_freq / 2) # bandwidth shift, Γ
    
    # due to refactor there is no y error only x, this means no mult error prop needed, the error is just x err times delta_gamma
    #sigma_delta_gamma = propogate_bandwidth_err(delta_gamma, dis_w_err)
    sigma_delta_gamma = delta_gamma * sigma_mean_delta_dis

    # remove entries of freqs not being analyzed
    arrs = [delta_gamma, sigma_delta_gamma, np.array(n_mean_delta_freqs), np.array(sigma_n_mean_delta_freqs)]
    delta_gamma, sigma_delta_gamma, n_mean_delta_freqs, sigma_n_mean_delta_freqs = remove_zero_elements(arrs)

    return n_mean_delta_freqs, delta_gamma, sigma_n_mean_delta_freqs, sigma_delta_gamma
    

def thin_film_liquid_analysis(which_plot, use_theoretical_vals, latex_installed):
    """application of thin film in liquid model
    works for multiple range selections at a time, as long as from same data file

    Args:
        user_input (tuple: (
        which_plot (dict): overtones and booleans on whether or not to plot/analyze
        use_theoretical_vals (bool): indicates to use theoretical values for resonant frequency, or offset
        latex_installed: TO BE DEPRECATED
        )): rely on a tuple passed in of all necessary variables, since tkinter buttons can only pass 1 argument to function

    Raises:
        Exceptions.ShapeMismatchException: raises when there is a different number of overtones selected in ui than found in stats file
    """    
    plot_customs = get_plot_preferences()
    fig_format = plot_customs['fig_format']
    dpi = plot_customs['fig_dpi']
    print("Performing thin film in liquid analysis...")

    # grab statistical data of overtones from files generated in interactive plot
    rf_df = pd.read_csv("selected_ranges/clean_all_stats_rf.csv", index_col=0)
    dis_df = pd.read_csv("selected_ranges/clean_all_stats_dis.csv", index_col=0)

    # grab all unique labels from dataset
    labels = rf_df['range_name'].unique()
    sources = rf_df['data_source'].unique()
    print(f"*** found labels: {labels}\n\t from sources: {sources}\n")
    
    # grab and analyze data for each range and indicated by the label
    for label in labels:
        n_mean_delta_freqs, delta_gamma, sigma_n_mean_delta_freqs, sigma_delta_gamma = process_bandwidth_calculations_for_linear_regression(
            which_plot, sources, rf_df, dis_df, label, use_theoretical_vals)
    
        # plot data
        data_label, x_label, y_label, title = get_labels(label, 'film_liquid', '', latex_installed)
        
        if n_mean_delta_freqs.shape != delta_gamma.shape:
            raise Exceptions.ShapeMismatchException((n_mean_delta_freqs.shape, delta_gamma.shape),"ERROR: Different number of overtones selected in UI than found in stats file")
        print("@#$@#$", n_mean_delta_freqs, delta_gamma)   
        print("@#$@#$", sigma_n_mean_delta_freqs, sigma_delta_gamma)   
        lin_plot, ax = plot_data(n_mean_delta_freqs, delta_gamma, sigma_n_mean_delta_freqs,
                                 sigma_delta_gamma, data_label, True)
        
        # take care of all linear fitting analysis 
        m, b = linearly_analyze(n_mean_delta_freqs, delta_gamma, ax, 'Shear dependent compliance: ', r'$\frac{1}{Pa}$')
        delta_gamma_fit = linear(n_mean_delta_freqs, m, b)

        # save calculations to file
        stats_out_fn = 'selected_ranges/thin_film_liquid_output.csv'                
        header = f"n*Df,bandwidth_shift,bandwidth_shift_FIT,range_name,data_source\n"
        prepare_stats_file(header, label, sources[0], stats_out_fn)
        with open(stats_out_fn, 'a') as stat_file:
            for i in range(len(delta_gamma)):
                stat_file.write(f"{n_mean_delta_freqs[i]:.8E},{delta_gamma[i]:.8E},{delta_gamma_fit[i]:.8E},{label},{sources[0]}\n")

        # save figure
        format_plot(ax, x_label, y_label, title)
        lin_plot.tight_layout() # fixes issue of graph being cut off on the edges when displaying/saving
        plt.savefig(f"qcmd-plots/modeling/thin_film_liquid_{label}.{fig_format}", format=fig_format, bbox_inches='tight', transparent=True, dpi=dpi)
        print("Thin film in liquid analysis complete")
        plt.rc('text', usetex=False)

def thin_film_air_analysis(which_plot, use_theoretical_vals, latex_installed):
    """application of thin film in air model
    works for multiple range selections at a time, as long as from same data file
    similar process to thin film in liquid, but a few extra steps

    Args:
        user_input (tuple: (
        which_plot (dict): overtones and booleans on whether or not to plot/analyze
        use_theoretical_vals (bool): indicates to use theoretical values for resonant frequency, or offset
        latex_installed: TO BE DEPRECATED
        )): rely on a tuple passed in of all necessary variables, since tkinter buttons can only pass 1 argument to function

    Raises:
        Exceptions.ShapeMismatchException: raises when there is a different number of overtones selected in ui than found in stats file
    """   
    plot_customs = get_plot_preferences()
    fig_format = plot_customs['fig_format']
    dpi = plot_customs['fig_dpi']
    print("Performing thin film in liquid analysis...")

    # grab statistical data of overtones from files generated in interactive plot
    rf_df = pd.read_csv("selected_ranges/clean_all_stats_rf.csv", index_col=0)
    dis_df = pd.read_csv("selected_ranges/clean_all_stats_dis.csv", index_col=0)

    # grab all unique labels from dataset
    labels = rf_df['range_name'].unique()
    sources = rf_df['data_source'].unique()
    overtones_df = rf_df[(rf_df!= 0).all(1)] # remove rows with 0 (unselected rows)
    overtones = overtones_df.index.unique()
    overtones = np.asarray([get_num_from_string(ov) for ov in overtones]) # get just the number from overtone labels
    print(f"*** found labels: {labels}\n\t from sources: {sources}\nfor overtones: {overtones}")
    
    # grab and analyze data for each range and indicated by the label
    for label in labels:
        n_mean_delta_freqs, delta_gamma, sigma_n_mean_delta_freqs, sigma_delta_gamma = process_bandwidth_calculations_for_linear_regression(which_plot, sources, rf_df, dis_df, label, use_theoretical_vals)
        
        # for thin film in air, Df and DGamma are normalized
        print("AAA", delta_gamma, overtones)
        delta_gamma_norm = delta_gamma / overtones
        sigma_delta_gamma_norm = sigma_delta_gamma / overtones

        # Df is divided twice since process function returns n*DGamma
        delta_freqs_norm = n_mean_delta_freqs / overtones / overtones
        sigma_delta_freqs_norm = sigma_n_mean_delta_freqs / overtones / overtones

        # plotting against overtones^2
        sq_overtones = overtones * overtones
        print(f"delta_gamma: {delta_gamma}\ndelta_gamma_normalized: {delta_gamma_norm}\nn^2: {sq_overtones}")

        # error checking
        if n_mean_delta_freqs.shape != delta_gamma.shape:
            raise Exceptions.ShapeMismatchException((n_mean_delta_freqs.shape, delta_gamma.shape),"ERROR: Different number of overtones selected in UI than found in stats file")

        # plot data for DGamma/n v n^2
        data_label, x_label, y_label, title = get_labels(label, 'film_air', 'gamma', latex_installed)     
        lin_plot, ax = plot_data(sq_overtones, delta_gamma_norm, None,
                                 sigma_delta_gamma_norm, data_label, True)
        
        # take care of all linear fitting analysis    
        dG_m, dG_b = linearly_analyze(sq_overtones, delta_gamma_norm, ax) 
        delta_gamma_norm_fit = linear(sq_overtones, dG_m, dG_b)

        # save figure
        format_plot(ax, x_label, y_label, title)
        lin_plot.tight_layout() # fixes issue of graph being cut off on the edges when displaying/saving
        plt.savefig(f"qcmd-plots/modeling/thin_film_air_GAMMA_{label}.{fig_format}", format=fig_format, bbox_inches='tight', transparent=True, dpi=dpi)
        
        # repeat above plotting/saving for Df/n v n^2
        data_label, x_label, y_label, title = get_labels(label, 'film_air', 'freq', latex_installed)     
        lin_plot, ax = plot_data(sq_overtones, delta_freqs_norm, None,
                                 sigma_delta_freqs_norm, data_label, True)
        
        # take care of all linear fitting analysis    
        linearly_analyze(sq_overtones, delta_freqs_norm, ax) 
        delta_freq_norm_fit = linear(sq_overtones, dG_m, dG_b)

        # save calculations to file
        stats_out_fn = 'selected_ranges/thin_film_air_output.csv'                
        header = f"sq_overtones,delta_gamma_norm,delta_gamma_norm_fit,delta_freqs_norm,delta_freq_norm_fit,range_name,data_source\n"
        prepare_stats_file(header, label, sources[0], stats_out_fn)
        with open(stats_out_fn, 'a') as stat_file:
            for i in range(len(sq_overtones)):
                stat_file.write(f"{sq_overtones[i]},{delta_gamma_norm[i]:.8E},{delta_gamma_norm_fit[i]:.8E},{delta_gamma_norm[i]:.8E},{delta_freq_norm_fit[i]:.8E},{label},{sources[0]}\n")

        # save figure
        format_plot(ax, x_label, y_label, title)
        lin_plot.tight_layout() # fixes issue of graph being cut off on the edges when displaying/saving
        plt.savefig(f"qcmd-plots/modeling/thin_film_air_FREQ_{label}.{fig_format}", format=fig_format, bbox_inches='tight', transparent=True, dpi=dpi)

        print("Thin film in air analysis complete")
        plt.rc('text', usetex=False)

def gordon_kanazawa(user_input):
    """application of Gordon-Kanazawa model
    NOT FULLY IMPLEMENTED, FUNCTION HERE NOT CALLED ANYWHERE CURRENTLY

    Args:
        user_input (tuple: (
        which_plot (dict): overtones and booleans on whether or not to plot/analyze
        use_theoretical_vals (bool): indicates to use theoretical values for resonant frequency, or offset
        )): rely on a tuple passed in of all necessary variables, since tkinter buttons can only pass 1 argument to function

    """    
    which_plot, will_use_theoretical_vals = user_input
    fig_format = get_plot_preferences()['fig_format']
    print("Analyzing Gordon-Kanazawa Equation...")

    # get offset of fundamental frequency
    if will_use_theoretical_vals:
        f0 = 4998264.628859391 # (HZ) calibration fundamental frequency value (will be experimentally determined later)
    else:
        f0_which_plot = which_plot
        f0_which_plot['fundamental_freq'] = True
        f0 = np.asarray(get_calibration_values(f0_which_plot, will_use_theoretical_vals)[0])[0] # get offset data
    print(f"***f0 = {f0}")

    # for saving output data
    header = "overtone,average_Df,average_Df_n,kinematic_viscosity,range_name,data_source\n"
    stats_out_fn = 'selected_ranges/gordon-kanazawa_output.csv'                

    # grab data from file
    stats_df = pd.read_csv("selected_ranges/clean_all_stats_rf.csv")
    stats_df = stats_df[(stats_df!= 0).all(1)] # remove freq rows with 0 (unselected rows)
    labels = stats_df['range_name'].unique()
    print(labels)
    overtone_labels = stats_df['overtone'].unique() # overtone number (x)
    overtones = np.asarray([get_num_from_string(ov) for ov in overtone_labels]) # get just the number from overtone labels
    source = stats_df['data_source'].unique()[0]

    for label in labels:
        stats_df_range = stats_df.loc[stats_df['range_name'] == label]
        mu_Df = stats_df_range['Dfreq_average'].values # grab averages and normalize
        mu_Df_n = mu_Df / overtones # grab averages and normalize
        sigma_mu_Df_n = stats_df_range['Dfreq_std_dev'].values
        kinematic_viscosity = gk_eqn(mu_Df_n, f0)
        print(f"** Kinematic Viscocity for {label}: {kinematic_viscosity}")
        prepare_stats_file(header, label, source, stats_out_fn)
        with open(stats_out_fn, 'a') as stat_file:
            for i in range(len(kinematic_viscosity)):
                stat_file.write(f"{overtones[i]},{mu_Df[i]},{mu_Df_n[i]},{kinematic_viscosity[i]},{label},{source}\n")

    print("Gordon-Kanazawa Analysis Complete")


def crystal_thickness(which_plot, will_use_theoretical_vals):
    """application of quartz crystal thickness model
    linear regression on offset value data to crystal thickness eqn, slope (h_q) is reported in mm

    Args:
        user_input (tuple: (
        which_plot (dict): overtones and booleans on whether or not to plot/analyze
        use_theoretical_vals (bool): indicates to use theoretical values for resonant frequency, or offset
        )): rely on a tuple passed in of all necessary variables, since tkinter buttons can only pass 1 argument to function

    """      
    plot_customs = get_plot_preferences()
    fig_format = plot_customs['fig_format']
    dpi = plot_customs['fig_dpi']
    
    overtones = get_overtones_selected(which_plot) # get overtones
    overtones = [get_num_from_string(n[0]) for n in overtones]
    print(get_calibration_values(which_plot, will_use_theoretical_vals),'\n', get_calibration_values(which_plot, will_use_theoretical_vals)[0])
    offset_vals = np.asarray(get_calibration_values(which_plot, will_use_theoretical_vals)) # get offset data
    offset_vals = offset_vals[offset_vals != 0]

    if offset_vals.size == 0:
        msg = "WARNING: offset values array empty\n\n" +\
                "Please ensure that offset values are selected rather than theoretical,\n"+\
                "And that RAW overtones are selected for analysis rather than shifted."
        print(msg)
        Exceptions.warning_popup(msg)

    # performing the for crystal thickness equation fit 
    print(overtones, offset_vals)
    params, cov = curve_fit(crystal_thickness_eqn, overtones, offset_vals)
    h_q = params[0]

    # calculate fit data
    y_fit = crystal_thickness_eqn(np.asarray(overtones), h_q)

    # determine quality of the fit
    squaredDiffs = np.square(offset_vals - y_fit)
    squaredDiffsFromMean = np.square(offset_vals - np.mean(offset_vals))
    rSquared = 1 - np.sum(squaredDiffs) / np.sum(squaredDiffsFromMean)
    print(f"R² = {rSquared}")

    # plotting data with fit
    data_label, x_label, y_label, title = get_labels('','crystal')
    crystal_fig, crystal_ax = plot_data(overtones, offset_vals, None, None, data_label, False)
    crystal_label = f"Crystal thickness: {h_q*1000:.4f} (mm)\n" + r'$R^2$: ' + f"{rSquared:.4f}"
    crystal_ax.plot(overtones, y_fit, 'r', label=crystal_label, zorder=-1)
    format_plot(crystal_ax, x_label, y_label, title, np.asarray(overtones))

    crystal_fig.tight_layout()
    crystal_fig.savefig(f"qcmd-plots/modeling/crystal_thickness.{fig_format}", format=fig_format, bbox_inches='tight', transparent=True, dpi=dpi)

    stats_out_fn = 'selected_ranges/crystal_thickness_output.csv'                
    header = f"overtone,offset_vals,offset_vals_FIT,crystal_thickness(mm)\n"
    with open(stats_out_fn, 'w') as stat_file:
        stat_file.write(header)
        for i in range(len(overtones)):
            stat_file.write(f"{overtones[i]},{offset_vals[i]:.8E},{y_fit[i]:.8E},{h_q*1000:.8E}\n")


def sauerbrey_avgs(mu_Df, delta_mu_Df, C, overtones, label, fig_format, dpi):
    """method 2 of applying Sauerbrey model
    finds mu_Dm and delta_mu_Dm over the range selected for EACH overtone
    works for multiple range selections at a time, as long as from same data file

    Args:
        mu_Df (np.Array): numpy array of floats containing avg change in frequencies for each overtone 
        delta_mu_Df (np.Array): numpy array of floats containing error for avg change in frequencies for each overtone 
        C (float): mass sensitivity constant obtained in parent sauerbrey() function 
        overtones (np.Array): numpy array of integers containing overtone numbers selected
        label (str): label for legend in plot
        fig_format (str): user spec'd file format for the figure
        dpi (int): dots per inch of figure (quality)

    Raises:
        Exceptions.ShapeMismatchException: raises when there is a different number of overtones selected in ui than found in stats file
    
    Returns:
        mu_Dm (np.Array): average change in Sauerbrey mass for each selected overtone
        delta_mu_Dm (np.Array): error in average change in Sauerbrey mass for each selected overtone

    """   
    # method 2 avg rf * C for each overtone
    mu_Df = np.array(mu_Df)
    mu_Dm = mu_Df * C / overtones
    delta_mu_Dm = np.abs(delta_mu_Df * C / overtones)

    if mu_Df.shape != overtones.shape:
        raise Exceptions.ShapeMismatchException((mu_Df.shape, overtones.shape),"ERROR: Different number of overtones selected in UI than found in stats file")
    
    data_label, x_label, y_label, title = get_labels(label, 'sauerbrey', 'avgs')
    avg_Dm_fig, avg_Dm_ax = plot_data(overtones, mu_Dm, None, delta_mu_Dm, data_label, True)
    format_plot(avg_Dm_ax, x_label, y_label, title, overtones)
    avg_Dm_fig.tight_layout()
    plt.savefig(f"qcmd-plots/modeling/Sauerbrey_avgs_range_{label}.{fig_format}", format=fig_format, bbox_inches='tight', transparent=True, dpi=dpi)

    return mu_Dm, delta_mu_Dm

def sauerbrey_fit(df, overtones, label, C, fig_format, dpi):
    """method 2 of applying Sauerbrey model
    finds mu_Dm and delta_mu_Dm over the range selected for EACH overtone
    works for multiple range selections at a time, as long as from same data file

    Args:
        df (pd.DataFrame): contains the statistical information from range selection in interactive plot
        overtones (np.Array): numpy array of integers containing overtone numbers selected
        label (str): label for legend in plot
        C (float): mass sensitivity constant obtained in parent sauerbrey() function 
        fig_format (str): user spec'd file format for the figure
        dpi (int): dots per inch of figure (quality)

    Raises:
        Exceptions.ShapeMismatchException: raises when there is a different number of overtones selected in ui than found in stats file

    Returns:
        mu_Df (np.Array): array of floats containing the average change in Sauerbrey mass
        delta_mu_Df (np.Array): array of floats containing error for the average change in Sauerbrey mass
        mu_Df_fit (np.Array): array of floats containing the linear fit for average change in Sauerbrey mass (slope * C is mass)

    """    
    # grabbing data from df
    df_range = df.loc[df['range_name'] == label]
    # method 1 of Sauerbrey mass (linear fit slope * C)
    mu_Df = df_range['Dfreq_average'].values.astype(np.float32) # average change in frequency (y)
    delta_mu_Df = df_range['Dfreq_std_dev'].values # std dev of y
    print('***',mu_Df,delta_mu_Df)

    if mu_Df.shape != overtones.shape:
        raise Exceptions.ShapeMismatchException((mu_Df.shape, overtones.shape),"ERROR: Different number of overtones selected in UI than found in stats file")
    
    # plotting average frequencies
    data_label, x_label, y_label, title = get_labels(label, 'sauerbrey', 'fit')
    # weird bug made ydata list of strings in certain dataset
    mu_Df = [float(y) for y in mu_Df]
    avg_Df_fig, avg_Df_ax = plot_data(overtones, mu_Df, None, delta_mu_Df, data_label, True)

    # take care of all linear fitting analysis    
    m, b = linearly_analyze(overtones, mu_Df, avg_Df_ax)
    mu_Df_fit = linear(overtones, m, b)

    format_plot(avg_Df_ax, x_label, y_label, title, overtones)
    avg_Df_fig.tight_layout()
    plt.legend().get_texts()[1].set_text("Sauerbrey mass: " + f"{m*C:.1f}" + r" ($\frac{ng}{cm^2}$)")
    plt.savefig(f"qcmd-plots/modeling/Sauerbrey_fit_range_{label}.{fig_format}", format=fig_format, bbox_inches='tight', transparent=True, dpi=dpi)

    return mu_Df, delta_mu_Df, mu_Df_fit

def sauerbrey(use_theoretical_vals):
    plot_customs = get_plot_preferences()
    fig_format = plot_customs['fig_format']
    dpi = plot_customs['fig_dpi']
    print("Analyzing Sauerbrey equation...")

    # grabbing df from csv
    df = pd.read_csv("selected_ranges/clean_all_stats_rf.csv")
    df = df[(df!= 0).all(1)] # remove freq rows with 0 (unselected rows)
    labels = df['range_name'].unique()
    overtones = df['overtone'].unique() # overtone number (x)
    overtones = np.asarray([get_num_from_string(ov) for ov in overtones]) # get just the number from overtone labels
    sources = df['data_source'].unique()
    print(f"LABELS: {labels}; OVERTONES: {overtones}")

    # calculate C for Sauerbrey mass formula if user opts to use calibration vals
    C = -17.7 # default theoretical value
    if not use_theoretical_vals:
        calibration_df = pd.read_csv(resource_path("offset_data/COPY-PASTE_OFFSET_VALUES_HERE.csv"))
        f0 = calibration_df.loc[0]['fundamental_freq']
        print(f"f0: {f0}")

        quarts_wave_velocity = 3340
        quartz_density = 2650
        C = -1 * ( quarts_wave_velocity * quartz_density ) / ( 2 * ( f0 ** 2 )  )
        C *= 1e8 # unit conversion
    print(f"C: {C}")

    for label in labels:
        mu_Df, delta_mu_Df, mu_Df_fit = sauerbrey_fit(df, overtones, label, C, fig_format, dpi)
        mu_Dm, delta_mu_Dm = sauerbrey_avgs(mu_Df, delta_mu_Df, C, overtones, label, fig_format, dpi)

        # save calculations to file
        stats_out_fn = 'selected_ranges/sauerbrey_output.csv'                
        header = f"overtone,avg_Df,avg_Df_err,avg_Df_FIT,avg_Dm,avg_Dm_err,C,range_name,data_source\n"
        prepare_stats_file(header, label, sources[0], stats_out_fn)
        with open(stats_out_fn, 'a') as stat_file:
            for i in range(len(mu_Df)):
                stat_file.write(f"{overtones[i]},{mu_Df[i]:.8E},{delta_mu_Df[i]:.8E},{mu_Df_fit[i]:.8E},{mu_Dm[i]:.8E},{delta_mu_Dm[i]:.8E},{C:.8E},{label},{sources[0]}\n")
        
    print("Sauerbrey analysis complete")
    plt.rc('text', usetex=False)

def avgs_analysis():
    """plot the average change in frequency and dissipation of range selection for each overtone

    Raises:
        Exceptions.ShapeMismatchException: raises when there is a different number of overtones selected in ui than found in stats file
    """    
    plot_customs = get_plot_preferences()
    fig_format = plot_customs['fig_format']
    dpi = plot_customs['fig_dpi']
    print("Analyzing average change in frequency and dissipation...")

    # grabbing df from csv
    rf_df = pd.read_csv("selected_ranges/clean_all_stats_rf.csv")
    rf_df = rf_df[(rf_df!= 0).all(1)] # remove freq rows with 0 (unselected rows)
    dis_df = pd.read_csv("selected_ranges/clean_all_stats_dis.csv")
    dis_df = dis_df[(dis_df!= 0).all(1)] # remove dis rows with 0 (unselected rows)
    labels = rf_df['range_name'].unique()
    overtones = rf_df['overtone'].unique() # overtone number (x)
    overtones = np.asarray([get_num_from_string(ov) for ov in overtones]) # get just the number from overtone labels
    print(f"LABELS: {labels}; OVERTONES: {overtones}")

    for label in labels:
        # grabbing data from df
        rf_df_range = rf_df.loc[rf_df['range_name'] == label]
        dis_df_range = dis_df.loc[dis_df['range_name'] == label]
        mu_Df = rf_df_range['Dfreq_average'].values # average change in frequency (y)
        delta_mu_Df = rf_df_range['Dfreq_std_dev'].values # std dev of y
        mu_Dd = dis_df_range['Ddis_average'].values # average change in dissipation (y)
        delta_mu_Dd = dis_df_range['Ddis_std_dev'].values # std dev of y

        if mu_Df.shape != overtones.shape:
            raise Exceptions.ShapeMismatchException((mu_Df.shape, overtones.shape),"ERROR: Different number of overtones selected in UI than found in stats file")
        
        # plotting average frequencies
        print(fig_format)
        data_label, x_label, y_label, title = get_labels(label, 'avgs', 'freq')
        avg_Df_range_plot, ax = plot_data(overtones, mu_Df, None, delta_mu_Df, data_label, True)
        format_plot(ax, x_label, y_label, title, overtones)
        avg_Df_range_plot.tight_layout()
        plt.savefig(f"qcmd-plots/modeling/Avg_Df_range_{label}.{fig_format}", format=fig_format, bbox_inches='tight', transparent=True, dpi=dpi)

        # plotting average dissipations
        data_label, x_label, y_label, title = get_labels(label, 'avgs', 'dis')
        avg_Dd_range_plot, ax = plot_data(overtones, mu_Dd, None, delta_mu_Dd, data_label, True)
        format_plot(ax, x_label, y_label, title, overtones)
        avg_Dd_range_plot.tight_layout()
        plt.savefig(f"qcmd-plots/modeling/Avg_Dd_range_{label}.{fig_format}", format=fig_format, bbox_inches='tight', transparent=True, dpi=dpi)

    print("Average change in frequency and dissipation analysis complete")
    plt.rc('text', usetex=False)


# main used for testing
if __name__ == "__main__":
    which_plot = {'raw': {'fundamental_freq': False, 'fundamental_dis': False, '3rd_freq': False, '3rd_dis': False,
                            '5th_freq': False, '5th_dis': False, '7th_freq': False, '7th_dis': False,
                            '9th_freq': False, '9th_dis': False, '11th_freq': False, '11th_dis': False,
                            '13th_freq': False, '13th_dis': False},

                    'clean': {'fundamental_freq': True, 'fundamental_dis': True, '3rd_freq': True, '3rd_dis': True,
                            '5th_freq': True, '5th_dis': True, '7th_freq': True, '7th_dis': True,
                            '9th_freq': True, '9th_dis': True, '11th_freq': True, '11th_dis': True,
                            '13th_freq': False, '13th_dis': False}}
    
    #linear_regression((which_plot['clean'], True, False))
    gordon_kanazawa((which_plot['clean'], True))