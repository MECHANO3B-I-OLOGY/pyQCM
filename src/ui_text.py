"""
Display-safe text for the Tk UI.

Some Linux Tk builds (e.g. Anaconda's default 'tk' package) can only use X11 core fonts, which usually
lack characters like Δ, so Tk draws them as escape codes instead (e.g. '\\u0394f'), or not at all in Tk 9.
ui_text() checks whether the UI font can actually draw each special character, and only if it cannot,
substitutes a readable ASCII equivalent. Windows and macOS Tk, and Linux Tk built with Xft (fontconfig)
draw these characters normally, so text is left unchanged there.

Plots are not affected, matplotlib renders text with its own fonts (see get_plot_preferences in analyze.py).
"""

import tkinter.font as tkfont
import unicodedata

# ASCII equivalents for special characters used, or likely to be used, in UI text
ASCII_FALLBACKS = {
    'Δ': 'Delta ', 'δ': 'delta ', 'Γ': 'Gamma ', 'γ': 'gamma ', 'Ω': 'Ohm', 'ω': 'omega ',
    'μ': 'u', 'µ': 'u', 'λ': 'lambda ', 'π': 'pi', 'ρ': 'rho', 'σ': 'sigma', 'η': 'eta', 'τ': 'tau',
    '²': '^2', '³': '^3', '°': ' deg', '±': '+/-', '×': 'x', '·': '*', '÷': '/',
    '≈': '~', '≤': '<=', '≥': '>=', '≠': '!=', '→': '->', '←': '<-',
    '–': '-', '—': '-', '‘': "'", '’': "'", '“': '"', '”': '"', '…': '...',
}

_can_render_cache = {}
_notified = False


def _escape_code(ch):
    return f'\\u{ord(ch):04x}' if ord(ch) <= 0xFFFF else f'\\U{ord(ch):08x}'


def can_render(ch, font):
    """Tk 8.6 draws characters missing from every available font as their escape code,
    and Tk 9 draws nothing (zero width), so either measurement means the character cannot be drawn"""
    if ch not in _can_render_cache:
        width = font.measure(ch)
        _can_render_cache[ch] = width > 0 and width != font.measure(_escape_code(ch))
    return _can_render_cache[ch]


def ascii_equivalent(ch):
    if ch in ASCII_FALLBACKS:
        return ASCII_FALLBACKS[ch]
    # accented letters etc. (é -> e), anything else becomes '?'
    decomposed = unicodedata.normalize('NFKD', ch).encode('ascii', 'ignore').decode()
    return decomposed or '?'


def ui_text(text):
    """returns text with any characters the Tk UI font cannot draw replaced by ASCII equivalents

    Args:
        text (str): text for a Tk widget, window title, or popup message

    Returns:
        str: the same text if all of it can be drawn (always the case on Windows/macOS)
    """
    global _notified
    if text is None or text.isascii():
        return text
    try:
        font = tkfont.nametofont('TkDefaultFont')
    except RuntimeError: # no Tk root window yet, cannot check
        return text

    safe_text = ''.join(ch if ch.isascii() or can_render(ch, font) else ascii_equivalent(ch) for ch in text)
    if safe_text != text and not _notified:
        _notified = True
        print("Note: this Tk installation cannot display some special characters (e.g. Greek letters like Delta), showing ASCII equivalents in the UI instead. "
              "Plots are unaffected. See the README (Run from source) for a Python whose Tk supports them.")
    return safe_text
