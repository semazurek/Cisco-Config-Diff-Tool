import os
import re
import sys
import difflib
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


APP_TITLE = "Cisco Config Diff Tool"

# Cisco IOS/IOS-XE/IOS-XR-style configuration sections. The parser also uses
# indentation, so this list is a fallback for common configuration modes and
# for command snippets pasted without indentation.
_CONTEXT_HEADER_PATTERNS = [
    (re.compile(r"^(?:interface|int)\s+\S+", re.I), "interface"),
    (re.compile(r"^router\s+\S+", re.I), "router"),
    (re.compile(r"^line\s+\S+", re.I), "line"),
    (re.compile(r"^vlan\s+\S+", re.I), "vlan"),
    (re.compile(r"^(?:ip|ipv6)\s+access-list\s+\S+", re.I), "acl"),
    (re.compile(r"^route-map\s+\S+", re.I), "route-map"),
    (re.compile(r"^(?:class-map|policy-map)\b", re.I), "policy"),
    (re.compile(r"^vrf\s+definition\s+\S+", re.I), "vrf"),
    (re.compile(r"^ip\s+vrf\s+\S+", re.I), "vrf"),
    (re.compile(r"^ip\s+dhcp\s+pool\s+\S+", re.I), "dhcp-pool"),
    (re.compile(r"^aaa\s+group\s+server\s+\S+", re.I), "aaa-group"),
    (re.compile(r"^(?:tacacs|radius)\s+server\s+\S+", re.I), "aaa-server"),
    (re.compile(r"^crypto\s+(?:ikev2\s+(?:proposal|policy|profile|keyring)|isakmp\s+(?:policy|profile)|ipsec\s+profile|map|pki\s+(?:trustpoint|certificate\s+chain))\b", re.I), "crypto"),
    (re.compile(r"^key\s+chain\s+\S+", re.I), "key-chain"),
    (re.compile(r"^spanning-tree\s+mst\s+configuration$", re.I), "mst"),
    (re.compile(r"^vlan\s+configuration\s+\S+", re.I), "vlan-config"),
    (re.compile(r"^ipv6\s+router\s+\S+", re.I), "ipv6-router"),
    (re.compile(r"^ip\s+sla\s+\d+\b", re.I), "ip-sla"),
    (re.compile(r"^track\s+\d+\b", re.I), "track"),
    (re.compile(r"^event\s+manager\s+applet\s+\S+", re.I), "eem"),
    (re.compile(r"^object-group\s+\S+", re.I), "object-group"),
    (re.compile(r"^object\s+(?:network|service|group)\s+\S+", re.I), "object"),
    (re.compile(r"^flow\s+(?:record|exporter|monitor)\s+\S+", re.I), "flow"),
    (re.compile(r"^parameter-map\s+\S+", re.I), "parameter-map"),
    (re.compile(r"^dial-peer\s+voice\s+\S+", re.I), "dial-peer"),
    (re.compile(r"^voice\s+(?:class|translation-rule)\s+\S+", re.I), "voice"),
    (re.compile(r"^zone(?:-pair)?\s+\S+", re.I), "zone"),
    (re.compile(r"^control-plane$", re.I), "control-plane"),
    (re.compile(r"^archive$", re.I), "archive"),
    (re.compile(r"^address-family\b", re.I), "nested"),
    (re.compile(r"^af-interface\b", re.I), "nested"),
    (re.compile(r"^af-group\b", re.I), "nested"),
    (re.compile(r"^class\s+\S+", re.I), "nested"),
    (re.compile(r"^template\s+\S+", re.I), "template"),
    (re.compile(r"^certificate\s+map\s+\S+", re.I), "certificate-map"),
]

