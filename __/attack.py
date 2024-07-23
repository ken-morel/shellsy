import yaml

import time

from PIL import ImageTk
from pyoload import *
from threading import Lock
from threading import Thread
from ttkbootstrap import *
from ttkbootstrap.icons import *
from ttkbootstrap.tooltip import *
from ttkbootstrap.utility import *

DEFAULT_ICON_WIN32 = "\ue154"
DEFAULT_ICON = "\u25f0"


class Notification:
    MARGIN = 10
    _STACK = []
    WIDTH = 350
    IMAGE_WIDTH = 100
    rearange_lock = Lock()

    def __init__(
        self,
        title,
        message,
        duration=None,
        bootstyle="dark",
        alert=False,
        icon=None,
    ):
        self.message = message
        self.title = title
        self.duration = duration
        self.bootstyle = bootstyle

        if isinstance(icon, str):
            image = Image.open(icon)
            w, h = image.size
            sc = Notification.IMAGE_WIDTH / w
            icon = ImageTk.PhotoImage(image.resize((int(w * sc), int(h * sc))))
        else:
            try:
                sc = Notification.IMAGE_WIDTH / icon.width()
                icon.config(
                    width=int(sc * icon.width()),
                    height=int(sc * icon.height()),
                )
            except Exception:
                pass
        self.icon = icon
        self.titlefont = None

    def show(self):
        self.root = window = Toplevel(overrideredirect=True, alpha=0.7)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(0, weight=1)
        window.attributes("-topmost", 1)

        root = ttk.Frame(window, bootstyle=self.bootstyle)
        root.grid(column=0, row=0, sticky="nsew")

        if self.icon is not None:
            ttk.Label(
                root,
                image=self.icon,
                compound="image",
                bootstyle=f"{self.bootstyle}-inverse",
                anchor=NW,
            ).grid(row=0, column=0, rowspan=2, sticky=NSEW, padx=(5, 0))

        ttk.Label(
            root,
            text=self.title,
            font="{20px arial}",
            bootstyle=f"{self.bootstyle}-inverse",
            anchor=NW,
        ).grid(row=0, column=1, sticky=NSEW, padx=10, pady=(5, 0))

        ttk.Label(
            root,
            text=self.message,
            wraplength=scale_size(root, Notification.WIDTH - 130),
            bootstyle=f"{self.bootstyle}-inverse",
            anchor=NW,
        ).grid(row=1, column=1, sticky=NSEW, padx=10, pady=(0, 5))

        window.bind("<ButtonPress>", self.hide)
        Notification.add(self)
        window.bell()

        if self.duration is not None:
            window.after(self.duration, self.hide)

    def hide(self, *_):
        """Destroy and close the toast window."""
        Notification.remove(self)

    def _hide(self):
        alpha = float(self.root.attributes("-alpha"))
        if alpha <= 0.1:
            self.root.destroy()
            Notification.position_widgets()
        else:
            self.root.attributes("-alpha", alpha - 0.1)
            self.root.after(25, self._hide)

    @classmethod
    def add(cls, notification):
        marg = Notification.MARGIN
        width = Notification.WIDTH
        notification.root.update_idletasks()

        height = notification.root.winfo_height()
        screen_height = notification.root.winfo_screenheight()

        while True:
            taken = 0
            for notif in Notification._STACK:
                taken += marg + notif.root.winfo_height()

            if screen_height - (taken + marg) < height:
                Notification.remove_earliset()
                continue
            else:
                break
        cls._STACK.append(notification)
        notification.root.geometry(f"{width}x{height}-{marg}-{taken+marg}")

    @classmethod
    def remove_earliset(cls):
        cls.remove(cls._STACK[0])

    @classmethod
    def remove(cls, notification):
        notification._hide()
        if notification in cls._STACK:
            cls._STACK.pop(cls._STACK.index(notification))

    @classmethod
    def position_widgets(cls):
        marg = cls.MARGIN

        for idx, notification in enumerate(cls._STACK):
            taken = 0
            height = notification.root.winfo_height()
            for notif in cls._STACK[:idx]:
                taken += marg + notif.root.winfo_height()

            pos2 = taken + marg
            swidth = notification.root.winfo_screenheight()
            while (swidth - notification.root.winfo_y() - height) > pos2:
                for notif in cls._STACK[idx:]:
                    notif.root.geometry(
                        f"-{marg}+{notif.root.winfo_y() + 1}",
                    )
                    notif.root.update_idletasks()
                # time.sleep(0.005)
            notification.root.geometry(f"-{marg}-{pos2}")
            notification.root.update_idletasks()


