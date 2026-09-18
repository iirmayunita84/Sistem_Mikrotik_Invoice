# settings_window.py
import tkinter as tk
from tkinter import simpledialog

def open_settings_window(parent):
    win = tk.Toplevel(parent)
    win.title("Settings")
    win.geometry("300x200")
    tk.Label(win, text="Ini adalah jendela setting").pack(pady=20)
    tk.Button(win, text="Tutup", command=win.destroy).pack(pady=10)