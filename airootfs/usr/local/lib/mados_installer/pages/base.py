"""
madOS Installer - Shared page UI helpers
"""

from gi.repository import Gtk

from ..config import NORD_POLAR_NIGHT, NORD_SNOW_STORM, NORD_FROST, NORD_AURORA


def create_page_header(title, step_num, total_steps=7):
    """Create consistent page header with step indicator dots"""
    header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    header.get_style_context().add_class("page-header")

    # Step indicator dots
    steps_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
    steps_box.set_halign(Gtk.Align.CENTER)
    steps_box.set_margin_bottom(8)
    steps_box.set_margin_top(2)

    for i in range(1, total_steps + 1):
        dot = Gtk.Label()
        if i == step_num:
            dot.set_markup(
                f'<span foreground="{NORD_FROST["nord8"]}" size="9000" weight="bold"> ● </span>'
            )
        elif i < step_num:
            dot.set_markup(
                f'<span foreground="{NORD_AURORA["nord14"]}" size="9000"> ● </span>'
            )
        else:
            dot.set_markup(
                f'<span foreground="{NORD_POLAR_NIGHT["nord3"]}" size="9000"> ● </span>'
            )
        steps_box.pack_start(dot, False, False, 0)

        if i < total_steps:
            line = Gtk.Label()
            if i < step_num:
                line.set_markup(
                    f'<span foreground="{NORD_AURORA["nord14"]}"> ── </span>'
                )
            else:
                line.set_markup(
                    f'<span foreground="{NORD_POLAR_NIGHT["nord3"]}"> ── </span>'
                )
            steps_box.pack_start(line, False, False, 0)

    header.pack_start(steps_box, False, False, 0)

    # Title
    title_label = Gtk.Label()
    title_label.set_markup(
        f'<span size="14000" weight="bold" foreground="{NORD_SNOW_STORM["nord6"]}">{title}</span>'
    )
    title_label.set_halign(Gtk.Align.CENTER)
    header.pack_start(title_label, False, False, 0)

    # Divider
    divider = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
    divider.get_style_context().add_class("page-divider")
    divider.set_margin_start(40)
    divider.set_margin_end(40)
    divider.set_margin_top(6)
    header.pack_start(divider, False, False, 0)

    return header


def create_nav_buttons(
    app, back_callback, next_callback, next_label=None, next_class="success-button"
):
    """Create consistent navigation buttons (Back + Next)"""
    btn_box = Gtk.Box(spacing=12)
    btn_box.set_halign(Gtk.Align.END)
    btn_box.set_margin_top(10)

    back_btn = Gtk.Button(label=app.t("back"))
    back_btn.get_style_context().add_class("nav-back-button")
    back_btn.connect("clicked", back_callback)
    btn_box.pack_start(back_btn, False, False, 0)

    next_btn = Gtk.Button(label=next_label or app.t("next"))
    next_btn.get_style_context().add_class(next_class)
    next_btn.connect("clicked", next_callback)
    btn_box.pack_start(next_btn, False, False, 0)

    return btn_box
