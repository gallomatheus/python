"""
ProcessKiller - Mata automaticamente um processo .exe sempre que ele aparecer.
Compatível com Windows. Requer: pip install psutil
"""

import tkinter as tk
from tkinter import ttk, messagebox, font
import threading
import time
import sys
import os

import subprocess as _sp
_sp.check_call([sys.executable, "-m", "pip", "install", "psutil"])
import site as _site
for _p in _site.getsitepackages() + [_site.getusersitepackages()]:
    if _p not in sys.path:
        sys.path.insert(0, _p)
import psutil


# ─────────────────────────────────────────────
#  Lógica de monitoramento
# ─────────────────────────────────────────────

class ProcessWatcher:
    def __init__(self, on_killed_callback):
        self._targets: list[str] = []
        self._running = False
        self._thread: threading.Thread | None = None
        self._interval = 5          # segundos entre varreduras
        self._on_killed = on_killed_callback
        self._lock = threading.Lock()

    # ── targets ──────────────────────────────
    def set_targets(self, names: list[str]):
        with self._lock:
            self._targets = [n.lower().strip() for n in names if n.strip()]

    def get_targets(self) -> list[str]:
        with self._lock:
            return list(self._targets)

    # ── controle ─────────────────────────────
    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    # ── loop principal ────────────────────────
    def _loop(self):
        while self._running:
            killed = []
            targets = self.get_targets()
            if targets:
                for proc in psutil.process_iter(["pid", "name"]):
                    try:
                        pname = proc.info["name"].lower()
                        if pname in targets:
                            proc.kill()
                            killed.append(f"{proc.info['name']} (PID {proc.info['pid']})")
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        pass
            if killed:
                for entry in killed:
                    self._on_killed(entry)
            time.sleep(self._interval)


# ─────────────────────────────────────────────
#  Interface gráfica
# ─────────────────────────────────────────────

