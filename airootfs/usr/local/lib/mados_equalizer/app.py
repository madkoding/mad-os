"""
madOS Audio Equalizer - Main Application Window
=================================================

Provides the main GTK3 application window with an 8-band parametric
equalizer interface. Features vertical sliders for each frequency band,
visual gain indicators, preset management, master volume control,
and language selection.

The window is designed for the Sway compositor with Nord theme styling
and an app_id of "mados-equalizer" for window management rules.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Pango
import cairo
import threading

from . import __app_id__, __app_name__, __version__
from .backend import AudioBackend
from .presets import (
    PresetManager, FREQUENCY_BANDS, BAND_LABELS, BAND_KEYS,
    GAIN_MIN, GAIN_MAX, GAIN_DEFAULT, BUILTIN_PRESET_ORDER,
)
from .translations import (
    TRANSLATIONS, AVAILABLE_LANGUAGES, DEFAULT_LANGUAGE, get_text, detect_system_language,
)
from .theme import apply_theme, get_gain_color, get_gain_color_hex, NORD


class GainIndicator(Gtk.DrawingArea):
    """Custom drawing area that displays a colored bar representing gain level.

    The bar color reflects the gain value:
        - Positive: green to yellow gradient
        - Negative: blue shading
        - Zero: gray

    Attributes:
        gain: The current gain value in dB.
    """

    def __init__(self):
        """Initialize the gain indicator with zero gain."""
        super().__init__()
        self.gain = 0.0
        self.set_size_request(20, 80)
        self.connect('draw', self._on_draw)

    def set_gain(self, gain_db):
        """Update the displayed gain value and redraw.

        Args:
            gain_db: The gain value in dB (-12 to +12).
        """
        self.gain = gain_db
        self.queue_draw()

    def _on_draw(self, widget, cr):
        """Draw the gain indicator bar.

        Args:
            widget: The DrawingArea widget.
            cr: The Cairo context for drawing.
        """
        alloc = widget.get_allocation()
        width = alloc.width
        height = alloc.height

        # Background
        cr.set_source_rgba(0.231, 0.259, 0.322, 1.0)  # #3B4252
        cr.rectangle(0, 0, width, height)
        cr.fill()

        # Border
        cr.set_source_rgba(0.263, 0.298, 0.369, 1.0)  # #434C5E
        cr.set_line_width(1)
        cr.rectangle(0.5, 0.5, width - 1, height - 1)
        cr.stroke()

        # Center line (0 dB reference)
        center_y = height / 2.0
        cr.set_source_rgba(0.298, 0.337, 0.416, 0.8)  # #4C566A with alpha
        cr.set_line_width(1)
        cr.move_to(2, center_y)
        cr.line_to(width - 2, center_y)
        cr.stroke()

        # Gain bar
        if abs(self.gain) > 0.1:
            color = get_gain_color(self.gain)
            cr.set_source_rgba(color.red, color.green, color.blue, 0.85)

            # Calculate bar height relative to gain range
            max_bar_height = (height / 2.0) - 4
            bar_height = abs(self.gain) / 12.0 * max_bar_height

            bar_x = 3
            bar_width = width - 6

            if self.gain > 0:
                # Draw upward from center
                bar_y = center_y - bar_height
                cr.rectangle(bar_x, bar_y, bar_width, bar_height)
            else:
                # Draw downward from center
                bar_y = center_y
                cr.rectangle(bar_x, bar_y, bar_width, bar_height)

            cr.fill()

            # Add a subtle gradient overlay for depth
            if self.gain > 0:
                gradient = cairo.LinearGradient(bar_x, center_y - bar_height, bar_x, center_y)
            else:
                gradient = cairo.LinearGradient(bar_x, center_y, bar_x, center_y + bar_height)

            gradient.add_color_stop_rgba(0, 1.0, 1.0, 1.0, 0.15)
            gradient.add_color_stop_rgba(1, 0.0, 0.0, 0.0, 0.1)
            cr.set_source(gradient)

            if self.gain > 0:
                cr.rectangle(bar_x, center_y - bar_height, bar_width, bar_height)
            else:
                cr.rectangle(bar_x, center_y, bar_width, bar_height)
            cr.fill()

        return False


class EqualizerApp:
    """Main application class for the madOS Audio Equalizer.

    Creates and manages the GTK3 window with all UI elements including
    the 8-band equalizer sliders, preset controls, master volume,
    and status information.

    Attributes:
        language: The current UI language.
        backend: The AudioBackend instance for PipeWire/PA integration.
        preset_manager: The PresetManager for preset operations.
        window: The main GTK3 window.
        band_scales: List of 8 Gtk.Scale widgets for EQ bands.
        band_labels: List of 8 Gtk.Label widgets showing dB values.
        gain_indicators: List of 8 GainIndicator widgets.
        preset_combo: The Gtk.ComboBoxText for preset selection.
        enable_button: The toggle button for enabling/disabling EQ.
        volume_scale: The Gtk.Scale for master volume.
        volume_label: The Gtk.Label showing volume percentage.
        device_label: The Gtk.Label showing active output device.
        status_label: The Gtk.Label showing status messages.
    """

    def __init__(self):
        """Initialize the application, create UI, and show the window."""
        self.language = detect_system_language()
        self._updating_sliders = False
        self._updating_preset = False

        # Initialize backend and preset manager
        self.backend = AudioBackend()
        self.preset_manager = PresetManager()

        # Apply Nord theme
        apply_theme()

        # Build the UI
        self._build_window()
        self._build_ui()

        # Load initial state
        self._refresh_device_info()
        self._refresh_volume()

        # Show the window
        self.window.show_all()

    def _t(self, key):
        """Get translated text for a key using the current language.

        Args:
            key: The translation key.

        Returns:
            The translated string.
        """
        return get_text(key, self.language)

    def _build_window(self):
        """Create and configure the main application window."""
        self.window = Gtk.Window()
        self.window.set_title(self._t('title'))
        self.window.set_default_size(750, 450)
        self.window.set_resizable(True)
        self.window.set_position(Gtk.WindowPosition.CENTER)

        # Set app_id for Sway window management
        # In Wayland/GTK3, the app_id is derived from the application name
        self.window.set_wmclass(__app_id__, __app_name__)
        # Also set the role for additional identification
        self.window.set_role(__app_id__)

        self.window.connect('destroy', self._on_destroy)
        self.window.connect('delete-event', self._on_delete)

    def _build_ui(self):
        """Build the complete user interface."""
        # Main vertical layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.window.add(main_box)

        # Top bar: title + enable toggle + language selector
        top_bar = self._build_top_bar()
        main_box.pack_start(top_bar, False, False, 0)

        # Separator
        sep1 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        main_box.pack_start(sep1, False, False, 0)

        # Preset bar
        preset_bar = self._build_preset_bar()
        main_box.pack_start(preset_bar, False, False, 0)

        # Separator
        sep2 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        main_box.pack_start(sep2, False, False, 0)

        # Main content: EQ bands + volume
        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        content_box.set_margin_start(12)
        content_box.set_margin_end(12)
        content_box.set_margin_top(8)
        content_box.set_margin_bottom(8)

        # EQ bands area
        eq_box = self._build_eq_bands()
        content_box.pack_start(eq_box, True, True, 0)

        # Vertical separator
        vsep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        content_box.pack_start(vsep, False, False, 4)

        # Master volume area
        volume_box = self._build_volume_control()
        content_box.pack_start(volume_box, False, False, 0)

        main_box.pack_start(content_box, True, True, 0)

        # Separator
        sep3 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        main_box.pack_start(sep3, False, False, 0)

        # Status bar
        status_bar = self._build_status_bar()
        main_box.pack_start(status_bar, False, False, 0)

    def _build_top_bar(self):
        """Build the top bar with title and enable toggle.

        Returns:
            A Gtk.Box containing the top bar widgets.
        """
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        top_bar.set_margin_start(12)
        top_bar.set_margin_end(12)
        top_bar.set_margin_top(8)
        top_bar.set_margin_bottom(8)

        # App title
        title_label = Gtk.Label()
        title_label.set_markup(
            f'<span font_weight="bold" font_size="large" foreground="#ECEFF4">'
            f'{self._t("audio_equalizer")}</span>'
        )
        title_label.set_halign(Gtk.Align.START)
        top_bar.pack_start(title_label, False, False, 0)
        self.title_label = title_label

        # Spacer
        spacer = Gtk.Box()
        top_bar.pack_start(spacer, True, True, 0)

        # Enable/Disable toggle button
        self.enable_button = Gtk.Button(label=self._t('enable'))
        self.enable_button.get_style_context().add_class('toggle-disabled')
        self.enable_button.connect('clicked', self._on_toggle_eq)
        self.enable_button.set_size_request(80, -1)
        top_bar.pack_start(self.enable_button, False, False, 0)

        return top_bar

    def _build_preset_bar(self):
        """Build the preset selection bar.

        Returns:
            A Gtk.Box containing preset controls.
        """
        preset_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        preset_bar.get_style_context().add_class('preset-bar')
        preset_bar.set_margin_start(12)
        preset_bar.set_margin_end(12)
        preset_bar.set_margin_top(4)
        preset_bar.set_margin_bottom(4)

        # Preset label
        preset_label = Gtk.Label(label=self._t('preset') + ':')
        preset_label.get_style_context().add_class('section-label')
        preset_bar.pack_start(preset_label, False, False, 0)
        self.preset_label_widget = preset_label

        # Preset combo box
        self.preset_combo = Gtk.ComboBoxText()
        self._populate_preset_combo()
        self.preset_combo.set_active(0)  # Start with "Flat"
        self.preset_combo.connect('changed', self._on_preset_changed)
        self.preset_combo.set_size_request(120, -1)
        self.preset_combo.set_hexpand(True)
        preset_bar.pack_start(self.preset_combo, True, True, 0)

        # Save preset button
        self.save_button = Gtk.Button(label=self._t('save_preset'))
        self.save_button.get_style_context().add_class('primary-button')
        self.save_button.connect('clicked', self._on_save_preset)
        preset_bar.pack_start(self.save_button, False, False, 0)

        # Delete preset button
        self.delete_button = Gtk.Button(label=self._t('delete_preset'))
        self.delete_button.get_style_context().add_class('danger-button')
        self.delete_button.connect('clicked', self._on_delete_preset)
        self.delete_button.set_sensitive(False)
        preset_bar.pack_start(self.delete_button, False, False, 0)

        # Spacer
        spacer = Gtk.Box()
        preset_bar.pack_start(spacer, True, True, 0)

        # Reset button
        self.reset_button = Gtk.Button(label=self._t('reset'))
        self.reset_button.connect('clicked', self._on_reset)
        preset_bar.pack_start(self.reset_button, False, False, 0)

        return preset_bar

    def _build_eq_bands(self):
        """Build the 8-band equalizer slider panel.

        Creates 8 vertical columns, each containing:
            - dB value label (top)
            - Gain indicator (colored bar)
            - Vertical slider
            - Frequency label (bottom)

        Returns:
            A Gtk.Box containing all 8 band controls.
        """
        eq_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        eq_container.set_homogeneous(True)

        self.band_scales = []
        self.band_labels = []
        self.gain_indicators = []

        for i in range(8):
            band_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            band_box.get_style_context().add_class('eq-band-box')
            band_box.set_margin_start(2)
            band_box.set_margin_end(2)
            band_box.set_margin_top(4)
            band_box.set_margin_bottom(4)

            # dB value label at the top
            db_label = Gtk.Label(label='0 dB')
            db_label.get_style_context().add_class('db-label')
            db_label.set_size_request(-1, 16)
            band_box.pack_start(db_label, False, False, 2)
            self.band_labels.append(db_label)

            # Gain indicator (colored bar)
            indicator = GainIndicator()
            indicator.set_size_request(20, -1)
            indicator.set_vexpand(False)
            indicator.set_hexpand(True)
            indicator.set_valign(Gtk.Align.CENTER)

            # Vertical slider
            adjustment = Gtk.Adjustment(
                value=0.0,
                lower=GAIN_MIN,
                upper=GAIN_MAX,
                step_increment=0.5,
                page_increment=1.0,
                page_size=0.0,
            )

            scale = Gtk.Scale(
                orientation=Gtk.Orientation.VERTICAL,
                adjustment=adjustment,
            )
            scale.set_inverted(True)  # Higher values at top
            scale.set_draw_value(False)
            scale.set_digits(1)
            scale.set_vexpand(True)
            scale.set_size_request(20, 80)

            # Add marks at key positions
            scale.add_mark(12.0, Gtk.PositionType.RIGHT, None)
            scale.add_mark(6.0, Gtk.PositionType.RIGHT, None)
            scale.add_mark(0.0, Gtk.PositionType.RIGHT, None)
            scale.add_mark(-6.0, Gtk.PositionType.RIGHT, None)
            scale.add_mark(-12.0, Gtk.PositionType.RIGHT, None)

            # Connect signal
            scale.connect('value-changed', self._on_band_changed, i)
            self.band_scales.append(scale)

            # Horizontal box for indicator and slider side by side
            slider_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
            slider_box.set_halign(Gtk.Align.CENTER)
            slider_box.pack_start(indicator, False, False, 0)
            slider_box.pack_start(scale, False, False, 0)
            self.gain_indicators.append(indicator)

            band_box.pack_start(slider_box, True, True, 0)

            # Frequency label at the bottom
            freq_text = self._t(BAND_KEYS[i])
            freq_label = Gtk.Label(label=freq_text)
            freq_label.get_style_context().add_class('freq-label')
            freq_label.set_size_request(-1, 16)
            band_box.pack_start(freq_label, False, False, 2)

            eq_container.pack_start(band_box, True, True, 0)

        # Store frequency labels for language updates
        self._freq_labels = []
        for child in eq_container.get_children():
            inner_children = child.get_children()
            if inner_children:
                # Last child is the freq label
                self._freq_labels.append(inner_children[-1])

        return eq_container

    def _build_volume_control(self):
        """Build the master volume control panel.

        Returns:
            A Gtk.Box containing the volume slider and mute button.
        """
        volume_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        volume_box.get_style_context().add_class('volume-box')
        volume_box.set_size_request(60, -1)

        # Volume title
        vol_title = Gtk.Label()
        vol_title.set_markup(
            f'<span font_size="small" foreground="#81A1C1" font_weight="bold">'
            f'{self._t("master_volume")}</span>'
        )
        vol_title.set_line_wrap(True)
        vol_title.set_max_width_chars(10)
        vol_title.set_justify(Gtk.Justification.CENTER)
        volume_box.pack_start(vol_title, False, False, 2)
        self.vol_title_label = vol_title

        # Volume percentage label
        self.volume_label = Gtk.Label(label='100%')
        self.volume_label.get_style_context().add_class('db-label')
        volume_box.pack_start(self.volume_label, False, False, 2)

        # Volume slider (vertical)
        vol_adjustment = Gtk.Adjustment(
            value=100.0,
            lower=0.0,
            upper=150.0,
            step_increment=1.0,
            page_increment=5.0,
            page_size=0.0,
        )

        self.volume_scale = Gtk.Scale(
            orientation=Gtk.Orientation.VERTICAL,
            adjustment=vol_adjustment,
        )
        self.volume_scale.set_inverted(True)
        self.volume_scale.set_draw_value(False)
        self.volume_scale.set_digits(0)
        self.volume_scale.set_vexpand(True)
        self.volume_scale.get_style_context().add_class('master-volume')

        # Add marks at key positions
        self.volume_scale.add_mark(150.0, Gtk.PositionType.LEFT, None)
        self.volume_scale.add_mark(100.0, Gtk.PositionType.LEFT, None)
        self.volume_scale.add_mark(50.0, Gtk.PositionType.LEFT, None)
        self.volume_scale.add_mark(0.0, Gtk.PositionType.LEFT, None)

        self.volume_scale.connect('value-changed', self._on_volume_changed)
        volume_box.pack_start(self.volume_scale, True, True, 0)

        # Mute button
        self.mute_button = Gtk.Button(label=self._t('mute'))
        self.mute_button.connect('clicked', self._on_mute_toggle)
        volume_box.pack_start(self.mute_button, False, False, 4)

        return volume_box

    def _build_status_bar(self):
        """Build the bottom status bar.

        Returns:
            A Gtk.Box containing status and device information.
        """
        status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        status_bar.get_style_context().add_class('status-bar')
        status_bar.set_margin_start(12)
        status_bar.set_margin_end(12)
        status_bar.set_margin_top(4)
        status_bar.set_margin_bottom(4)

        # Status message
        self.status_label = Gtk.Label(label=self._t('disabled'))
        self.status_label.get_style_context().add_class('status-label')
        self.status_label.set_halign(Gtk.Align.START)
        status_bar.pack_start(self.status_label, False, False, 0)

        # Spacer
        spacer = Gtk.Box()
        status_bar.pack_start(spacer, True, True, 0)

        # Output device
        device_prefix = Gtk.Label(label=self._t('active_output') + ': ')
        device_prefix.get_style_context().add_class('subtitle-label')
        status_bar.pack_start(device_prefix, False, False, 0)
        self.device_prefix_label = device_prefix

        self.device_label = Gtk.Label(label=self._t('no_device'))
        self.device_label.get_style_context().add_class('device-label')
        self.device_label.set_halign(Gtk.Align.END)
        self.device_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.device_label.set_max_width_chars(40)
        status_bar.pack_start(self.device_label, False, False, 0)

        return status_bar

    def _populate_preset_combo(self):
        """Populate the preset combobox with built-in and custom presets."""
        self._updating_preset = True
        self.preset_combo.remove_all()

        # Add built-in presets
        for key in BUILTIN_PRESET_ORDER:
            display_name = self._t(key)
            self.preset_combo.append(key, display_name)

        # Add separator text if there are custom presets
        custom_presets = self.preset_manager.get_custom_presets()
        if custom_presets:
            self.preset_combo.append('__separator__', '--- ' + self._t('custom_preset') + ' ---')
            for preset in custom_presets:
                self.preset_combo.append(preset['key'], preset['name'])

        self._updating_preset = False

    def _on_band_changed(self, scale, band_index):
        """Handle a change in one of the 8 band sliders.

        Updates the dB label, gain indicator, and applies EQ if enabled.

        Args:
            scale: The Gtk.Scale that changed.
            band_index: Index of the band (0-7).
        """
        if self._updating_sliders:
            return

        value = scale.get_value()
        self.band_labels[band_index].set_text(f'{value:+.1f} dB')
        self.gain_indicators[band_index].set_gain(value)

        # Update backend gains
        gains = [s.get_value() for s in self.band_scales]

        if self.backend.enabled:
            # Apply asynchronously to avoid UI freezing
            self.backend.apply_eq_async(
                gains=gains,
                callback=lambda ok, msg: GLib.idle_add(self._on_eq_applied, ok, msg)
            )

    def _on_preset_changed(self, combo):
        """Handle preset selection change.

        Loads the selected preset's gain values into the sliders.

        Args:
            combo: The Gtk.ComboBoxText that changed.
        """
        if self._updating_preset:
            return

        active_id = combo.get_active_id()
        if not active_id or active_id == '__separator__':
            return

        preset = self.preset_manager.get_preset(active_id)
        if not preset:
            return

        # Update delete button sensitivity
        self.delete_button.set_sensitive(not preset.get('builtin', True))

        # Apply preset gains to sliders
        self._set_slider_values(preset['gains'])

    def _set_slider_values(self, gains):
        """Set all 8 band sliders to the given gain values.

        Args:
            gains: List of 8 gain values in dB.
        """
        self._updating_sliders = True
        for i, gain in enumerate(gains):
            self.band_scales[i].set_value(float(gain))
            self.band_labels[i].set_text(f'{gain:+.1f} dB')
            self.gain_indicators[i].set_gain(float(gain))
        self._updating_sliders = False

        # Apply if EQ is enabled
        if self.backend.enabled:
            self.backend.apply_eq_async(
                gains=[float(g) for g in gains],
                callback=lambda ok, msg: GLib.idle_add(self._on_eq_applied, ok, msg)
            )

    def _on_toggle_eq(self, button):
        """Handle the enable/disable toggle button click.

        Args:
            button: The Gtk.Button that was clicked.
        """
        if self.backend.enabled:
            # Disable EQ
            success, message = self.backend.disable_eq()
            self._update_enable_button(False)
            self._set_status(self._t('eq_disabled'))
        else:
            # Enable EQ with current slider values
            gains = [s.get_value() for s in self.band_scales]
            self.backend.gains = gains
            success, message = self.backend.enable_eq()
            if success:
                self._update_enable_button(True)
                self._set_status(self._t('eq_applied'))
            else:
                self._update_enable_button(False)
                self._set_status(self._t(message) if message in TRANSLATIONS.get(self.language, {}) else message)

    def _update_enable_button(self, enabled):
        """Update the enable/disable button appearance.

        Args:
            enabled: True if the EQ is now enabled.
        """
        ctx = self.enable_button.get_style_context()
        if enabled:
            self.enable_button.set_label(self._t('enabled'))
            ctx.remove_class('toggle-disabled')
            ctx.add_class('toggle-enabled')
        else:
            self.enable_button.set_label(self._t('enable'))
            ctx.remove_class('toggle-enabled')
            ctx.add_class('toggle-disabled')

    def _on_save_preset(self, button):
        """Handle the save preset button click.

        Opens a dialog to get a name for the new preset and saves
        the current slider values.

        Args:
            button: The Gtk.Button that was clicked.
        """
        dialog = Gtk.Dialog(
            title=self._t('save_preset'),
            parent=self.window,
            flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
        )
        dialog.add_button(self._t('cancel'), Gtk.ResponseType.CANCEL)
        dialog.add_button(self._t('save'), Gtk.ResponseType.OK)

        content = dialog.get_content_area()
        content.set_margin_start(16)
        content.set_margin_end(16)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_spacing(8)

        label = Gtk.Label(label=self._t('preset_name') + ':')
        label.set_halign(Gtk.Align.START)
        content.pack_start(label, False, False, 0)

        entry = Gtk.Entry()
        entry.set_placeholder_text(self._t('custom_preset'))
        entry.set_activates_default(True)
        content.pack_start(entry, False, False, 0)

        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.show_all()

        response = dialog.run()
        preset_name = entry.get_text().strip()
        dialog.destroy()

        if response == Gtk.ResponseType.OK and preset_name:
            # Check if preset already exists
            if self.preset_manager.preset_exists(preset_name):
                # Ask to overwrite
                confirm = self._show_confirm_dialog(
                    self._t('preset_exists'),
                    f'{self._t("save")}?'
                )
                if not confirm:
                    return

            gains = [s.get_value() for s in self.band_scales]
            success, message, key = self.preset_manager.save_custom_preset(
                preset_name, gains
            )

            if success:
                self._populate_preset_combo()
                # Select the newly saved preset
                self.preset_combo.set_active_id(key)
                self._set_status(self._t('preset_saved'))
            else:
                self._set_status(self._t(message) if message in TRANSLATIONS.get(self.language, {}) else message)

    def _on_delete_preset(self, button):
        """Handle the delete preset button click.

        Deletes the currently selected custom preset after confirmation.

        Args:
            button: The Gtk.Button that was clicked.
        """
        active_id = self.preset_combo.get_active_id()
        if not active_id or self.preset_manager.is_builtin(active_id):
            return

        preset = self.preset_manager.get_preset(active_id)
        if not preset:
            return

        # Confirm deletion
        confirm = self._show_confirm_dialog(
            self._t('delete_preset'),
            f'"{preset["name"]}"?'
        )
        if not confirm:
            return

        success, message = self.preset_manager.delete_custom_preset(active_id)
        if success:
            self._populate_preset_combo()
            self.preset_combo.set_active(0)  # Reset to Flat
            self._set_status(self._t('preset_deleted'))
        else:
            self._set_status(self._t(message) if message in TRANSLATIONS.get(self.language, {}) else message)

    def _on_reset(self, button):
        """Handle the reset button click. Resets all bands to 0 dB.

        Args:
            button: The Gtk.Button that was clicked.
        """
        flat_gains = self.preset_manager.get_flat_gains()
        self._set_slider_values(flat_gains)
        self._updating_preset = True
        self.preset_combo.set_active(0)  # Select "Flat"
        self._updating_preset = False
        self.delete_button.set_sensitive(False)

    def _on_volume_changed(self, scale):
        """Handle master volume slider change.

        Args:
            scale: The Gtk.Scale that changed.
        """
        value = scale.get_value()
        self.volume_label.set_text(f'{value:.0f}%')

        # Apply volume in background thread
        volume_float = value / 100.0
        threading.Thread(
            target=self.backend.set_volume,
            args=(volume_float,),
            daemon=True,
        ).start()

    def _on_mute_toggle(self, button):
        """Handle mute button click.

        Args:
            button: The Gtk.Button that was clicked.
        """
        def _toggle():
            muted = self.backend.toggle_mute()
            GLib.idle_add(self._update_mute_button, muted)

        threading.Thread(target=_toggle, daemon=True).start()

    def _update_mute_button(self, muted):
        """Update the mute button label based on mute state.

        Args:
            muted: True if currently muted.
        """
        if muted:
            self.mute_button.set_label(self._t('unmute'))
            self.mute_button.get_style_context().add_class('danger-button')
        else:
            self.mute_button.set_label(self._t('mute'))
            self.mute_button.get_style_context().remove_class('danger-button')

    def _refresh_device_info(self):
        """Refresh the displayed audio output device information."""
        def _detect():
            device_name = self.backend.refresh_output_device()
            GLib.idle_add(self._update_device_label, device_name)

        threading.Thread(target=_detect, daemon=True).start()

    def _update_device_label(self, device_name):
        """Update the device label on the UI thread.

        Args:
            device_name: The device name string to display.
        """
        if device_name:
            self.device_label.set_text(device_name)
        else:
            self.device_label.set_text(self._t('no_device'))

    def _refresh_volume(self):
        """Refresh the displayed master volume level."""
        def _get_vol():
            volume, muted = self.backend.get_volume()
            GLib.idle_add(self._update_volume_display, volume, muted)

        threading.Thread(target=_get_vol, daemon=True).start()

    def _update_volume_display(self, volume, muted):
        """Update volume slider and mute button on the UI thread.

        Args:
            volume: Volume level 0.0 to 1.5.
            muted: Whether the output is muted.
        """
        pct = volume * 100.0
        self.volume_scale.set_value(pct)
        self.volume_label.set_text(f'{pct:.0f}%')
        self._update_mute_button(muted)

    def _on_eq_applied(self, success, message):
        """Callback for async EQ application. Updates status label.

        Args:
            success: Whether the operation succeeded.
            message: Status message key or string.
        """
        translated = self._t(message)
        self._set_status(translated)

    def _set_status(self, text):
        """Set the status bar message.

        Args:
            text: The status message to display.
        """
        self.status_label.set_text(text)

    def _show_confirm_dialog(self, title, message):
        """Show a confirmation dialog.

        Args:
            title: Dialog title text.
            message: Dialog body message.

        Returns:
            True if the user clicked OK/Yes.
        """
        dialog = Gtk.MessageDialog(
            parent=self.window,
            flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=title,
        )
        dialog.format_secondary_text(message)
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.YES

    def _on_delete(self, window, event):
        """Handle window close (delete-event).

        Args:
            window: The Gtk.Window.
            event: The Gdk.Event.

        Returns:
            False to allow the window to close.
        """
        self.backend.cleanup()
        return False

    def _on_destroy(self, window):
        """Handle window destruction.

        Args:
            window: The Gtk.Window being destroyed.
        """
        Gtk.main_quit()
