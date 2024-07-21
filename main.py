from attack import *
from pyoload import *
from shellsy import Shellsy
import pyttsx3

update_splash("loading language files")
Dictionary("dictionary/en.yaml").install()

OPEN = True
MOVING = False
SCHEDULE_ID = 0


update_splash("initializing...")


def enter(e):
    unschedule_collapse()
    expand()


def leave(e):
    schedule_collapse()


def enter_schedule(e):
    expand()
    schedule_collapse()


def schedule_collapse():
    global SCHEDULE_ID
    unschedule_collapse()
    SCHEDULE_ID = window.after(5000, collapse)


def unschedule_collapse():
    global SCHEDULE_ID
    try:
        window.after_cancel(SCHEDULE_ID)
    except ValueError:
        pass
    finally:
        SCHEDULE_ID = None


def collapse():
    global OPEN, MOVING
    if not OPEN or MOVING:
        return
    MOVING = True
    responsesTxt.grid_forget()
    for x in range(35, 300, 20):
        window.geometry(f"200x{325 - x}")
        window.update()
    MOVING = OPEN = False
    window.attributes("-alpha", 0.3)


def expand():
    global OPEN, MOVING
    if OPEN or MOVING:
        return
    MOVING = True
    responsesTxt.grid()
    for x in range(35, 300, 80):
        window.attributes("-alpha", (x - 35) / 300)
        window.geometry(f"200x{x}")
        window.update()
    window.attributes("-alpha", 1)
    OPEN = True
    MOVING = False


@annotate
def speak(text: str):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()


def respond(arg):
    text = queryInput.get()
    # responsesTxt.delete("1.0", "end")
    responsesTxt.insert("end", text + "\n", ("query",))
    try:
        response = shellsy.respond(text)
    except Exception as e:
        Notification(
            title="Shellsy error",
            message=str(e),
            icon=icon,
            bootstyle="danger",
            duration=5000,
        ).show()
    else:
        queryInput.delete("0", "end")
        for x in response.response:
            print("> ", x)
            responsesTxt.insert("end - 1c", x, ("response",))
            # window.update()
            # speak(x)
        responsesTxt.insert("end - 1c", "\n", ("response",))

close_splash()

window = Window(themename="vapor", overrideredirect=True, alpha=0.4)
icon = PhotoImage(file="icon.png")
window.geometry("200x300+20-20")
window.iconbitmap("icon.png")
window.bind("<Enter>", enter)
window.bind("<Key>", enter_schedule)
window.bind("<Leave>", leave)
window.attributes("-topmost", 1)
(root := Frame(window)).grid(column=0, row=0, sticky="nsew")
window.columnconfigure(0, weight=1)
window.rowconfigure(0, weight=1)
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

(responsesFrm := Frame(root)).grid(column=0, row=0, sticky="nsew")
(responsesTxt := Text(responsesFrm, width=31)).grid(
    column=0, row=0, sticky="nsew"
)
responsesTxt.tag_configure("response", background="#112", foreground="#fff")
responsesTxt.tag_configure("query", background="#211", foreground="#fff")

(queryFrm := Frame(root)).grid(column=0, row=1)
queryFrm.columnconfigure(0, weight=1)
queryFrm.rowconfigure(0, weight=1)
(
    queryInput := ToolTip(
        Entry(queryFrm, width=100),
        _("queryinput.tooltip"),
        bootstyle="dark",
    ).widget
).grid(column=0, row=0, sticky="nsew")


queryInput.bind("<Return>", respond)
queryInput.focus()

shellsy = Shellsy()

collapse()
window.mainloop()
