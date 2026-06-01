"""
Auto Clicker - versão 3 (interface compacta)
--------------------------------------------------
Janela principal mínima (só o botão). Configurações e gravação de
múltiplos pontos ficam em pequenas janelas no menu "Opções".

Recursos:
- Intervalo configurável em H / M / S / MS
- Captura de posição por clique ("Capturar ponto")
- Hotkey global configurável (padrão: F6)
- Modo "múltiplos cliques": várias posições, cada uma com seu delay

Dependências: pip install pynput
"""

import os
import sys
import time
import threading

import tkinter as tk
from tkinter import ttk, messagebox

from pynput.mouse import Button, Controller as MouseController, Listener as MouseListener
from pynput import keyboard


def resource_path(relative):
    """Resolve o caminho de arquivos embutidos (necessário após o PyInstaller)."""
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, relative)


def format_key(key):
    """Nome legível para a tecla."""
    if isinstance(key, keyboard.KeyCode) and key.char:
        return key.char.upper()
    if isinstance(key, keyboard.Key):
        return key.name.upper()
    return str(key)


class ClickerEngine(threading.Thread):
    """Thread que executa os cliques em loop enquanto 'running' for True."""

    def __init__(self):
        super().__init__()
        self.daemon = True
        self.mouse = MouseController()
        self.running = False
        self.alive = True

        # Modo posição atual
        self.delay = 0.1
        self.button = Button.left

        # Modo múltiplos cliques: lista de {x, y, delay, button}
        self.positions = []
        self.use_positions = False

    def run(self):
        while self.alive:
            if not self.running:
                time.sleep(0.05)
                continue

            if self.use_positions and self.positions:
                for pos in list(self.positions):
                    if not self.running:
                        break
                    self.mouse.position = (pos["x"], pos["y"])
                    self.mouse.click(pos["button"])
                    time.sleep(pos["delay"])
            else:
                self.mouse.click(self.button)
                time.sleep(self.delay)


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Clicker")
        self.root.resizable(False, False)
        try:
            self.root.iconbitmap(resource_path("AutoClicker.ico"))
        except Exception:
            pass

        self.engine = ClickerEngine()
        self.engine.start()

        self.toggle_key = keyboard.Key.f6
        self.listener = None
        self.settings_win = None
        self.recorder_win = None

        # Variáveis persistentes (compartilhadas entre as janelas)
        self.h_var = tk.StringVar(value="0")
        self.m_var = tk.StringVar(value="0")
        self.s_var = tk.StringVar(value="0")
        self.ms_var = tk.StringVar(value="100")
        self.button_var = tk.StringVar(value="Esquerdo")
        self.use_positions_var = tk.BooleanVar(value=False)
        self.hotkey_var = tk.StringVar(value=format_key(self.toggle_key))
        self.btn_text_var = tk.StringVar()
        self._set_button_idle()

        self._build_main()
        self._start_main_listener()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ============================ UTIL ============================
    def _center_over_parent(self, win):
        """Posiciona a janela 'win' centralizada sobre a janela principal."""
        win.update_idletasks()
        px, py = self.root.winfo_x(), self.root.winfo_y()
        pw, ph = self.root.winfo_width(), self.root.winfo_height()
        w, h = win.winfo_width(), win.winfo_height()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        win.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    # ============================ JANELA PRINCIPAL ============================
    def _build_main(self):
        menubar = tk.Menu(self.root)

        m_opt = tk.Menu(menubar, tearoff=0)
        m_opt.add_command(label="Configurações...", command=self.open_settings)
        m_opt.add_command(label="Gravar múltiplos cliques...", command=self.open_recorder)
        menubar.add_cascade(label="Opções", menu=m_opt)
        menubar.add_command(label="Ajuda", command=self.show_help)
        self.root.config(menu=menubar)

        wrap = ttk.Frame(self.root, padding=14)
        wrap.pack(fill="both", expand=True)
        self.toggle_btn = ttk.Button(wrap, textvariable=self.btn_text_var, command=self.toggle, width=26)
        self.toggle_btn.pack(fill="x", ipady=16)

    def _set_button_idle(self):
        self.btn_text_var.set(f"Pressione {format_key(self.toggle_key)} para clicar")

    def _set_button_running(self):
        self.btn_text_var.set(f"Clicando...  ({format_key(self.toggle_key)} para parar)")

    # ============================ CONFIGURAÇÕES ============================
    def open_settings(self):
        if self.settings_win and self.settings_win.winfo_exists():
            self.settings_win.lift()
            return

        win = tk.Toplevel(self.root)
        self.settings_win = win
        win.title("Configurações")
        win.resizable(False, False)
        win.transient(self.root)
        try:
            win.iconbitmap(resource_path("AutoClicker.ico"))
        except Exception:
            pass

        f_int = ttk.LabelFrame(win, text="Intervalo entre cliques")
        f_int.pack(fill="x", padx=12, pady=(12, 0))
        for col, (label, var) in enumerate(
            [("H", self.h_var), ("M", self.m_var), ("S", self.s_var), ("MS", self.ms_var)]
        ):
            ttk.Label(f_int, text=label).grid(row=0, column=col, padx=6, pady=(6, 0))
            ttk.Entry(f_int, textvariable=var, width=6, justify="center").grid(
                row=1, column=col, padx=6, pady=6
            )

        f_btn = ttk.Frame(win)
        f_btn.pack(fill="x", padx=12, pady=(10, 0))
        ttk.Label(f_btn, text="Botão do mouse:").pack(side="left")
        ttk.Combobox(
            f_btn, textvariable=self.button_var, values=["Esquerdo", "Direito"],
            width=10, state="readonly",
        ).pack(side="left", padx=8)

        f_hk = ttk.Frame(win)
        f_hk.pack(fill="x", padx=12, pady=(10, 0))
        ttk.Label(f_hk, text="Atalho:").pack(side="left")
        ttk.Label(f_hk, textvariable=self.hotkey_var, foreground="#2980b9").pack(side="left", padx=6)
        self.hotkey_btn = ttk.Button(f_hk, text="Alterar", width=8, command=self.change_hotkey)
        self.hotkey_btn.pack(side="left", padx=6)

        ttk.Button(win, text="OK", command=self._close_settings).pack(pady=12)
        win.protocol("WM_DELETE_WINDOW", self._close_settings)
        self._center_over_parent(win)

    def _close_settings(self):
        if self.settings_win:
            self.settings_win.destroy()
            self.settings_win = None

    # ============================ GRAVAR MÚLTIPLOS CLIQUES ============================
    def open_recorder(self):
        if self.recorder_win and self.recorder_win.winfo_exists():
            self.recorder_win.lift()
            return

        win = tk.Toplevel(self.root)
        self.recorder_win = win
        win.title("Gravar múltiplos cliques")
        win.resizable(False, False)
        win.transient(self.root)
        try:
            win.iconbitmap(resource_path("AutoClicker.ico"))
        except Exception:
            pass

        ttk.Checkbutton(
            win, text="Gravar e repetir múltiplos cliques", variable=self.use_positions_var
        ).pack(anchor="w", padx=12, pady=(12, 6))

        f_count = ttk.Frame(win)
        f_count.pack(fill="x", padx=12)
        ttk.Label(f_count, text="Cliques gravados:").pack(side="left")
        self.count_var = tk.StringVar()
        ttk.Label(f_count, textvariable=self.count_var, font=("TkDefaultFont", 10, "bold")).pack(
            side="left", padx=6
        )

        cols = ("#", "X", "Y", "Delay")
        self.tree = ttk.Treeview(win, columns=cols, show="headings", height=4)
        for c, w in zip(cols, (28, 64, 64, 84)):
            self.tree.heading(c, text=("Delay (ms)" if c == "Delay" else c))
            self.tree.column(c, width=w, anchor="center")
        self.tree.pack(fill="x", padx=12, pady=8)

        f_btns = ttk.Frame(win)
        f_btns.pack(fill="x", padx=12, pady=(0, 6))
        self.capture_btn = ttk.Button(f_btns, text="Capturar ponto", command=self.capture_position)
        self.capture_btn.pack(side="left")
        ttk.Button(f_btns, text="Remover", command=self.remove_position).pack(side="left", padx=6)
        ttk.Button(f_btns, text="Limpar", command=self.clear_positions).pack(side="left")

        self.rec_status = tk.StringVar(value="")
        ttk.Label(win, textvariable=self.rec_status, foreground="#2980b9").pack(padx=12)

        ttk.Button(win, text="OK", command=self._close_recorder).pack(pady=12)
        win.protocol("WM_DELETE_WINDOW", self._close_recorder)

        self._refresh_recorder()
        self._center_over_parent(win)

    def _close_recorder(self):
        if self.recorder_win:
            self.recorder_win.destroy()
            self.recorder_win = None

    def _refresh_recorder(self):
        if not (self.recorder_win and self.recorder_win.winfo_exists()):
            return
        self.count_var.set(str(len(self.engine.positions)))
        self.tree.delete(*self.tree.get_children())
        for i, p in enumerate(self.engine.positions, start=1):
            self.tree.insert("", "end", values=(i, p["x"], p["y"], round(p["delay"] * 1000)))

    def capture_position(self):
        self.capture_btn.configure(state="disabled")
        self.rec_status.set("Clique no alvo na tela...")

        def on_click(x, y, button, pressed):
            if pressed:
                self.root.after(0, lambda: self._add_position(x, y))
                return False  # encerra este listener temporário

        self._cap_listener = MouseListener(on_click=on_click)
        self._cap_listener.start()

    def _add_position(self, x, y):
        delay = self._read_interval(silent=True) or 0.1
        btn = Button.left if self.button_var.get() == "Esquerdo" else Button.right
        self.engine.positions.append({"x": int(x), "y": int(y), "delay": delay, "button": btn})
        if self.recorder_win and self.recorder_win.winfo_exists():
            self.capture_btn.configure(state="normal")
            self.rec_status.set("")
            self._refresh_recorder()

    def remove_position(self):
        if not (self.recorder_win and self.recorder_win.winfo_exists()):
            return
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        del self.engine.positions[idx]
        self._refresh_recorder()

    def clear_positions(self):
        self.engine.positions.clear()
        self._refresh_recorder()

    # ============================ HOTKEY ============================
    def _start_main_listener(self):
        def on_press(key):
            if key == self.toggle_key:
                self.root.after(0, self.toggle)

        self.listener = keyboard.Listener(on_press=on_press)
        self.listener.daemon = True
        self.listener.start()

    def change_hotkey(self):
        try:
            self.hotkey_btn.configure(state="disabled")
        except Exception:
            pass
        self.hotkey_var.set("pressione...")
        if self.listener:
            self.listener.stop()

        def on_press(key):
            self.root.after(0, lambda: self._set_hotkey(key))
            return False

        self._hk_listener = keyboard.Listener(on_press=on_press)
        self._hk_listener.start()

    def _set_hotkey(self, key):
        self.toggle_key = key
        self.hotkey_var.set(format_key(key))
        try:
            if self.hotkey_btn.winfo_exists():
                self.hotkey_btn.configure(state="normal")
        except Exception:
            pass
        self._set_button_running() if self.engine.running else self._set_button_idle()
        self._start_main_listener()

    # ============================ INTERVALO ============================
    def _read_interval(self, silent=False):
        try:
            h = int(self.h_var.get() or 0)
            m = int(self.m_var.get() or 0)
            s = int(self.s_var.get() or 0)
            ms = int(self.ms_var.get() or 0)
            total = h * 3600 + m * 60 + s + ms / 1000
            if total <= 0:
                raise ValueError
        except ValueError:
            if not silent:
                messagebox.showerror("Erro", "Intervalo inválido. Use números inteiros e total maior que 0.")
            return None
        return total

    # ============================ INICIAR / PARAR ============================
    def toggle(self):
        self._stop() if self.engine.running else self._start()

    def _start(self):
        self.engine.use_positions = self.use_positions_var.get()
        if self.engine.use_positions:
            if not self.engine.positions:
                messagebox.showerror(
                    "Erro", "Nenhum ponto gravado.\nAbra Opções > Gravar múltiplos cliques."
                )
                return
        else:
            delay = self._read_interval()
            if delay is None:
                return
            self.engine.delay = delay
            self.engine.button = Button.left if self.button_var.get() == "Esquerdo" else Button.right

        self.engine.running = True
        self._set_button_running()

    def _stop(self):
        self.engine.running = False
        self._set_button_idle()

    # ============================ AJUDA / FECHAR ============================
    def show_help(self):
        messagebox.showinfo(
            "Ajuda",
            "Como usar:\n\n"
            "1. Em Opções > Configurações, defina o intervalo (H/M/S/MS),\n"
            "   o botão do mouse e a tecla de atalho.\n\n"
            "2. Pressione o atalho (padrão F6) ou o botão para iniciar/parar.\n\n"
            "Múltiplos cliques:\n"
            "- Abra Opções > Gravar múltiplos cliques.\n"
            "- Use 'Capturar ponto' e clique no alvo (cada ponto guarda o\n"
            "  intervalo definido no momento da captura).\n"
            "- Marque 'Gravar e repetir múltiplos cliques' e inicie.",
        )

    def on_close(self):
        self.engine.alive = False
        if self.listener:
            self.listener.stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()