# These commands are usually global configuration commands. This list is
# used only when NEW is pasted as an unindented command-mode snippet.
_GLOBAL_COMMAND_PATTERNS = [
    re.compile(p, re.I) for p in [
        r"^(?:no\s+)?hostname\b",
        r"^version\b",
        r"^boot(?:-start-marker|-end-marker)?\b",
        r"^(?:no\s+)?service\b",
        r"^(?:no\s+)?ip\s+(?:routing|cef|name-server|domain-name|domain\s+lookup|default-gateway|route\b|ssh\b|http\b|tftp\b|ftp\b|scp\b|forward-protocol\b|prefix-list\b|community-list\b|as-path\s+access-list\b|dhcp\s+excluded-address\b|nat\b)",
        r"^(?:no\s+)?ipv6\s+(?:unicast-routing|route\b)",
        r"^(?:no\s+)?logging\b",
        r"^snmp-server\b",
        r"^aaa\b",
        r"^username\b",
        r"^enable\s+(?:secret|password|algorithm-type)\b",
        r"^(?:no\s+)?clock\b",
        r"^(?:no\s+)?ntp\b",
        r"^tacacs\s+server\b",
        r"^radius\s+server\b",
        r"^crypto\s+(?:pki|ikev2|isakmp|ipsec)\b",
        r"^spanning-tree\s+(?:mode|extend|loopguard|portfast\s+default)\b",
        r"^(?:no\s+)?cdp\s+run\b",
        r"^(?:no\s+)?lldp\s+(?:run|receive|transmit)\b",
        r"^errdisable\s+recovery\b",
        r"^redundancy\b",
        r"^license\b",
        r"^call-home\b",
        r"^netconf\b",
        r"^restconf\b",
    ]
]

_INTERFACE_ALIASES = {
    "gi": "gigabitethernet",
    "gigabitethernet": "gigabitethernet",
    "fa": "fastethernet",
    "fastethernet": "fastethernet",
    "te": "tengigabitethernet",
    "tengigabitethernet": "tengigabitethernet",
    "fo": "fortygigabitethernet",
    "fortygigabitethernet": "fortygigabitethernet",
    "hu": "hundredgigabitethernet",
    "hundredgigabitethernet": "hundredgigabitethernet",
    "eth": "ethernet",
    "et": "ethernet",
    "ethernet": "ethernet",
    "po": "port-channel",
    "port-channel": "port-channel",
    "lo": "loopback",
    "loopback": "loopback",
    "vl": "vlan",
    "vlan": "vlan",
    "tu": "tunnel",
    "tunnel": "tunnel",
    "se": "serial",
    "serial": "serial",
    "mgmt": "management",
    "management": "management",
}
_SENSITIVE_MARKERS = {
    "secret", "password", "community", "key-string",
    "authentication-key", "message-digest-key",
}


def _collapse_whitespace(value):
    """Normalize spacing without changing meaningful text."""
    return re.sub(r"\s+", " ", value).strip()


def _canonical_interface_header(command):
    """Expand common Cisco interface abbreviations in interface headers."""
    match = re.match(r"^(?:interface|int)\s+(.+)$", command, re.I)
    if not match:
        return _collapse_whitespace(command).casefold()

    interface_part = match.group(1)

    def expand(match_obj):
        token = match_obj.group(1).casefold()
        suffix = match_obj.group(2)
        return _INTERFACE_ALIASES.get(token, token) + suffix

    # Handles names in "interface range" as well as a single interface.
    interface_part = re.sub(
        r"(?<![A-Za-z])([A-Za-z-]+)(\d[\w./:-]*)",
        expand,
        interface_part,
    )
    return "interface " + _collapse_whitespace(interface_part).casefold()


def _normalize_command(command):
    """
    Build a comparison key for one command.

    IOS command keywords are case-insensitive. Free-form descriptions,
    remarks, banners and values following common secret/password markers are
    kept case-sensitive to avoid treating genuinely different values as equal.
    """
    command = _collapse_whitespace(command)
    if not command:
        return ""

    parts = command.split()
    first = parts[0].casefold()

    if first in {"description", "remark"}:
        return first + (" " + " ".join(parts[1:]) if len(parts) > 1 else "")

    if first == "banner":
        if len(parts) > 1:
            return "banner " + " ".join(parts[1:])
        return "banner"

    lowered = [part.casefold() for part in parts]
    for index, token in enumerate(lowered):
        if token in _SENSITIVE_MARKERS:
            # Normalize command syntax before the value, but preserve the
            # value itself (hashes, passwords, communities, keys).
            return " ".join(lowered[:index + 1] + parts[index + 1:])

    return " ".join(lowered)


def _context_header_kind(command):
    for pattern, kind in _CONTEXT_HEADER_PATTERNS:
        if pattern.match(command):
            return kind
    return None


def _canonical_context_header(command):
    if re.match(r"^(?:interface|int)\s+", command, re.I):
        return _canonical_interface_header(command)
    return _collapse_whitespace(command).casefold()


