import tkinter as tk
from tkinter import filedialog
# Create the window
filepath = ""
def open_browser():
    global filepath
    filepath = filedialog.askdirectory()
    if (filepath != ""):
        print("selected {}".format(filepath))
    else:
        print("no file selected")

window = tk.Tk()
# Create a label that asks for folder location
label = tk.Label(text="Enter a folder location:")
# add the label to the window
label.pack()
# Create a browse button to browse folders
button = tk.Button(text="Browse", command=open_browser())
label = tk.Label(text=f"Folder location:{filepath}")
# run

window.mainloop()