class ToolTip:
    def __init__(
        self,
        widget,
        text,
        bootstyle=None,
        wraplength=None,
        delay=250,  # milliseconds
    ):
        self.widget = widget
        self.text = text
        self.bootstyle = bootstyle
        self.wraplength = wraplength or utility.scale_size(self.widget, 300)
        self.toplevel = None
        self.delay = delay
        self.id = None

        # event binding
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<Motion>", self.move_tip)
        self.widget.bind("<ButtonPress>", self.leave)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hide_tip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.delay, self.show_tip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def show_tip(self, *_):
        """Create a show the tooltip window"""
        if self.toplevel:
            return

        self.toplevel = ttk.Toplevel(
            overrideredirect=True, master=self.toplevel
        )
        lbl = ttk.Label(
            master=self.toplevel,
            text=self.text,
            justify=LEFT,
            wraplength=self.wraplength,
            padding=10,
            bootstyle="info",
        )
        lbl.pack(fill=BOTH, expand=YES)
        self.move_tip()
        if self.bootstyle:
            lbl.configure(bootstyle=self.bootstyle)
        else:
            lbl.configure(style="tooltip.TLabel")

    def move_tip(self, *_):
        """Move the tooltip window to the current mouse position within the
        widget.
        """
        if self.toplevel:
            mx = self.widget.winfo_pointerx()
            my = self.widget.winfo_pointery()

            # self.toplevel.update_idletasks()
            w = self.toplevel.winfo_width()
            h = self.toplevel.winfo_height()
            sw = self.toplevel.winfo_screenwidth()
            sh = self.toplevel.winfo_screenheight()

            wx = mx
            wy = my

            if wx + w > sw:
                wx -= w
            if wy + h > sh:
                wy -= h
            self.toplevel.geometry(f"+{wx}+{wy}")

    def hide_tip(self, *_):
        """Destroy the tooltip window."""
        if self.toplevel:
            self.toplevel.destroy()
            self.toplevel = None


class Dictionary:
    def __init__(self, file):
        with open(file) as f:
            self.data = yaml.safe_load(f.read())

    def install(self):
        import builtins

        builtins._ = self

    def __call__(self, pattern):
        path = pattern.split(".")
        obj = self.data
        for x in path:
            obj = obj[x]
        return obj


SPLASH = None


def splash(file, text=""):
    global SPLASH
    try:
        import pyi_splash
    except ImportError:
        SPLASH = tk.Tk()
        # SPLASH.configure(overrideredirect=True)
        SPLASH.attributes("-topmost", 1)
        SPLASH.image = PhotoImage(file=file)
        SPLASH.label = Label(
            SPLASH, compound="bottom", image=SPLASH.image, text=text
        )
        SPLASH.label.grid(column=0, row=0)
        SPLASH.update_idletasks()
        sw, sh = SPLASH.winfo_screenwidth(), SPLASH.winfo_screenheight()
        w, h = SPLASH.winfo_width(), SPLASH.winfo_height()
        SPLASH.geometry(f"+{sw//2-w//2}+{sh//2-h//2}")
        SPLASH.update()
    else:
        pyi_splash.update_text(text)


def update_splash(text):
    try:
        import pyi_splash
    except ImportError:
        if SPLASH:
            SPLASH.label.text = text
            SPLASH.update()
    else:
        pyi_splash.update_text(text)


def close_splash():
    try:
        import pyi_splash
    except ImportError:
        if SPLASH:
            SPLASH.destroy()
    else:
        pyi_splash.close()