def _is_global_command_in_unindented_snippet(command):
    return any(pattern.match(command) for pattern in _GLOBAL_COMMAND_PATTERNS)


def _is_ignored_output_line(command):
    lowered = command.casefold()
    if not command:
        return True
    if lowered in {"building configuration...", "end", "exit", "configure terminal", "conf t"}:
        return True
    if re.match(r"^current configuration\s*:", lowered):
        return True
    if re.match(r"^last configuration change", lowered):
        return True
    if re.match(r"^using\s+\d+\s+out of\s+\d+\s+bytes", lowered):
        return True
    if re.match(r"^\S+[>#]\s*(?:show\s+(?:running-config|run).*)?$", command, re.I):
        return True
    return False


class ConfigEntry:
    """One meaningful line from a Cisco configuration."""

    __slots__ = ("line_number", "raw_line", "command", "context", "key", "is_header")

    def __init__(self, line_number, raw_line, command, context, key, is_header):
        self.line_number = line_number
        self.raw_line = raw_line
        self.command = command
        self.context = tuple(context)
        self.key = tuple(key)
        self.is_header = is_header


def parse_cisco_config(config_text):
    """
    Parse a Cisco config into context-aware command keys.

    Normal show running-config indentation is preferred. If the pasted text
    contains no indentation at all, common context headers are used to support
    command snippets such as:
        interface Gi1/0/1
        description Uplink
        switchport mode trunk
    """
    raw_lines = config_text.splitlines()
    meaningful_lines = [
        line for line in raw_lines
        if line.strip()
        and line.strip() != "!"
        and line.strip().casefold() not in {"exit", "exit-address-family", "end"}
    ]
    # Indentation on a mode-exit command does not mean the actual config
    # statements are indented. This supports command snippets where only
    # "exit-address-family" is indented.
    unindented_mode = not any(
        line[:1].isspace() for line in meaningful_lines
    )

    entries = []
    stack = []  # (indent level, canonical context header)

    for line_number, raw_line in enumerate(raw_lines, start=1):
        command = raw_line.strip()

        # "!" is a visual separator, not always an end-of-context marker.
        # In an indented show run, indentation of the next command safely
        # determines which parent blocks remain active. In a fully unindented
        # snippet, pop a nested mode first (e.g. address-family), otherwise
        # close the current top-level section.
        if command == "!":
            if unindented_mode:
                if len(stack) > 1:
                    stack.pop()
                else:
                    stack.clear()
            continue

        if not command:
            continue

        lowered = command.casefold()
        if lowered in {"end", "exit"}:
            if stack:
                stack.pop()
            continue
        if lowered == "exit-address-family":
            if stack and stack[-1][1].startswith("address-family "):
                stack.pop()
            continue

        if _is_ignored_output_line(command):
            continue

        # Some CLI snippets contain prompts or mode-control commands.
        if command.startswith(("(",)) and command.endswith((")",)):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" \t"))
        header_kind = _context_header_kind(command)

        if unindented_mode:
            if header_kind:
                # address-family / class / af-interface are nested beneath
                # the current router or policy-map context.
                nested_header = header_kind == "nested"
                if stack and not nested_header:
                    stack.clear()

                context = tuple(item[1] for item in stack)
                canonical_header = _canonical_context_header(command)
                key = context + (canonical_header,)
                entries.append(ConfigEntry(
                    line_number, raw_line, command, context, key, True
                ))
                stack.append((len(stack), canonical_header))
                continue

            if stack and not _is_global_command_in_unindented_snippet(command):
                context = tuple(item[1] for item in stack)
            else:
                context = ()
                if _is_global_command_in_unindented_snippet(command):
                    stack.clear()

            normalized = _normalize_command(command)
            if normalized:
                entries.append(ConfigEntry(
                    line_number, raw_line, command, context,
                    context + (normalized,), False
                ))
            continue

        # Standard show run mode: indentation determines parent/child context.
        while stack and indent <= stack[-1][0]:
            stack.pop()

        context = tuple(item[1] for item in stack)

        if header_kind:
            canonical_header = _canonical_context_header(command)
            key = context + (canonical_header,)
            entries.append(ConfigEntry(
                line_number, raw_line, command, context, key, True
            ))
            stack.append((indent, canonical_header))
        else:
            normalized = _normalize_command(command)
            if normalized:
                entries.append(ConfigEntry(
                    line_number, raw_line, command, context,
                    context + (normalized,), False
                ))

    return entries


