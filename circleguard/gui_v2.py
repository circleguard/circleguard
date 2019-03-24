import tkinter
from tkinter import ttk, Tk, N, W, E, S, StringVar, TclError
from types import SimpleNamespace
import threading
from pathlib import Path

from circleguard import Circleguard
from config import VERSION
from secret import API_KEY

def run():
    """
    Runs the circleguard with the options given in the gui.
    """

    _map_id = map_id.get()
    _user_id = user_id.get()
    _local = local.get()
    _threshold = threshold.get()

    _stddevs = stddevs.get() if auto.get() else None

    _number = num.get()
    _cache = cache.get()
    _silent = True # Visualizations do very very bad things when not called from the main thread, so when using gui, we just...force ignore them
    _verify = verify.get()

    def run_circleguard():
        circleguard = Circleguard(SimpleNamespace(map_id=_map_id, user_id=_user_id, mods="", local=_local, threshold=_threshold, stddevs=_stddevs,
                                              number=_number, cache=_cache, silent=_silent, verify=_verify), API_KEY, Path(__file__).parent)
        circleguard.run()

    thread = threading.Thread(target=run_circleguard)
    thread.start()


# Root and Frames configuration
root = Tk()
root.title("Circleguard v{}".format(VERSION))
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)
# houses boolean inputs passed to circleguard
s = ttk.Style()
s.configure("TFrame", foreground="#ccc")

main = ttk.Frame(root)
main.grid(row=0, column=0)
# houses options - what type of search, whether to use local, etc.
options = ttk.Frame(root)
options.grid(row=0, column=2)
sep = ttk.Separator(root, orient="vertical")
sep.grid(row=0, column=1)

# Global vars
map_id = tkinter.StringVar()
user_id = tkinter.StringVar()
local = tkinter.BooleanVar(value=False)
threshold = tkinter.IntVar(value=20)
auto = tkinter.BooleanVar(value=False)
stddevs = tkinter.DoubleVar(value=2.0)
compare_to_map = tkinter.BooleanVar(value=False)
num = tkinter.IntVar(value=50)
cache = tkinter.BooleanVar(value=False)

# unimplemented
verify = tkinter.BooleanVar(value=False)

# Make visual elements for main frame
map_label = ttk.Label(main, text="Map id:")
map_label.grid(row=0, column=0)

map_entry = ttk.Entry(main, width=14, textvariable=map_id)
map_entry.grid(row=0, column=1)

user_label = ttk.Label(main, text="User id:")
user_label.grid(row=1, column=0)

user_entry = ttk.Entry(main, width=14, textvariable=user_id)
user_entry.grid(row=1, column=1)

run_button = ttk.Button(main, text="Run", command=run)
run_button.grid(row=2, column=1)

# Make visual elements for options frame
should_cache = ttk.Frame(options)
should_cache.grid(row=0, column=0)
cache_check = ttk.Checkbutton(should_cache, variable=cache)
cache_check.grid(row=0, column=0)
cache_label = ttk.Label(should_cache, text="Cache downloaded replays?")
cache_label.grid(row=0, column=1)

should_local_compare = ttk.Frame(options)
should_local_compare.grid(row=1, column=0)
local_compare_check = ttk.Checkbutton(should_local_compare, variable=local)
local_compare_check.grid(row=0, column=0)
local_compare_label = ttk.Label(should_local_compare, text="Compare to local replays?")
local_compare_label.grid(row=0, column=1)

top_x_plays = ttk.Frame(options)
top_x_plays.grid(row=2, column=0)
top_plays_check = ttk.Checkbutton(top_x_plays, variable=compare_to_map)
top_plays_check.grid(row=0, column=0)
top_plays_label1 = ttk.Label(top_x_plays, text="Compare to top")
top_plays_label1.grid(row=0, column=1)
top_plays_entry = ttk.Entry(top_x_plays, width=4, textvariable=num)
top_plays_entry.grid(row=0, column=2)
top_plays_label2 = ttk.Label(top_x_plays, text="leaderboard plays?\n(Between 2 and 100 inclusive)")
top_plays_label2.grid(row=0, column=3)

auto_threshold = ttk.Frame(options)
auto_threshold.grid(row=3, column=0)
auto_check = ttk.Checkbutton(auto_threshold, variable=auto)
auto_check.grid(row=0, column=0)
auto_label1 = ttk.Label(auto_threshold, text="Automatically determine threshold?")
auto_label1.grid(row=0, column=1)
auto_entry = ttk.Entry(auto_threshold, width=3, textvariable=stddevs)
auto_entry.grid(row=0, column=2)
auto_label2 = ttk.Label(auto_threshold, text="Stddevs below average threshold to print for\n(typically between 1.5 and 2.5. The higher, the less results you will get)")
auto_label2.grid(row=0, column=3)

for child in main.winfo_children(): child.grid_configure(padx=5, pady=5)

root.mainloop()
