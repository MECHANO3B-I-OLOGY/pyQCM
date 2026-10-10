from tkinter import messagebox

from src.ui_text import ui_text

def error_popup(msg=None):
    msg = "Uncaught unknown exception has occurred, please view the terminal for details" if msg == None else msg
    messagebox.showerror("Error", ui_text(str(msg)))

def warning_popup(msg):
    messagebox.showwarning("Warning", ui_text(str(msg)))

class ShapeMismatchException(Exception):
    def __init__(self, shapes, msg):
        self.shapes = shapes if shapes else (0,0)
        self.msg = msg if msg else None

    def __str__(self):
        if self.msg:
            msg = f"SHAPE MISMATCH ERROR CAUGHT: {self.msg}\nDimensions must be equal, found {self.shapes[0]} and {self.shapes[1]}"
            error_popup(msg)
            return msg
        else:
            return "SHAPE MISMATCH ERROR CAUGHT"
        
class MissingPlotCustomizationException(Exception):
    def __init__(self, opt, msg):
        self.missing_option = opt if opt else ''
        self.msg = msg if msg else None
        
    def __str__(self):
        if self.msg:
            msg = f"PLOT CUSTOMIZATION ERROR CAUGHT: {self.msg}\nMissing input for field: {self.missing_option}"
            error_popup(msg)
            return msg
        else:
            return "PLOT CUSTOMIZATION ERROR CAUGHT"
        
class InputtedIntPlotOvertoneNotSelectedException(Exception):
    def __init__(self, overtone_selected, msg):
        self.overtone_selected = overtone_selected if overtone_selected else ''
        self.msg = msg if msg else None

    def __str__(self):
        if self.msg:
            msg = f"INTERACTIVE PLOT ERROR CAUGHT: {self.msg}\n{self.overtone_selected} inputted to analyze, but not selected in checkboxes"
            error_popup(msg)
            return msg
        else:
            return "INTERACTIVE PLOT ERROR CAUGHT"