def compare_cisco_configs(old_text, new_text):
    """
    Compare NEW as a list of desired commands against the full OLD config.

    A command is present only if the same normalized command exists under the
    same context (for example, the same interface or router section).
    Explicit Cisco negation commands ("no ...") are classified as removals.
    """
    old_entries = parse_cisco_config(old_text)
    new_entries = parse_cisco_config(new_text)
    old_keys = {entry.key for entry in old_entries}

    results = []
    present_count = 0
    missing_count = 0
    removed_count = 0

    for entry in new_entries:
        if re.match(r"^no\s+", entry.command, re.I):
            status = "removed"
            removed_count += 1
        elif entry.key in old_keys:
            status = "present"
            present_count += 1
        else:
            status = "missing"
            missing_count += 1
        results.append((status, entry))

    return {
        "old_count": len(old_entries),
        "new_count": len(new_entries),
        "present_count": present_count,
        "missing_count": missing_count,
        "removed_count": removed_count,
        "results": results,
    }


def print_colored_diff(line, color_override=None):
    """Print a diff/result line with ANSI colors in the terminal."""
    if sys.platform.startswith("win"):
        os.system("")

    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"
    RESET = "\033[0m"

    if color_override == "present":
        color = GRAY
    elif color_override == "missing":
        color = GREEN
    elif color_override == "removed":
        color = RED
    elif line.startswith("---"):
        color = RED
    elif line.startswith("+++"):
        color = GREEN
    elif line.startswith("-"):
        color = RED
    elif line.startswith("+"):
        color = GREEN
    elif line.startswith("@@"):
        color = YELLOW
    elif line.startswith("***"):
        color = CYAN
    elif line.startswith("="):
        color = GRAY
    else:
        color = RESET

    print(f"{color}{line}{RESET}")


class NetCompareGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1100x700")
        self.root.minsize(760, 520)

        self.compare_mode = tk.StringVar(value="semantic")
        self.status_text = tk.StringVar(
            value="Paste the OLD configuration and the NEW, then run the comparison."
        )

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=0)

        self._build_ui()

    def _build_ui(self):
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.grid(row=0, column=0, sticky="nsew")
        top_frame.columnconfigure(0, weight=1)
        top_frame.columnconfigure(1, weight=1)
        top_frame.rowconfigure(0, weight=1)

        old_frame = ttk.LabelFrame(
            top_frame, text=" OLD — full show running-config ", padding=5
        )
        old_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=5)
        old_frame.columnconfigure(0, weight=1)
        old_frame.rowconfigure(1, weight=1)

        old_btn_frame = ttk.Frame(old_frame)
        old_btn_frame.grid(row=0, column=0, sticky="ew", pady=2)
        old_btn_frame.columnconfigure(1, weight=1)
        ttk.Button(
            old_btn_frame, text="📁 Browse...", command=self._load_old_file
        ).grid(row=0, column=0, sticky="w")
        self.lbl_old_status = ttk.Label(
            old_btn_frame,
            text="You can paste the text below",
            font=("sans-serif", 8, "italic"),
        )
        self.lbl_old_status.grid(row=0, column=1, sticky="e", padx=5)
        self.txt_old_input = self._create_scrollable_text(old_frame, 1, 0)

        new_frame = ttk.LabelFrame(
            top_frame, text=" NEW — commands to add / update ", padding=5
        )
        new_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=5)
        new_frame.columnconfigure(0, weight=1)
        new_frame.rowconfigure(1, weight=1)

        new_btn_frame = ttk.Frame(new_frame)
        new_btn_frame.grid(row=0, column=0, sticky="ew", pady=2)
        new_btn_frame.columnconfigure(1, weight=1)
        ttk.Button(
            new_btn_frame, text="📁 Browse...", command=self._load_new_file
        ).grid(row=0, column=0, sticky="w")
        self.lbl_new_status = ttk.Label(
            new_btn_frame,
            text="You can paste the text below",
            font=("sans-serif", 8, "italic"),
        )
        self.lbl_new_status.grid(row=0, column=1, sticky="e", padx=5)
        self.txt_new_input = self._create_scrollable_text(new_frame, 1, 0)

        action_frame = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        action_frame.grid(row=1, column=0, sticky="ew")
        action_frame.columnconfigure(0, weight=1)

        mode_frame = ttk.LabelFrame(
            action_frame, text=" Comparison mode ", padding=(8, 4)
        )
        mode_frame.grid(row=0, column=0, sticky="ew", pady=(0, 7))
        ttk.Radiobutton(
            mode_frame,
            text="Cisco — check for the presence of commands within the same context (recommended)",
            variable=self.compare_mode,
            value="semantic",
        ).grid(row=0, column=0, sticky="w", padx=4)
        ttk.Radiobutton(
            mode_frame,
            text="Classic line-based diff (the old way)",
            variable=self.compare_mode,
            value="classic",
        ).grid(row=1, column=0, sticky="w", padx=4)

        ttk.Button(
            action_frame,
            text="⚡ COMPARE CONFIGURATIONS",
            command=self.run_compare,
        ).grid(row=1, column=0, sticky="ew", ipady=7)

        ttk.Label(
            action_frame,
            textvariable=self.status_text,
            anchor="w",
            font=("sans-serif", 8),
        ).grid(row=2, column=0, sticky="ew", pady=(6, 0))

    def _create_scrollable_text(self, parent, row, column):
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=column, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        y_scroll = ttk.Scrollbar(frame, orient="vertical")
        x_scroll = ttk.Scrollbar(frame, orient="horizontal")
        text_widget = tk.Text(
            frame,
            yscrollcommand=y_scroll.set,
            xscrollcommand=x_scroll.set,
            font=("Courier New", 9),
            wrap="none",
            undo=True,
            maxundo=-1,
        )
        text_widget.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        y_scroll.config(command=text_widget.yview)
        x_scroll.config(command=text_widget.xview)
        return text_widget

    @staticmethod
    def _read_config_file(filepath):
        # utf-8-sig also removes a BOM if the file was saved by Windows tools.
        with open(filepath, "r", encoding="utf-8-sig", errors="replace") as file:
            return file.read()

    def _load_old_file(self):
        filepath = filedialog.askopenfilename(
            title="Select Old Configuration File",
            filetypes=[
                ("Text and Config Files", "*.conf *.txt *.cfg *.log"),
                ("All Files", "*.*"),
            ],
        )
        if not filepath:
            return

        try:
            content = self._read_config_file(filepath)
            self.txt_old_input.delete("1.0", tk.END)
            self.txt_old_input.insert("1.0", content)
            self.lbl_old_status.config(text=f"Loaded: {os.path.basename(filepath)}")
            self.status_text.set(f"Załadowano OLD: {os.path.basename(filepath)}")
        except (OSError, UnicodeError) as error:
            messagebox.showerror("Read Error", f"Nie można otworzyć pliku:\n{error}")

    def _load_new_file(self):
        filepath = filedialog.askopenfilename(
            title="Select New Configuration File",
            filetypes=[
                ("Text and Config Files", "*.conf *.txt *.cfg *.log"),
                ("All Files", "*.*"),
            ],
        )
        if not filepath:
            return

        try:
            content = self._read_config_file(filepath)
            self.txt_new_input.delete("1.0", tk.END)
            self.txt_new_input.insert("1.0", content)
            self.lbl_new_status.config(text=f"Loaded: {os.path.basename(filepath)}")
            self.status_text.set(f"NEW: {os.path.basename(filepath)}")
        except (OSError, UnicodeError) as error:
            messagebox.showerror("Read Error", f"Cannot open file:\n{error}")

    @staticmethod
    def _get_text_without_widget_sentinel(widget):
        # Do not use .strip(): leading spaces can define Cisco config hierarchy.
        return widget.get("1.0", "end-1c").rstrip("\n")

    def _show_result_window(self, title, summary, rows):
        result_window = tk.Toplevel(self.root)
        result_window.title(title)
        result_window.geometry("1050x700")
        result_window.minsize(700, 420)
        result_window.columnconfigure(0, weight=1)
        result_window.rowconfigure(1, weight=1)

        ttk.Label(
            result_window,
            text=summary,
            padding=(10, 10, 10, 5),
            justify="left",
            wraplength=1000,
        ).grid(row=0, column=0, sticky="ew")

        text_frame = ttk.Frame(result_window, padding=(10, 0, 10, 10))
        text_frame.grid(row=1, column=0, sticky="nsew")
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        y_scroll = ttk.Scrollbar(text_frame, orient="vertical")
        x_scroll = ttk.Scrollbar(text_frame, orient="horizontal")
        output = tk.Text(
            text_frame,
            wrap="none",
            font=("Courier New", 10),
            yscrollcommand=y_scroll.set,
            xscrollcommand=x_scroll.set,
        )
        output.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        y_scroll.config(command=output.yview)
        x_scroll.config(command=output.xview)

        output.tag_configure("present", foreground="#888888")
        output.tag_configure("missing", foreground="#16803c")
        output.tag_configure("removed", foreground="#c62828")
        output.tag_configure("heading", foreground="#245a8d", font=("Courier New", 10, "bold"))
        output.tag_configure("normal", foreground="#202020")

        for row in rows:
            if len(row) == 3:
                prefix, line, tag = row
                output.insert(tk.END, prefix + line + "\n", tag)
            else:
                line, tag = row
                output.insert(tk.END, line + "\n", tag)

        output.config(state="disabled")

    def _run_semantic_compare(self, old_text, new_text):
        comparison = compare_cisco_configs(old_text, new_text)

        summary = (
            f"OLD: {comparison['old_count']} identified entries | "
            f"NEW: {comparison['new_count']} entries to be checked\n"
            f"ALREADY EXISTS: {comparison['present_count']} | "
            f"TO BE ADDED / UPDATED: {comparison['missing_count']} | "
            f"TO BE REMOVED: {comparison['removed_count']}\n"
        )

        rows = [
            (" ", " ", "heading"),
            ("", "", "normal"),
        ]

        for status, entry in comparison["results"]:
            if status == "present":
                rows.append(("= ", entry.raw_line, "present"))
                print_colored_diff("= " + entry.raw_line, "present")
            elif status == "removed":
                rows.append(("- ", entry.raw_line, "removed"))
                print_colored_diff("- " + entry.raw_line, "removed")
            else:
                rows.append(("+ ", entry.raw_line, "missing"))
                print_colored_diff("+ " + entry.raw_line, "missing")

        print("\n" + summary + "\n")
        if not comparison["results"]:
            rows.append(("", "No commands found for comparison.", "normal"))

        self._show_result_window("Cisco comparison result", summary, rows)
        self.status_text.set(
            f"Comparison complete: {comparison['present_count']} exists, "
            f"{comparison['missing_count']} to be added/updated, "
            f"{comparison['removed_count']} to be removed."
        )

    def _run_classic_compare(self, old_text, new_text):
        diff_lines = list(difflib.unified_diff(
            old_text.splitlines(),
            new_text.splitlines(),
            fromfile="old.conf",
            tofile="new.conf",
            lineterm="",
        ))

        rows = []
        if diff_lines:
            for line in diff_lines:
                rows.append((line, "removed" if line.startswith("-") else
                             "missing" if line.startswith("+") else "normal"))
                print_colored_diff(line)
            summary = (
                f"Classic linear diff: {len(diff_lines)} result lines. "
            )
        else:
            summary = "No differences — the configurations are identical."
            rows.append((summary, "normal"))
            print(summary)

        self._show_result_window("Classic diff", summary, rows)
        self.status_text.set("The classic linear comparison has been completed.")

    def run_compare(self):
        old_text = self._get_text_without_widget_sentinel(self.txt_old_input)
        new_text = self._get_text_without_widget_sentinel(self.txt_new_input)

        if not old_text.strip():
            messagebox.showwarning(
                "Missing Data",
                "Paste the text or select a file containing the OLD configuration.",
            )
            return
        if not new_text.strip():
            messagebox.showwarning(
                "Missing Data",
                "Paste the text or select a file containing the NEW configuration.",
            )
            return

        print("\n")

        try:
            if self.compare_mode.get() == "classic":
                self._run_classic_compare(old_text, new_text)
            else:
                self._run_semantic_compare(old_text, new_text)
        except Exception as error:
            messagebox.showerror(
                "Compare Error",
                f"An error occurred while comparing the configuration:\n{error}",
            )
            self.status_text.set("Comparison failed.")


def main():
    try:
        root = tk.Tk()
    except tk.TclError as error:
        print(f"Unable to launch the Tkinter graphical interface: {error}")
        print("Check whether Python has been installed with Tcl/Tk support.")
        return 1

    NetCompareGUI(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
