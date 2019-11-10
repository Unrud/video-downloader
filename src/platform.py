import os
import re
import tkinter as tk
import tkinter.font
from tkinter import ttk

from video_downloader import BASE_DPI


class Platform:
    def __init__(self, master, unused_fonts):
        assert len(unused_fonts) >= 2
        self.master = master
        self.custom_titlebar = False
        self._platform = []  # ["gnome", "nt", "x11"]
        self._xlib = None
        self._dpy = None
        if "GNOME" in os.environ.get("XDG_CURRENT_DESKTOP", "").split(":"):
            self._platform.append("gnome")
        if re.match(r"X\d+R\d+", self.master.winfo_server()):
            self._platform.append("x11")
        if os.name == "nt":
            self._platform.append("nt")
        if "x11" in self._platform:
            import Xlib
            import Xlib.display
            import Xlib.rdb
            from Xlib import Xatom, Xutil
            self._xlib, self._xatom, self._xutil = Xlib, Xatom, Xutil
            self._dpy = Xlib.display.Display()

        initial_scaling = self.master.tk.call("tk", "scaling")
        if "x11" in self._platform and "gnome" in self._platform:
            self.custom_titlebar = True
        if "x11" in self._platform:
            self._set_X_scaling()
        self._set_theme(unused_fonts, initial_scaling)

    def window_apply(self, w):
        if self.custom_titlebar and "x11" in self._platform:

            def on_visibility(event):
                w.unbind("<Visibility>", on_visibility_funcid)
                self._hide_X_titlebar(w)
            on_visibility_funcid = w.bind("<Visibility>", on_visibility)
        elif self.custom_titlebar and "nt" in self._platform:
            w.overrideredirect(1)

    def _hide_X_titlebar(self, w):
        """Call after window is visible."""
        Xlib = self._xlib
        window = self._dpy.create_resource_object("window", w.winfo_id())
        parent = window.query_tree().parent
        _MOTIF_WM_HINTS_STRUCT = Xlib.protocol.rq.Struct(
            Xlib.protocol.rq.Card32("flags"),
            Xlib.protocol.rq.Card32("functions", default=0),
            Xlib.protocol.rq.Card32("decorations", default=0),
            Xlib.protocol.rq.Int32("input_mode", default=0),
            Xlib.protocol.rq.Card32("status", default=0))
        _motif_wm_hints = self._dpy.intern_atom("_MOTIF_WM_HINTS", 1)
        if _motif_wm_hints == 0:
            raise RuntimeError("_MOTIF_WM_HINTS not found")
        parent.change_property(
            _motif_wm_hints, _motif_wm_hints, 32,
            _MOTIF_WM_HINTS_STRUCT.to_binary(flags=0x2, decorations=0x2))
        self._dpy.flush()

    def _set_X_scaling(self):
        Xlib, Xatom, Xutil = self._xlib, self._xatom, self._xutil
        rdbstring = self._dpy.screen().root.get_full_property(
            Xatom.RESOURCE_MANAGER, Xatom.STRING)
        rdbstring = rdbstring.value.decode() if rdbstring else None
        rdb = Xlib.rdb.ResourceDB(string=rdbstring)
        xdpi = float(rdb.get("Xft.dpi", "Xft.dpi", BASE_DPI))
        self.master.tk.call("tk", "scaling", xdpi / BASE_DPI)

    def _set_theme(self, unused_fonts, initial_scaling):
        def font_px_to_pt(v):
            """Convert font size in px to pt for correct scaling"""
            if v >= 0:
                # Unit is already pt
                return v
            # Font sizes in px are scaled by initial scaling value
            return round(abs(v) / initial_scaling)

        for name in ["TkDefaultFont", "TkTextFont", "TkFixedFont",
                     "TkMenuFont", "TkHeadingFont", "TkCaptionFont",
                     "TkSmallCaptionFont", "TkIconFont", "TkTooltipFont"]:
            font = tk.font.nametofont(name)
            font.config(size=font_px_to_pt(font.config()["size"]))
        default_font = tk.font.nametofont("TkDefaultFont")
        title_font = unused_fonts.pop()
        title_font.config(**default_font.config())
        title_font.config(weight="bold")
        icon_font = unused_fonts.pop()
        icon_font.config(**default_font.config())
        icon_font.config(size=icon_font.config()["size"] * 4)

        s = ttk.Style(self.master)
        s.theme_use("clam")
        s.configure("Title.TLabel", font=title_font)
        s.configure("Header.TFrame", background="#3f3f3f")
        s.configure("Header.Title.TLabel", background="#3f3f3f",
                    foreground="white")
        s.configure("Header.WindowButton.TButton", relief="flat",
                    background="#3f3f3f", foreground="#cbcbcb")
        s.map("Header.WindowButton.TButton",
              background=[("active", "#525252")])
        s.configure("Suggested.TButton", background="#2861ae",
                    foreground="white", darkcolor="#225394",
                    lightcolor="#2e6fc7", bordercolor="#163761")
        s.map("Suggested.TButton",
              background=[("pressed", "#1c457b"), ("active", "#4a90d9")],
              darkcolor=[("pressed", "#163661")],
              lightcolor=[("pressed", "#225394")])
        s.configure("Icon.TLabel", font=icon_font)
