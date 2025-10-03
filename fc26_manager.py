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

# Candidate names in "not a crack" folder (case-insensitive detection)
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

        # Buttons
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

        # Log area
        ttk.Label(frm, text="Log / Status:").grid(row=row, column=0, sticky=tk.W)
        row += 1
        self.log_text = scrolledtext.ScrolledText(frm, height=18, width=90, wrap=tk.WORD)
        self.log_text.grid(row=row, column=0, columnspan=3, pady=(4, 0))
        self.log("Let's goooo. Script directory: {}".format(self.script_dir))

    # ----------------------
    # UI helpers
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
    # Confirmation
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
                                   "This will delete specific files from the fc26 folder and restore original exe. Proceed?"):
            return
        threading.Thread(target=self.delete_flow, daemon=True).start()

    # ----------------------
    # Helper for backing up both exe types in fc26 (on install)
    # ----------------------
    def backup_fc26_exes_if_present(self, fc26: Path):
        """
        If FC26.exe exists -> rename to FC26_org.exe (remove any existing _org first).
        If FC26_Showcase.exe exists -> rename to FC26_Showcase_org.exe.
        """
        try:
            # Normal exe
            normal = fc26 / "FC26.exe"
            normal_org = fc26 / "FC26_org.exe"
            if normal.exists():
                if normal_org.exists():
                    self.log("Removing existing", normal_org.name, "to allow backup.")
                    normal_org.unlink()
                self.log(f"Backing up {normal.name} -> {normal_org.name}")
                shutil.move(str(normal), str(normal_org))

            # Showcase exe
            showcase = fc26 / "FC26_Showcase.exe"
            showcase_org = fc26 / "FC26_Showcase_org.exe"
            if showcase.exists():
                if showcase_org.exists():
                    self.log("Removing existing", showcase_org.name, "to allow backup.")
                    showcase_org.unlink()
                self.log(f"Backing up {showcase.name} -> {showcase_org.name}")
                shutil.move(str(showcase), str(showcase_org))
        except Exception as e:
            self.log("Error during backup_fc26_exes_if_present:", e)
            raise

    # ----------------------
    # Core flows
    # ----------------------
    def install_flow(self):
        try:
            self.set_progress(0)
            not_a_crack = Path(self.not_a_crack_path.get())
            fc26 = Path(self.fc26_path.get())

            self.log("Starting install from:", not_a_crack, "to:", fc26)

            if not not_a_crack.exists() or not not_a_crack.is_dir():
                messagebox.showerror("Error", f"'not a crack' folder does not exist: {not_a_crack}")
                return
            if not fc26.exists() or not fc26.is_dir():
                messagebox.showerror("Error", f"'fc26' folder does not exist: {fc26}")
                return

            # Detect candidate exe (case-insensitive)
            candidate = None
            candidate_lower_name = None
            for name in CANDIDATE_EXES:
                p = not_a_crack / name
                if p.exists():
                    candidate = p
                    candidate_lower_name = name.lower()
                    break
                # also try a case-insensitive scan of directory
            if candidate is None:
                # fallback: scan folder for any file whose lower() matches our known patterns
                for p in not_a_crack.iterdir():
                    if p.is_file() and p.name.lower() in [s.lower() for s in CANDIDATE_EXES]:
                        candidate = p
                        candidate_lower_name = p.name.lower()
                        break

            if candidate is None:
                messagebox.showerror("Error", f"None of the candidate EXE files were found in {not_a_crack}.")
                return

            self.log("Found candidate exe in 'not a crack':", candidate.name)
            self.set_progress(10)

            # Determine target rename based on which candidate was found
            if "showcase" in candidate_lower_name:
                # Found FC26_Showcase fixed.exe
                new_name = "FC26_Showcase.exe"
                org_name = "FC26_Showcase_org.exe"
            else:
                # Found FC26 fixed.exe
                new_name = "FC26.exe"
                org_name = "FC26_org.exe"

            # Rename candidate inside not_a_crack to canonical new_name
            renamed_candidate = not_a_crack / new_name
            if renamed_candidate.exists():
                # keep a small .bak if present to avoid overwrite
                backup = not_a_crack / (new_name + ".bak")
                self.log(f"Existing {new_name} in not_a_crack found; creating backup {backup.name}")
                if backup.exists():
                    backup.unlink()
                shutil.move(str(renamed_candidate), str(backup))
            try:
                self.log(f"Renaming {candidate.name} -> {new_name} inside not_a_crack")
                candidate.rename(renamed_candidate)
            except Exception as e:
                self.log("Failed to rename candidate in not_a_crack:", e)
                raise

            self.set_progress(25)

            # In fc26: backup any existing FC26.exe and/or FC26_Showcase.exe as required by your spec
            self.backup_fc26_exes_if_present(fc26)
            self.set_progress(40)

            # Now copy all files from not_a_crack into fc26 (overwrite)
            self.log("Copying files from 'not a crack' into fc26 (overwrite).")
            files = list(not_a_crack.iterdir())
            total = max(len(files), 1)
            for i, item in enumerate(files, start=1):
                dest = fc26 / item.name
                try:
                    if item.is_dir():
                        # remove dest dir then copy
                        if dest.exists():
                            if dest.is_dir():
                                shutil.rmtree(dest)
                            else:
                                dest.unlink()
                        shutil.copytree(item, dest)
                    else:
                        # ensure dest parent exists
                        dest_parent = dest.parent
                        dest_parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dest)
                    self.log("Copied:", item.name)
                except Exception as e:
                    self.log("Failed to copy", item.name, ":", e)
                self.set_progress(40 + int(50 * i / total))

            self.set_progress(95)
            self.log("Install flow complete.")
            messagebox.showinfo("Install complete", "Install operation completed successfully.")
            self.set_progress(100)

        except Exception as e:
            self.log("Error in install_flow:", e)
            self.log(traceback.format_exc())
            messagebox.showerror("Error", f"An error occurred: {e}")
            self.set_progress(0)

    def delete_flow(self):
        """
        Delete the 'not a crack' files per DELETE_FILES & FAKE folder,
        then detect which *_org.exe files exist and restore them:

        - If FC26_org.exe exists: delete FC26.exe (if present) then rename FC26_org.exe -> FC26.exe
        - If FC26_Showcase_org.exe exists: delete FC26_Showcase.exe (if present) then rename FC26_Showcase_org.exe -> FC26_Showcase.exe

        If both *_org.exe exist, perform both restores.
        """
        try:
            self.set_progress(0)
            fc26 = Path(self.fc26_path.get())
            self.log("Starting delete flow in:", fc26)

            if not fc26.exists() or not fc26.is_dir():
                messagebox.showerror("Error", f"fc26 folder does not exist: {fc26}")
                return

            # Delete listed files
            for i, f in enumerate(DELETE_FILES, start=1):
                p = fc26 / f
                if p.exists():
                    try:
                        if p.is_file() or p.is_symlink():
                            p.unlink()
                        elif p.is_dir():
                            shutil.rmtree(p)
                        self.log("Deleted:", p.name)
                    except Exception as e:
                        self.log("Failed to delete", p.name, ":", e)
                self.set_progress(int(50 * i / len(DELETE_FILES)))

            # Delete FAKE folder
            fake = fc26 / FAKE_DIR_NAME
            if fake.exists():
                try:
                    shutil.rmtree(fake)
                    self.log("Deleted FAKE folder.")
                except Exception as e:
                    self.log("Failed to delete FAKE folder:", e)
            else:
                self.log("No FAKE folder found.")

            self.set_progress(65)

            # Restore logic: check both _org exe files and restore accordingly
            restored_any = False

            # 1) Restore normal exe if backup exists
            normal_org = fc26 / "FC26_org.exe"
            normal_exe = fc26 / "FC26.exe"
            if normal_org.exists():
                # delete current FC26.exe if present
                if normal_exe.exists():
                    try:
                        normal_exe.unlink()
                        self.log("Deleted current FC26.exe to allow restore from FC26_org.exe")
                    except Exception as e:
                        self.log("Failed to delete FC26.exe before restore:", e)
                # move backup -> original name
                try:
                    shutil.move(str(normal_org), str(normal_exe))
                    self.log("Restored FC26_org.exe -> FC26.exe")
                    restored_any = True
                except Exception as e:
                    self.log("Failed to restore FC26_org.exe -> FC26.exe:", e)

            # 2) Restore showcase exe if backup exists
            showcase_org = fc26 / "FC26_Showcase_org.exe"
            showcase_exe = fc26 / "FC26_Showcase.exe"
            if showcase_org.exists():
                # delete current FC26_Showcase.exe if present
                if showcase_exe.exists():
                    try:
                        showcase_exe.unlink()
                        self.log("Deleted current FC26_Showcase.exe to allow restore from FC26_Showcase_org.exe")
                    except Exception as e:
                        self.log("Failed to delete FC26_Showcase.exe before restore:", e)
                # move backup -> original name
                try:
                    shutil.move(str(showcase_org), str(showcase_exe))
                    self.log("Restored FC26_Showcase_org.exe -> FC26_Showcase.exe")
                    restored_any = True
                except Exception as e:
                    self.log("Failed to restore FC26_Showcase_org.exe -> FC26_Showcase.exe:", e)

            if not restored_any:
                self.log("No *_org.exe found to restore.")

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
        edt_path = self.script_dir / "EDTD.exe"
        if not edt_path.exists():
            messagebox.showerror("Missing EDTD.exe", f"EDTD.exe not found in script folder:\n{edt_path}")
            return
        try:
            subprocess.Popen([str(edt_path)], cwd=str(self.script_dir))
            self.log("Launched EDTD.exe:", edt_path)
        except Exception as e:
            self.log("Failed to launch EDTD.exe:", e)
            messagebox.showerror("Launch failed", f"Failed to launch EDTD.exe: {e}")


if __name__ == "__main__":
    app = FC26ManagerApp()
    app.mainloop()