DARK_BG      = "#0f0f0f"
PANEL_BG     = "#1a1a1a"
BORDER       = "#2a2a2a"
ACCENT       = "#ff3c3c"
ACCENT_DIM   = "#7a1010"
TEXT_PRI     = "#f0f0f0"
TEXT_SEC     = "#888888"
TEXT_LOG     = "#ff6b6b"
GREEN        = "#3cffa0"
YELLOW       = "#ffd23c"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ProcessKiller")
        self.geometry("680x560")
        self.resizable(False, False)
        self.configure(bg=DARK_BG)

        # Ícone (fallback se não tiver .ico)
        try:
            self.iconbitmap(default="")
        except Exception:
            pass

        self._watcher = ProcessWatcher(on_killed_callback=self._on_process_killed)
        self._log_lines = []
        self._kill_count = 0

        self._build_ui()
        self._sync_targets()  # sincroniza processos padrão
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── construção da UI ──────────────────────
    def _build_ui(self):
        # ── Cabeçalho ──
        header = tk.Frame(self, bg=DARK_BG)
        header.pack(fill="x", padx=24, pady=(22, 0))

        title_lbl = tk.Label(
            header, text="⬡  ProcessKiller",
            bg=DARK_BG, fg=ACCENT,
            font=("Courier New", 20, "bold"),
        )
        title_lbl.pack(side="left")

        self._status_dot = tk.Label(
            header, text="●  INATIVO",
            bg=DARK_BG, fg=TEXT_SEC,
            font=("Courier New", 11),
        )
        self._status_dot.pack(side="right", padx=4)

        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=24, pady=(12, 18))

        # ── Área de entrada ──
        input_frame = tk.Frame(self, bg=DARK_BG)
        input_frame.pack(fill="x", padx=24)

        tk.Label(
            input_frame, text="PROCESSOS ALVO",
            bg=DARK_BG, fg=TEXT_SEC,
            font=("Courier New", 9, "bold"),
        ).pack(anchor="w", pady=(0, 6))

        entry_row = tk.Frame(input_frame, bg=DARK_BG)
        entry_row.pack(fill="x")

        self._entry = tk.Entry(
            entry_row,
            bg=PANEL_BG, fg=TEXT_PRI,
            insertbackground=ACCENT,
            relief="flat",
            font=("Courier New", 13),
            bd=0, highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
        )
        self._entry.pack(side="left", fill="x", expand=True, ipady=8, ipadx=10)
        self._entry.insert(0, "exemplo.exe")
        self._entry.bind("<FocusIn>",  self._clear_placeholder)
        self._entry.bind("<Return>",   lambda e: self._add_target())

        btn_add = tk.Button(
            entry_row, text="ADICIONAR",
            bg=ACCENT, fg="#000",
            activebackground=ACCENT_DIM, activeforeground=TEXT_PRI,
            relief="flat", bd=0,
            font=("Courier New", 10, "bold"),
            cursor="hand2",
            command=self._add_target,
            padx=16, pady=8,
        )
        btn_add.pack(side="left", padx=(8, 0))

        # ── Lista de alvos ──
        list_frame = tk.Frame(self, bg=DARK_BG)
        list_frame.pack(fill="x", padx=24, pady=(14, 0))

        tk.Label(
            list_frame, text="LISTA DE ALVOS",
            bg=DARK_BG, fg=TEXT_SEC,
            font=("Courier New", 9, "bold"),
        ).pack(anchor="w", pady=(0, 6))

        lbox_wrap = tk.Frame(list_frame, bg=PANEL_BG, highlightthickness=1,
                             highlightbackground=BORDER)
        lbox_wrap.pack(fill="x")

        self._listbox = tk.Listbox(
            lbox_wrap,
            bg=PANEL_BG, fg=GREEN,
            selectbackground=ACCENT_DIM, selectforeground=TEXT_PRI,
            relief="flat", bd=0,
            font=("Courier New", 12),
            height=4,
            activestyle="none",
        )
        self._listbox.pack(fill="x", padx=8, pady=4)

        for _default in ["LogDesktop.exe", "Logstart.exe"]:
            self._listbox.insert("end", _default)

        remove_btn = tk.Button(
            list_frame, text="REMOVER SELECIONADO",
            bg=PANEL_BG, fg=TEXT_SEC,
            activebackground=BORDER, activeforeground=TEXT_PRI,
            relief="flat", bd=0,
            font=("Courier New", 9),
            cursor="hand2",
            command=self._remove_target,
            pady=4,
        )
        remove_btn.pack(anchor="e", pady=(4, 0))

        # ── Botões de controle ──
        ctrl_frame = tk.Frame(self, bg=DARK_BG)
        ctrl_frame.pack(fill="x", padx=24, pady=14)

        self._btn_start = tk.Button(
            ctrl_frame, text="▶  INICIAR MONITORAMENTO",
            bg=GREEN, fg="#000",
            activebackground="#1a7a50", activeforeground=TEXT_PRI,
            relief="flat", bd=0,
            font=("Courier New", 11, "bold"),
            cursor="hand2",
            command=self._toggle,
            padx=20, pady=10,
        )
        self._btn_start.pack(side="left")

        self._counter_lbl = tk.Label(
            ctrl_frame,
            text="Processos eliminados: 0",
            bg=DARK_BG, fg=TEXT_SEC,
            font=("Courier New", 10),
        )
        self._counter_lbl.pack(side="right")

        # ── Log ──
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=24, pady=(0, 10))

        log_frame = tk.Frame(self, bg=DARK_BG)
        log_frame.pack(fill="both", expand=True, padx=24, pady=(0, 16))

        tk.Label(
            log_frame, text="LOG DE ATIVIDADE",
            bg=DARK_BG, fg=TEXT_SEC,
            font=("Courier New", 9, "bold"),
        ).pack(anchor="w", pady=(0, 6))

        log_wrap = tk.Frame(log_frame, bg=PANEL_BG, highlightthickness=1,
                            highlightbackground=BORDER)
        log_wrap.pack(fill="both", expand=True)

        self._log_text = tk.Text(
            log_wrap,
            bg=PANEL_BG, fg=TEXT_LOG,
            insertbackground=ACCENT,
            relief="flat", bd=0,
            font=("Courier New", 10),
            state="disabled",
            wrap="word",
        )
        scrollbar = tk.Scrollbar(log_wrap, command=self._log_text.yview,
                                 bg=PANEL_BG, troughcolor=PANEL_BG,
                                 activebackground=BORDER)
        self._log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._log_text.pack(fill="both", expand=True, padx=8, pady=6)

        self._append_log("Sistema iniciado. Adicione processos e clique em INICIAR.")

    # ── callbacks ─────────────────────────────
    def _clear_placeholder(self, event):
        if self._entry.get() == "exemplo.exe":
            self._entry.delete(0, "end")

    def _add_target(self):
        name = self._entry.get().strip()
        if not name or name == "exemplo.exe":
            return
        if not name.lower().endswith(".exe"):
            name += ".exe"
        existing = [self._listbox.get(i) for i in range(self._listbox.size())]
        if name.lower() in [e.lower() for e in existing]:
            self._append_log(f"[!] '{name}' já está na lista.")
            return
        self._listbox.insert("end", name)
        self._sync_targets()
        self._entry.delete(0, "end")
        self._append_log(f"[+] Alvo adicionado: {name}")

    def _remove_target(self):
        sel = self._listbox.curselection()
        if not sel:
            return
        name = self._listbox.get(sel[0])
        self._listbox.delete(sel[0])
        self._sync_targets()
        self._append_log(f"[-] Alvo removido: {name}")

    def _sync_targets(self):
        targets = [self._listbox.get(i) for i in range(self._listbox.size())]
        self._watcher.set_targets(targets)

    def _toggle(self):
        if self._watcher.is_running:
            self._watcher.stop()
            self._btn_start.configure(
                text="▶  INICIAR MONITORAMENTO",
                bg=GREEN, fg="#000",
            )
            self._status_dot.configure(text="●  INATIVO", fg=TEXT_SEC)
            self._append_log("[■] Monitoramento encerrado.")
        else:
            if self._listbox.size() == 0:
                messagebox.showwarning(
                    "Nenhum alvo",
                    "Adicione pelo menos um processo .exe antes de iniciar.",
                )
                return
            self._watcher.start()
            self._btn_start.configure(
                text="■  PARAR MONITORAMENTO",
                bg=ACCENT, fg="#000",
            )
            self._status_dot.configure(text="●  ATIVO", fg=GREEN)
            self._append_log("[▶] Monitoramento iniciado. Verificando a cada 5 segundos...")

    def _on_process_killed(self, entry: str):
        self._kill_count += 1
        self.after(0, self._update_killed, entry)

    def _update_killed(self, entry: str):
        self._append_log(f"[✗] ELIMINADO → {entry}")
        self._counter_lbl.configure(
            text=f"Processos eliminados: {self._kill_count}",
            fg=ACCENT,
        )

    def _append_log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        self._log_text.configure(state="normal")
        self._log_text.insert("end", f"[{ts}] {msg}\n")
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    def _on_close(self):
        self._watcher.stop()
        self.destroy()


# ─────────────────────────────────────────────
#  Ponto de entrada
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
