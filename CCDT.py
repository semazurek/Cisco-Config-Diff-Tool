import sys
import subprocess
import os
import tempfile
import difflib

def clear_console():
    # os.name returns 'nt' for Windows and 'posix' for Linux/macOS
    os.system('cls' if os.name == 'nt' else 'clear')

# ---------------------------------------------------------
# 0. Bootstrapper / Auto-Installer for Dependencies
# ---------------------------------------------------------
def ensure_dependencies():
    """Checks for required Python and system-level modules, installing missing ones."""
    # 1. Try importing Tkinter. If missing on Linux, suggest/install via system package manager.
    try:
        import tkinter
    except ImportError:
        print("[!] Tkinter is missing. Attempting system installation...")
        if sys.platform.startswith("linux"):
            try:
                # Detect Linux distribution via /etc/os-release
                distro_id = ""
                if os.path.exists("/etc/os-release"):
                    with open("/etc/os-release") as f:
                        for line in f:
                            if line.startswith("ID="):
                                distro_id = line.strip().split("=")[1].replace('"', '')

                if distro_id in ["ubuntu", "debian", "linuxmint", "pop"]:
                    print("[*] Detected Debian/Ubuntu family. Installing python3-tk...")
                    subprocess.check_call(["sudo", "apt-get", "update"])
                    subprocess.check_call(["sudo", "apt-get", "install", "-y", "python3-tk"])
                elif distro_id in ["arch", "manjaro", "endeavouros"]:
                    print("[*] Detected Arch Linux family. Installing tk...")
                    subprocess.check_call(["sudo", "pacman", "-S", "--noconfirm", "tk"])
                else:
                    print(f"[!] Unsupported Linux distribution ({distro_id}). Please install Tkinter manually (e.g. python3-tk or tk).")
                    sys.exit(1)
            except Exception as e:
                print(f"[!] Failed to install Tkinter automatically: {e}")
                print("[!] Please install 'python3-tk' (Debian/Ubuntu) or 'tk' (Arch Linux) using your package manager.")
                sys.exit(1)
        elif sys.platform.startswith("win"):
            print("[!] Tkinter is not installed in your Python environment on Windows.")
            print("[!] Please modify your Python installation via Windows Installer and check 'tcl/tk and IDLE'.")
            sys.exit(1)

    # 2. Check and auto-install Python packages via pip (e.g. hier-config for conf_diff)
    REQUIRED_PIP_PACKAGES = {
        "conf_diff": "hier_config"  # module_name: pip_package_name
    }

    for module_name, pip_package in REQUIRED_PIP_PACKAGES.items():
        try:
            __import__(module_name)
        except ImportError:
            print(f"[*] Missing Python package '{module_name}'. Installing '{pip_package}' via pip...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pip_package])
            except subprocess.CalledProcessError:
                # Fallback for systems blocking global pip installs (PEP 668 - externally managed environments)
                print(f"[*] Retrying pip install with --break-system-packages / --user...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", pip_package])

# Execute dependency check before importing modules
ensure_dependencies()
clear_console()
# ---------------------------------------------------------
# 1. Imports
# ---------------------------------------------------------
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import conf_diff
except ImportError:
    conf_diff = None

# ---------------------------------------------------------
# 2. ANSI Helper Function for Console Output Styling
# ---------------------------------------------------------
def print_colored_diff(line):
    """Prints colored diff lines to the terminal using ANSI escape codes."""
    # Enable ANSI color support on Windows Command Prompt if applicable
    if sys.platform.startswith("win"):
        os.system("")

    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    RESET = "\033[0m"

    if line.startswith("---") or line.startswith("+++"):
        print(f"{RED if line.startswith('---') else GREEN}{line}{RESET}")
    elif line.startswith("-"):
        print(f"{RED}{line}{RESET}")
    elif line.startswith("+"):
        print(f"{GREEN}{line}{RESET}")
    elif line.startswith("@@"):
        print(f"{YELLOW}{line}{RESET}")
    elif line.startswith("***"):
        print(f"{CYAN}{line}{RESET}")
    else:
        print(line)

