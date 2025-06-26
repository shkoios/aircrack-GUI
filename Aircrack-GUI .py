import tkinter as tk
from tkinter import ttk
import subprocess
import threading
import signal
import csv
import os
import time

# === COLORS ===
bg_color = "#1e1e1e"
fg_color = "#ffffff"
btn_bg = "#2e2e2e"
btn_hover = "#3e3e3e"

# === MAIN WINDOW ===
root = tk.Tk()
root.title("Aircrack-ng GUI BY ./SHKO")
root.geometry("900x700")
root.configure(bg=bg_color)

style = ttk.Style()
style.theme_use("default")
style.configure("TNotebook", background=bg_color)
style.configure("TNotebook.Tab", background=btn_bg, foreground=fg_color, padding=10)
style.map("TNotebook.Tab", background=[("selected", btn_hover)])
style.configure("TFrame", background=bg_color)

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True)

# === TABS ===
tab_iwconfig = ttk.Frame(notebook)
tab_airodump = ttk.Frame(notebook)
tab_aireplay = ttk.Frame(notebook)
tab_aircrack = ttk.Frame(notebook)

notebook.add(tab_iwconfig, text="Interfaces (iwconfig)")
notebook.add(tab_airodump, text="Airodump-ng")
notebook.add(tab_aireplay, text="Aireplay-ng")
notebook.add(tab_aircrack, text="Aircrack-ng")

# === TAB 1: iwconfig ===
text_iwconfig = tk.Text(tab_iwconfig, height=15, bg=btn_bg, fg=fg_color,
                       insertbackground=fg_color, relief="flat", font=("Consolas", 11))
text_iwconfig.pack(fill="both", expand=True)

def show_iwconfig():
    text_iwconfig.delete(1.0, tk.END)
    output = subprocess.getoutput("iwconfig")
    text_iwconfig.insert(tk.END, output)

show_btn = tk.Button(tab_iwconfig, text="Show Interfaces", command=show_iwconfig, bg=btn_hover, fg=fg_color)
show_btn.pack(pady=5)

# === START/STOP MONITOR MODE ===
def start_monitor():
    iface = interface_var.get()
    if iface:
        result = subprocess.getoutput(f"airmon-ng start {iface}")
        append_to_console(result)

def stop_monitor():
    iface = interface_var.get()
    if iface:
        result = subprocess.getoutput(f"airmon-ng stop {iface}")
        append_to_console(result)

start_btn = tk.Button(tab_iwconfig, text="Start Monitor Mode", command=start_monitor, bg=btn_hover, fg=fg_color)
start_btn.pack(pady=5)

stop_btn = tk.Button(tab_iwconfig, text="Stop Monitor Mode", command=stop_monitor, bg=btn_hover, fg=fg_color)
stop_btn.pack(pady=5)

# === INTERFACE SELECTION ===
interface_var = tk.StringVar()
interface_menu = ttk.Combobox(tab_iwconfig, textvariable=interface_var, state="readonly")
interface_menu.pack(pady=5)

def update_interfaces():
    output = subprocess.getoutput("iwconfig")
    interfaces = []
    for line in output.splitlines():
        if "IEEE 802.11" in line:
            iface = line.split()[0]
            interfaces.append(iface)
    interface_menu['values'] = interfaces
    if interfaces:
        interface_menu.current(0)

refresh_btn = tk.Button(tab_iwconfig, text="Refresh Interfaces", command=update_interfaces, bg=btn_hover, fg=fg_color)
refresh_btn.pack(pady=5)

update_interfaces()

# === LIVE CONSOLE ===
console_frame = tk.Frame(tab_iwconfig, bg=bg_color)
console_frame.pack(fill="both", expand=True)

console_scrollbar = tk.Scrollbar(console_frame)
console_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

console_output = tk.Text(console_frame, wrap=tk.WORD, yscrollcommand=console_scrollbar.set, height=10,
                         bg="#121212", fg="#00FF00", font=("Consolas", 10), insertbackground=fg_color)
console_output.pack(fill="both", expand=True)
console_scrollbar.config(command=console_output.yview)

def append_to_console(text):
    console_output.insert(tk.END, text + "\n")
    console_output.see(tk.END)

# === TAB 2: Airodump-ng ===

CSV_FILE = "capture-01.csv"  # This is the default output filename by airodump-ng

columns = ("BSSID", "PWR", "Beacons", "Data", "CH", "MB", "ENC", "ESSID")

tree_airodump = ttk.Treeview(tab_airodump, columns=columns, show="headings")
for col in columns:
    tree_airodump.heading(col, text=col)
    tree_airodump.column(col, width=100, anchor="center")
tree_airodump.pack(fill="both", expand=True)

airodump_process = None
running = False
# Create right-click context menu
menu = tk.Menu(tab_airodump, tearoff=0)
def copy_row():
    selected = tree_airodump.selection()
    if not selected:
        return
    row_values = tree_airodump.item(selected[0])['values']
    # Convert list of values to a tab-separated string
    row_text = "\t".join(str(v) for v in row_values)
    root.clipboard_clear()
    root.clipboard_append(row_text)
    # Optional: show a brief message (e.g. console)
    append_to_console(f"Copied row: {row_text}")

menu.add_command(label="Copy", command=copy_row)

def show_context_menu(event):
    # Select the row under mouse
    row_id = tree_airodump.identify_row(event.y)
    if row_id:
        tree_airodump.selection_set(row_id)
        menu.post(event.x_root, event.y_root)

tree_airodump.bind("<Button-3>", show_context_menu)  # Right click on Windows/Linux
# On macOS right click might be <Control-Button-1> or <Button-2> sometimes,
# add more bindings if needed:
# tree_airodump.bind("<Control-Button-1>", show_context_menu)


def start_airodump():
    global airodump_process, running
    iface = interface_var.get()
    if not iface:
        append_to_console("Please select an interface first.")
        return
    if airodump_process is None or airodump_process.poll() is not None:
        # Remove old CSV if exists
        if os.path.exists(CSV_FILE):
            try:
                os.remove(CSV_FILE)
            except Exception as e:
                append_to_console(f"Error removing old CSV: {e}")

        cmd = [
            "sudo", "airodump-ng",
            "--write", "capture",
            "--write-interval", "1",
            "--output-format", "csv",
            iface
        ]

        airodump_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        running = True
        threading.Thread(target=update_table_loop, daemon=True).start()
        append_to_console(f"Airodump-ng started on {iface}")

def stop_airodump():
    global airodump_process, running
    if airodump_process and airodump_process.poll() is None:
        airodump_process.send_signal(signal.SIGINT)
        airodump_process.wait()
        airodump_process = None
    running = False
    append_to_console("Airodump-ng stopped.")

def update_table_loop():
    while running:
        update_table()
        time.sleep(1)

def update_table():
    if not os.path.exists(CSV_FILE) or os.path.getsize(CSV_FILE) < 100:
        return

    try:
        with open(CSV_FILE, newline='', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            rows = list(reader)
    except Exception:
        return

    for row in tree_airodump.get_children():
        tree_airodump.delete(row)

    ap_start = None
    ap_end = None
    for i, row in enumerate(rows):
        if row and row[0] == "BSSID":
            ap_start = i + 1
        elif ap_start and (not row or row[0] == ""):
            ap_end = i
            break
    if ap_start is None:
        return
    if ap_end is None:
        ap_end = len(rows)

    ap_rows = rows[ap_start:ap_end]

    for r in ap_rows:
        if len(r) < 14:
            continue
        bssid = r[0]
        ch = r[3]
        mb = r[4]
        enc = f"{r[5]}/{r[6]}/{r[7]}"  # Privacy/Cipher/Auth
        pwr = r[8]
        beacons = r[9]
        data = r[10]
        essid = r[13]
        tree_airodump.insert("", "end", values=(bssid, pwr, beacons, data, ch, mb, enc, essid))


start_airodump_btn = tk.Button(tab_airodump, text="Start Airodump-ng", command=start_airodump, bg=btn_hover, fg=fg_color)
start_airodump_btn.pack(pady=5)

stop_airodump_btn = tk.Button(tab_airodump, text="Stop Airodump-ng", command=stop_airodump, bg=btn_hover, fg=fg_color)
stop_airodump_btn.pack(pady=5)

# === START MAIN ===
root.mainloop()
