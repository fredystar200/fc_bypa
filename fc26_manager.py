#!/usr/bin/env python3
"""
fc26_manager.py

Simple GUI to perform the three tasks described by the user:
1) Install "not a crack" into fc26 (handle renames & copy)
2) Delete listed files & FAKE folder then restore original exe
3) Launch EDTD.exe (expected in same directory as this script)

Test on Windows. Requires Python 3.8+ (works on 3.7).
"""
import os
import shutil
import subprocess
import threading
import traceback
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# Files to delete (as requested)
DELETE_FILES = [
    "anadius.cfg",
    "anadius64.dll",
    "anadius.cfg.bak",
    "EAAntiCheat.GameServiceLauncher.exe",
    "FC26.exe",
    "FC26Plugin.Launcher.FMT.Javelin.dll",
    "origin_helper_tools.html",
]
FAKE_DIR_NAME = "FAKE"

# Candidate names in "not a crack" folder (try these in order)
CANDIDATE_EXES = ["FC26_Showcase fixed.exe", "FC26 fixed.exe"]


class FC26ManagerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FC26 GUI Showcase Bypass")
        self.geometry("760x520")
        self.resizable(False, False)

        # Variables
        self.not_a_crack_path = tk.StringVar()
        self.fc26_path = tk.StringVar()
        self.script_dir = Path(__file__).parent.resolve()

        # Build UI
        self._build_ui()

    def _build_ui(self):
        frm = ttk.Frame(self, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        # Folder selection
        row = 0
        ttk.Label(frm, text="1) Select 'not a crack' folder:").grid(row=row, column=0, sticky=tk.W)
        ttk.Entry(frm, textvariable=self.not_a_crack_path, width=72).grid(row=row, column=1, padx=6)
        ttk.Button(frm, text="Browse", command=self.browse_not_a_crack).grid(row=row, column=2)
        row += 1

        ttk.Label(frm, text="2) Select 'fc26' folder:").grid(row=row, column=0, sticky=tk.W)
        ttk.Entry(frm, textvariable=self.fc26_path, width=72).grid(row=row, column=1, padx=6)
        ttk.Button(frm, text="Browse", command=self.browse_fc26).grid(row=row, column=2)
        row += 1

        # Buttons: Install, Delete, Launch
        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=row, column=0, columnspan=3, pady=(10, 6), sticky=tk.W)
        ttk.Button(btn_frame, text="Install (apply not a crack → fc26)", command=self.confirm_install).grid(row=0, column=0, padx=6)
        ttk.Button(btn_frame, text="Delete not a crack", command=self.confirm_delete).grid(row=0, column=1, padx=6)
        ttk.Button(btn_frame, text="EA Denuvo Token Dumper (by RMC-4)", command=self.launch_edtd).grid(row=0, column=2, padx=6)
        ttk.Button(btn_frame, text="Open script folder", command=self.open_script_dir).grid(row=0, column=3, padx=6)

        # Progress bar
        row += 1
        self.progress = ttk.Progressbar(frm, mode="determinate", maximum=100)
        self.progress.grid(row=row, column=0, columnspan=3, sticky="we", pady=(10, 4))
        row += 1

        # Log / status text area
        ttk.Label(frm, text="Log / Status:").grid(row=row, column=0, sticky=tk.W)
        row += 1
        self.log_text = scrolledtext.ScrolledText(frm, height=18, width=90, wrap=tk.WORD)
        self.log_text.grid(row=row, column=0, columnspan=3, pady=(4, 0))
        self.log("Let's goooo. Script directory: {}".format(self.script_dir))

    # ----------------------
    # UI helper methods
    # ----------------------
    def browse_not_a_crack(self):
        p = filedialog.askdirectory(title="Select 'not a crack' folder")
        if p:
            self.not_a_crack_path.set(p)

    def browse_fc26(self):
        p = filedialog.askdirectory(title="Select 'fc26' folder")
        if p:
            self.fc26_path.set(p)

    def log(self, *args):
        self.log_text.insert(tk.END, " ".join(str(a) for a in args) + "\n")
        self.log_text.see(tk.END)

    def set_progress(self, value):
        self.progress['value'] = value
        self.update_idletasks()

    def open_script_dir(self):
        try:
            if os.name == 'nt':
                subprocess.Popen(['explorer', str(self.script_dir)])
            else:
                subprocess.Popen(['xdg-open', str(self.script_dir)])
        except Exception as e:
            self.log("Failed to open script folder:", e)

    # ----------------------
    # Confirmation wrappers
    # ----------------------
    def confirm_install(self):
        if not self.not_a_crack_path.get() or not self.fc26_path.get():
            messagebox.showwarning("Missing folders", "Please select both folders first.")
            return
        if not messagebox.askyesno("Confirm install", 
                                   "This will rename and copy files from 'not a crack' into 'fc26' and may overwrite files in the fc26 folder. Proceed?"):
            return
        threading.Thread(target=self.install_flow, daemon=True).start()

    def confirm_delete(self):
        if not self.fc26_path.get():
            messagebox.showwarning("Missing folder", "Please select the 'fc26' folder first.")
            return
        if not messagebox.askyesno("Confirm delete", 
                                   "This will delete specific files from the fc26 folder and restore FC26_org.exe -> FC26.exe. Proceed?"):
            return
        threading.Thread(target=self.delete_flow, daemon=True).start()

    # ----------------------
    # Core flows
    # ----------------------
    def install_flow(self):
        try:
            self.set_progress(0)
            not_a_crack = Path(self.not_a_crack_path.get())
            fc26 = Path(self.fc26_path.get())

            self.log("Starting install from:", not_a_crack, "to:", fc26)

            # Validate folders
            if not not_a_crack.exists() or not not_a_crack.is_dir():
                messagebox.showerror("Error", f"'not a crack' folder does not exist: {not_a_crack}")
                return
            if not fc26.exists() or not fc26.is_dir():
                messagebox.showerror("Error", f"'fc26' folder does not exist: {fc26}")
                return

            # Find candidate exe in not_a_crack
            candidate = None
            for name in CANDIDATE_EXES:
                p = not_a_crack / name
                if p.exists():
                    candidate = p
                    break

            if candidate is None:
                messagebox.showerror("Error", f"None of the candidate EXE files were found in {not_a_crack}. Looked for: {CANDIDATE_EXES}")
                return

            self.log("Found candidate exe in 'not a crack':", candidate.name)
            self.set_progress(10)

            # Rename candidate -> FC26.exe inside not_a_crack
            fc26_exe_in_not = not_a_crack / "FC26.exe"
            if fc26_exe_in_not.exists():
                # make a backup of existing FC26.exe in not_a_crack (avoid overwrite surprise)
                backup = not_a_crack / "FC26.exe.bak"
                self.log("Existing FC26.exe in not_a_crack found; creating backup:", backup.name)
                shutil.move(str(fc26_exe_in_not), str(backup))
            self.log(f"Renaming {candidate.name} -> FC26.exe inside not_a_crack")
            candidate.rename(fc26_exe_in_not)
            self.set_progress(25)

            # In fc26: if FC26.exe exists, rename to FC26_org.exe (backup of original)
            fc26_exe = fc26 / "FC26.exe"
            fc26_org = fc26 / "FC26_org.exe"
            if fc26_exe.exists():
                # if FC26_org.exe already exists, create incremented backup to avoid loss
                if fc26_org.exists():
                    i = 1
                    while (fc26.parent / f"FC26_org_{i}.exe").exists():
                        i += 1
                    new_backup = fc26.parent / f"FC26_org_{i}.exe"
                    self.log("FC26_org.exe already exists; moving existing FC26_org.exe ->", new_backup.name)
                    shutil.move(str(fc26_org), str(new_backup))
                self.log("Renaming existing fc26/FC26.exe -> FC26_org.exe")
                shutil.move(str(fc26_exe), str(fc26_org))
            else:
                self.log("No FC26.exe present in fc26 folder; continuing.")

            self.set_progress(45)

            # Copy all files from not_a_crack into fc26 (overwrite)
            self.log("Copying files from 'not a crack' into fc26 (this will overwrite existing files).")
            files = list(not_a_crack.iterdir())
            total = max(len(files), 1)
            done = 0
            for item in files:
                dest = fc26 / item.name
                # If item is directory, copytree (overwrite by removing existing)
                if item.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(item, dest)
                    self.log("Copied folder:", item.name)
                else:
                    shutil.copy2(item, dest)
                    self.log("Copied file:", item.name)
                done += 1
                self.set_progress(45 + int(45 * done / total))

            self.set_progress(95)
            self.log("Install flow complete. Finalizing...")

            messagebox.showinfo("Install complete", "Install operation completed successfully.")
            self.set_progress(100)
        except Exception as e:
            self.log("Error in install_flow:", e)
            self.log(traceback.format_exc())
            messagebox.showerror("Error", f"An error occurred: {e}")
            self.set_progress(0)

    def delete_flow(self):
        try:
            self.set_progress(0)
            fc26 = Path(self.fc26_path.get())
            self.log("Starting delete flow in:", fc26)

            if not fc26.exists() or not fc26.is_dir():
                messagebox.showerror("Error", f"fc26 folder does not exist: {fc26}")
                return

            # Delete listed files
            total = len(DELETE_FILES) + 2
            done = 0
            for f in DELETE_FILES:
                p = fc26 / f
                if p.exists():
                    try:
                        if p.is_file() or p.is_symlink():
                            p.unlink()
                            self.log("Deleted:", p.name)
                        elif p.is_dir():
                            shutil.rmtree(p)
                            self.log("Deleted directory (unexpectedly named like file):", p.name)
                    except Exception as e:
                        self.log("Failed to delete", p.name, ":", e)
                else:
                    self.log("Not present (skipping):", p.name)
                done += 1
                self.set_progress(int(80 * done / total))

            # Delete FAKE folder if exists
            fake = fc26 / FAKE_DIR_NAME
            if fake.exists() and fake.is_dir():
                try:
                    shutil.rmtree(fake)
                    self.log("Deleted FAKE folder.")
                except Exception as e:
                    self.log("Failed to delete FAKE folder:", e)
            else:
                self.log("No FAKE folder found.")

            done += 1
            self.set_progress(int(80 * done / total))

            # Rename FC26_org.exe back to FC26.exe if present
            fc26_org = fc26 / "FC26_org.exe"
            fc26_exe = fc26 / "FC26.exe"
            if fc26_org.exists():
                if fc26_exe.exists():
                    # remove existing FC26.exe before restore
                    try:
                        fc26_exe.unlink()
                        self.log("Removed leftover FC26.exe to restore original.")
                    except Exception as e:
                        self.log("Could not remove existing FC26.exe:", e)
                shutil.move(str(fc26_org), str(fc26_exe))
                self.log("Restored:", fc26_exe.name)
            else:
                self.log("No FC26_org.exe found to restore.")

            done += 1
            self.set_progress(100)
            self.log("Delete flow complete.")
            messagebox.showinfo("Delete complete", "Delete operation finished.")
        except Exception as e:
            self.log("Error in delete_flow:", e)
            self.log(traceback.format_exc())
            messagebox.showerror("Error", f"An error occurred: {e}")
            self.set_progress(0)

    # ----------------------
    # Launch EDTD
    # ----------------------
    def launch_edtd(self):
        # EDTD.exe expected in same folder as this script
        edt_path = self.script_dir / "EDTD.exe"
        if not edt_path.exists():
            messagebox.showerror("Missing EDTD.exe", f"EDTD.exe not found in script folder:\n{edt_path}")
            return
        try:
            # Launch edt as a separate process without blocking the GUI
            subprocess.Popen([str(edt_path)], cwd=str(self.script_dir))
            self.log("Launched EDTD.exe:", edt_path)
        except Exception as e:
            self.log("Failed to launch EDTD.exe:", e)
            messagebox.showerror("Launch failed", f"Failed to launch EDTD.exe: {e}")


if __name__ == "__main__":
    app = FC26ManagerApp()
    app.mainloop()