# ---------------------------------------------------------
# 3. Graphical User Interface (GUI)
# ---------------------------------------------------------
class NetCompareGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Cisco Config Diff Tool")
        self.root.geometry("900x550")
        self.root.minsize(600, 400)

        # Allow window grid rows and columns to expand dynamically
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=0)

        self._build_ui()

    def _build_ui(self):
        # Top Frame - Main Layout with Grid
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.grid(row=0, column=0, sticky="nsew")

        top_frame.columnconfigure(0, weight=1)
        top_frame.columnconfigure(1, weight=1)
        top_frame.rowconfigure(0, weight=1)

        # Left Panel: Old Config
        old_frame = ttk.LabelFrame(top_frame, text=" Old Configuration ", padding=5)
        old_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        old_frame.columnconfigure(0, weight=1)
        old_frame.rowconfigure(1, weight=1)

        old_btn_frame = ttk.Frame(old_frame)
        old_btn_frame.grid(row=0, column=0, sticky="ew", pady=2)
        old_btn_frame.columnconfigure(0, weight=0)
        old_btn_frame.columnconfigure(1, weight=1)

        ttk.Button(old_btn_frame, text="📁 Browse...", command=self._load_old_file).grid(row=0, column=0, sticky="w")
        self.lbl_old_status = ttk.Label(old_btn_frame, text="No file selected (paste text below)", font=("sans-serif", 8, "italic"))
        self.lbl_old_status.grid(row=0, column=1, sticky="e", padx=5)

        self.txt_old_input = self._create_scrollable_text(old_frame, row=1, column=0)

        # Right Panel: New Config
        new_frame = ttk.LabelFrame(top_frame, text=" New Configuration ", padding=5)
        new_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        new_frame.columnconfigure(0, weight=1)
        new_frame.rowconfigure(1, weight=1)

        new_btn_frame = ttk.Frame(new_frame)
        new_btn_frame.grid(row=0, column=0, sticky="ew", pady=2)
        new_btn_frame.columnconfigure(0, weight=0)
        new_btn_frame.columnconfigure(1, weight=1)

        ttk.Button(new_btn_frame, text="📁 Browse...", command=self._load_new_file).grid(row=0, column=0, sticky="w")
        self.lbl_new_status = ttk.Label(new_btn_frame, text="No file selected (paste text below)", font=("sans-serif", 8, "italic"))
        self.lbl_new_status.grid(row=0, column=1, sticky="e", padx=5)

        self.txt_new_input = self._create_scrollable_text(new_frame, row=1, column=0)

        # Bottom Action Button
        action_frame = ttk.Frame(self.root, padding=10)
        action_frame.grid(row=1, column=0, sticky="ew")
        action_frame.columnconfigure(0, weight=1)

        compare_btn = ttk.Button(action_frame, text="⚡ COMPARE CONFIGURATIONS", command=self.run_compare)
        compare_btn.grid(row=0, column=0, sticky="ew", ipady=6)

    def _create_scrollable_text(self, parent, row, column):
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=column, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        scroll = ttk.Scrollbar(frame)
        scroll.grid(row=0, column=1, sticky="ns")

        txt = tk.Text(frame, yscrollcommand=scroll.set, font=("Courier New", 9), wrap="none", undo=True)
        txt.grid(row=0, column=0, sticky="nsew")

        scroll.config(command=txt.yview)
        return txt

    def _load_old_file(self):
        filepath = filedialog.askopenfilename(
            title="Select Old Configuration File",
            filetypes=[("Text and Config Files", "*.conf *.txt *.cfg"), ("All Files", "*.*")]
        )
        if filepath:
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                self.txt_old_input.delete("1.0", tk.END)
                self.txt_old_input.insert(tk.END, content)
                self.lbl_old_status.config(text=f"Loaded: {os.path.basename(filepath)}")
            except Exception as e:
                messagebox.showerror("Read Error", f"Could not open file:\n{str(e)}")

    def _load_new_file(self):
        filepath = filedialog.askopenfilename(
            title="Select New Configuration File",
            filetypes=[("Text and Config Files", "*.conf *.txt *.cfg"), ("All Files", "*.*")]
        )
        if filepath:
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                self.txt_new_input.delete("1.0", tk.END)
                self.txt_new_input.insert(tk.END, content)
                self.lbl_new_status.config(text=f"Loaded: {os.path.basename(filepath)}")
            except Exception as e:
                messagebox.showerror("Read Error", f"Could not open file:\n{str(e)}")

    def run_compare(self):
        old_text = self.txt_old_input.get("1.0", tk.END).strip()
        new_text = self.txt_new_input.get("1.0", tk.END).strip()

        if not old_text:
            messagebox.showwarning("Missing Data", "Please paste text or select a file for OLD configuration!")
            return
        if not new_text:
            messagebox.showwarning("Missing Data", "Please paste text or select a file for NEW configuration!")
            return

        print("\n")

        # Generate clean diff output with defined filenames
        diff_lines = list(difflib.unified_diff(
            old_text.splitlines(),
            new_text.splitlines(),
            fromfile='old.conf',
            tofile='new.conf',
            lineterm=''
        ))

        if diff_lines:
            for line in diff_lines:
                print_colored_diff(line)
        else:
            print("No differences found — configurations are identical.")

        print("\n")

# ---------------------------------------------------------
# 4. Main Application Entry Point
# ---------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = NetCompareGUI(root)
    root.mainloop()