# Cisco / Network Config Diff Tool

A cross-platform Python tool with a Tkinter Graphical User Interface (GUI) designed to easily compare network configuration files (e.g., Cisco, RouterOS, generic `.conf`/`.cfg` files). It outputs side-by-side text comparisons directly into a colorized, ANSI-formatted terminal stream.

---

## 💡Features

- **Automated Dependency Management**: Self-checks and installs missing Python/system packages (`Tkinter`, `hier-config`) on first launch.
- **Cross-Platform**: Supports Windows, Debian/Ubuntu, and Arch Linux out of the box.
- **Intuitive GUI**: Built with Tkinter to easily upload or paste configurations side by side.
- **Colorized Terminal Output**: Styled unified diff output rendered directly in the terminal using ANSI escape codes.
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/18dcf783-7334-42df-abd7-86cfff642071" />


---

## 🛠 Prerequisites & Installation

### Windows

1. **Python 3.x**: Ensure Python is installed and added to your system `PATH`.
   > **Note**: During Python installation on Windows, make sure the **`tcl/tk and IDLE`** option is checked (it is enabled by default).
2. Clone or download this repository.
3. No manual `pip` installation is strictly required — the script automatically checks and installs required libraries (like `hier_config`) on launch.

### Linux (Debian, Ubuntu, Arch, Manjaro)

1. Ensure **Python 3** and **`pip`** are installed.
2. The script includes a built-in bootstrapper that automatically detects your distribution and installs Tkinter (`python3-tk` or `tk`) via `apt` or `pacman` if missing.

---

## 📦 Usage

### Running on Windows

Open Command Prompt or PowerShell in the repository folder and run:

```cmd
python CCDT.py
```
### Running on Linux

Open Terminal and run:

```shell
python -m venv venv
source ./venv/bin/activate.fish
python CCDT.py
