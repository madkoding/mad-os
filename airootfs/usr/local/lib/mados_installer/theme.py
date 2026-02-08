"""
madOS Installer - Nord theme CSS for GTK3
"""

from gi.repository import Gtk, Gdk

from .config import (
    NORD_POLAR_NIGHT, NORD_SNOW_STORM, NORD_FROST, NORD_AURORA
)


def apply_theme():
    """Apply Nord dark theme to the entire application"""
    css_provider = Gtk.CssProvider()
    css = f"""
        * {{
            outline-width: 0;
        }}
        
        window {{ 
            background-color: {NORD_POLAR_NIGHT['nord0']};
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        .demo-banner {{
            background-color: {NORD_AURORA['nord12']};
            color: {NORD_POLAR_NIGHT['nord0']};
            font-weight: bold;
            padding: 5px;
        }}
        
        .title {{ 
            font-size: 24px; 
            font-weight: bold; 
            color: {NORD_SNOW_STORM['nord6']}; 
        }}
        
        .subtitle {{ 
            font-size: 13px; 
            color: {NORD_FROST['nord8']}; 
        }}
        
        label {{ 
            color: {NORD_SNOW_STORM['nord6']};
            background-color: transparent;
        }}
        
        radio, checkbutton {{
            color: {NORD_SNOW_STORM['nord6']};
            background-color: transparent;
        }}
        
        radio:checked {{
            color: {NORD_FROST['nord8']};
        }}
        
        entry {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            color: {NORD_SNOW_STORM['nord6']};
            border: 1px solid {NORD_POLAR_NIGHT['nord3']};
            border-radius: 5px;
            padding: 6px;
            caret-color: {NORD_FROST['nord8']};
        }}
        
        entry:focus {{
            background-color: {NORD_POLAR_NIGHT['nord2']};
            border: 1px solid {NORD_FROST['nord9']};
        }}
        
        entry selection {{
            background-color: {NORD_FROST['nord9']};
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        combobox button {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            background-image: none;
            color: {NORD_SNOW_STORM['nord6']};
            border: 1px solid {NORD_POLAR_NIGHT['nord3']};
            border-radius: 5px;
            padding: 6px;
        }}
        
        combobox button:hover {{
            background-color: {NORD_POLAR_NIGHT['nord2']};
            background-image: none;
        }}
        
        combobox button cellview {{
            color: {NORD_SNOW_STORM['nord6']};
            background-color: transparent;
        }}
        
        combobox window.popup {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
        }}
        
        combobox window.popup > frame > border {{
            border-color: {NORD_POLAR_NIGHT['nord3']};
        }}
        
        combobox menu, combobox .menu {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        combobox menu menuitem, combobox .menu menuitem {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            color: {NORD_SNOW_STORM['nord6']};
            padding: 6px 10px;
        }}
        
        combobox menu menuitem:hover, combobox .menu menuitem:hover {{
            background-color: {NORD_FROST['nord9']};
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        cellview {{
            background-color: transparent;
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        menu, .menu, .popup {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        menuitem {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        menuitem:hover {{
            background-color: {NORD_FROST['nord9']};
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        button {{
            background-image: linear-gradient(to bottom, {NORD_FROST['nord10']}, #4A6A94);
            color: #FFFFFF;
            border: none;
            border-radius: 5px;
            padding: 8px 16px;
            font-weight: bold;
            text-shadow: 0px 1px 2px rgba(0, 0, 0, 0.3);
        }}
        
        button:hover {{
            background-image: linear-gradient(to bottom, {NORD_FROST['nord9']}, {NORD_FROST['nord10']});
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.4);
        }}
        
        button:active {{
            background-image: linear-gradient(to bottom, #4A6A94, {NORD_FROST['nord10']});
        }}
        
        .warning-button {{
            background-image: linear-gradient(to bottom, {NORD_AURORA['nord11']}, #9A3B44);
            color: #FFFFFF;
        }}
        
        .warning-button:hover {{
            background-image: linear-gradient(to bottom, #D08080, {NORD_AURORA['nord11']});
        }}
        
        .success-button {{
            background-image: linear-gradient(to bottom, {NORD_AURORA['nord14']}, #7A9168);
            color: #FFFFFF;
        }}
        
        .success-button:hover {{
            background-image: linear-gradient(to bottom, #B5D49E, {NORD_AURORA['nord14']});
        }}
        
        progressbar {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            border-radius: 5px;
        }}
        
        progressbar trough {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            border-radius: 5px;
            min-height: 20px;
        }}
        
        progressbar progress {{
            background-image: linear-gradient(to right, {NORD_FROST['nord8']}, {NORD_FROST['nord10']});
            border-radius: 5px;
            min-height: 20px;
        }}
        
        .warning-box {{
            background-color: {NORD_AURORA['nord11']};
            border-radius: 5px;
            padding: 10px;
            margin: 5px;
        }}
        
        .warning-box label {{
            color: {NORD_SNOW_STORM['nord6']};
            font-weight: bold;
        }}
        
        .info-box {{
            background-color: {NORD_FROST['nord10']};
            border-radius: 5px;
            padding: 10px;
            margin: 5px;
        }}
        
        .info-box label {{
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        .success-box {{
            background-color: {NORD_AURORA['nord14']};
            border-radius: 5px;
            padding: 10px;
            margin: 5px;
        }}
        
        .success-box label {{
            color: {NORD_POLAR_NIGHT['nord0']};
        }}
        
        .summary-card {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            border-left: 4px solid {NORD_FROST['nord8']};
            border-radius: 5px;
            padding: 15px;
            margin: 10px;
        }}
        
        textview {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            color: {NORD_SNOW_STORM['nord5']};
            padding: 10px;
        }}
        
        textview text {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            color: {NORD_SNOW_STORM['nord5']};
        }}
        
        scrolledwindow {{
            background-color: {NORD_POLAR_NIGHT['nord0']};
        }}
        
        list, listbox {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        listbox row {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        listbox row:hover {{
            background-color: {NORD_POLAR_NIGHT['nord2']};
        }}
        
        listbox row:selected {{
            background-color: {NORD_FROST['nord9']};
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        messagedialog, dialog {{
            background-color: {NORD_POLAR_NIGHT['nord0']};
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        messagedialog .titlebar, dialog .titlebar {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        messagedialog box, dialog box {{
            background-color: {NORD_POLAR_NIGHT['nord0']};
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        messagedialog label, dialog label {{
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        messagedialog .dialog-action-area button, dialog .dialog-action-area button {{
            background-image: linear-gradient(to bottom, {NORD_FROST['nord10']}, #4A6A94);
            color: #FFFFFF;
            border: none;
            border-radius: 5px;
            padding: 8px 20px;
        }}
        
        messagedialog .dialog-action-area button:hover, dialog .dialog-action-area button:hover {{
            background-image: linear-gradient(to bottom, {NORD_FROST['nord9']}, {NORD_FROST['nord10']});
        }}
        
        .welcome-container {{
            background-color: {NORD_POLAR_NIGHT['nord0']};
        }}
        
        .welcome-title {{
            font-size: 28px;
            font-weight: bold;
            color: {NORD_SNOW_STORM['nord6']};
        }}
        
        .welcome-subtitle {{
            font-size: 13px;
            color: {NORD_FROST['nord8']};
            font-style: italic;
        }}
        
        .welcome-divider {{
            background-color: {NORD_FROST['nord8']};
            min-height: 2px;
        }}
        
        .feature-card {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            border-radius: 8px;
            padding: 8px 12px;
        }}
        
        .feature-icon {{
            color: {NORD_FROST['nord8']};
            font-size: 16px;
        }}
        
        .feature-text {{
            color: {NORD_SNOW_STORM['nord4']};
            font-size: 13px;
        }}
        
        .start-button {{
            background-image: linear-gradient(to bottom, {NORD_FROST['nord8']}, {NORD_FROST['nord10']});
            color: {NORD_POLAR_NIGHT['nord0']};
            border: none;
            border-radius: 8px;
            padding: 10px 32px;
            font-size: 14px;
            font-weight: bold;
        }}
        
        .start-button:hover {{
            background-image: linear-gradient(to bottom, {NORD_FROST['nord7']}, {NORD_FROST['nord9']});
            box-shadow: 0 4px 12px rgba(136, 192, 208, 0.3);
        }}
        
        .exit-button {{
            background-color: transparent;
            background-image: none;
            color: {NORD_POLAR_NIGHT['nord3']};
            border: 1px solid {NORD_POLAR_NIGHT['nord3']};
            border-radius: 8px;
            padding: 10px 24px;
            font-size: 13px;
            font-weight: normal;
        }}
        
        .exit-button:hover {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            background-image: none;
            color: {NORD_SNOW_STORM['nord4']};
            border-color: {NORD_SNOW_STORM['nord4']};
        }}
        
        .lang-label {{
            color: {NORD_POLAR_NIGHT['nord3']};
            font-size: 12px;
        }}
        
        .version-label {{
            color: {NORD_POLAR_NIGHT['nord3']};
            font-size: 11px;
        }}
        
        /* ── Page Layout ── */
        .page-container {{
            background-color: {NORD_POLAR_NIGHT['nord0']};
        }}
        
        .page-header {{
            margin-top: 6px;
            margin-bottom: 2px;
        }}
        
        .page-divider {{
            background-color: {NORD_POLAR_NIGHT['nord2']};
            min-height: 1px;
        }}
        
        /* ── Navigation ── */
        .nav-back-button {{
            background-color: transparent;
            background-image: none;
            color: {NORD_SNOW_STORM['nord4']};
            border: 1px solid {NORD_POLAR_NIGHT['nord3']};
            border-radius: 6px;
            padding: 8px 18px;
            font-weight: normal;
        }}
        
        .nav-back-button:hover {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            background-image: none;
            color: {NORD_SNOW_STORM['nord6']};
            border-color: {NORD_SNOW_STORM['nord4']};
        }}
        
        /* ── Content Cards ── */
        .content-card {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            border-radius: 10px;
            padding: 12px 16px;
        }}
        
        /* ── Warning Banner ── */
        .warning-banner {{
            background-color: rgba(191, 97, 106, 0.15);
            border-radius: 8px;
            padding: 6px 12px;
        }}
        
        /* ── Partition Options ── */
        .partition-card {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            border-radius: 10px;
            padding: 10px 14px;
            border: 2px solid {NORD_POLAR_NIGHT['nord2']};
        }}
        
        /* ── Partition Bar ── */
        .partition-bar-efi {{
            background-color: {NORD_AURORA['nord13']};
            border-radius: 4px 0 0 4px;
            min-height: 22px;
            padding: 1px 6px;
        }}
        
        .partition-bar-root {{
            background-color: {NORD_FROST['nord9']};
            min-height: 22px;
            padding: 1px 6px;
        }}
        
        .partition-bar-home {{
            background-color: {NORD_AURORA['nord14']};
            border-radius: 0 4px 4px 0;
            min-height: 22px;
            padding: 1px 6px;
        }}
        
        .partition-bar-root-only {{
            background-color: {NORD_FROST['nord9']};
            border-radius: 0 4px 4px 0;
            min-height: 22px;
            padding: 1px 6px;
        }}
        
        /* ── Form Styling ── */
        .form-card {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            border-radius: 10px;
            padding: 16px 20px;
        }}
        
        /* ── Summary Cards ── */
        .summary-card-system {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            border-left: 4px solid {NORD_FROST['nord8']};
            border-radius: 8px;
            padding: 10px 14px;
        }}
        
        .summary-card-account {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            border-left: 4px solid {NORD_AURORA['nord15']};
            border-radius: 8px;
            padding: 10px 14px;
        }}
        
        .summary-card-partitions {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            border-left: 4px solid {NORD_AURORA['nord13']};
            border-radius: 8px;
            padding: 10px 14px;
        }}
        
        .summary-card-software {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            border-left: 4px solid {NORD_AURORA['nord14']};
            border-radius: 8px;
            padding: 10px 14px;
        }}
        
        /* ── Completion Page ── */
        .completion-card {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            border-radius: 10px;
            padding: 14px 18px;
            border-left: 4px solid {NORD_AURORA['nord14']};
        }}
        
        /* ── Disk Cards ── */
        .disk-card {{
            background-color: {NORD_POLAR_NIGHT['nord1']};
            background-image: none;
            border-radius: 10px;
            padding: 0;
            border: 2px solid {NORD_POLAR_NIGHT['nord2']};
            text-shadow: none;
        }}
        
        .disk-card:hover {{
            background-color: {NORD_POLAR_NIGHT['nord2']};
            background-image: none;
            border-color: {NORD_FROST['nord9']};
        }}
        
        .disk-card-selected {{
            background-color: rgba(136, 192, 208, 0.08);
            background-image: none;
            border-radius: 10px;
            padding: 0;
            border: 2px solid {NORD_FROST['nord8']};
            text-shadow: none;
        }}
        
        .disk-card-selected:hover {{
            background-color: rgba(136, 192, 208, 0.12);
            background-image: none;
            border-color: {NORD_FROST['nord8']};
        }}
        
        .disk-type-badge {{
            background-color: {NORD_POLAR_NIGHT['nord2']};
            background-image: none;
            border-radius: 6px;
            padding: 4px 10px;
            min-width: 50px;
        }}
        
        .disk-type-nvme {{
            background-color: rgba(136, 192, 208, 0.2);
            background-image: none;
            border-radius: 6px;
            padding: 4px 10px;
            min-width: 50px;
        }}
        
        .disk-type-ssd {{
            background-color: rgba(163, 190, 140, 0.2);
            background-image: none;
            border-radius: 6px;
            padding: 4px 10px;
            min-width: 50px;
        }}
        
        .disk-type-hdd {{
            background-color: rgba(216, 222, 233, 0.1);
            background-image: none;
            border-radius: 6px;
            padding: 4px 10px;
            min-width: 50px;
        }}
        
        .demo-banner {{
            background-color: rgba(208, 135, 112, 0.9);
            color: {NORD_POLAR_NIGHT['nord0']};
            border-radius: 0 0 8px 8px;
            padding: 4px 16px;
            font-weight: bold;
        }}
        
        /* ── Spinner ── */
        spinner {{
            color: {NORD_FROST['nord8']};
        }}
        
        .install-spinner {{
            min-width: 48px;
            min-height: 48px;
        }}
        """
    css_provider.load_from_data(css.encode())
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        css_provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )
