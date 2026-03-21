import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import json
import os

# ── Importa pynput ───────────────────────────────────────────────────────────
try:
    from pynput.mouse import Button, Controller as MouseController
    from pynput.mouse import Listener as MouseListener
    from pynput import keyboard
    from pynput.keyboard import Key
    mouse = MouseController()
    PYNPUT_OK = True
except ImportError:
    PYNPUT_OK = False
    Key = None

# ── Arquivo de configurações ─────────────────────────────────────────────────
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

# ── Cores e fontes ───────────────────────────────────────────────────────────
BG      = "#0d0d0d"
PANEL   = "#141414"
ACCENT  = "#00ff88"
ACCENT2 = "#00ccff"
DANGER  = "#ff3355"
YELLOW  = "#ffcc00"
PURPLE  = "#bb88ff"
ORANGE  = "#ff9944"
TEXT    = "#e0e0e0"
MUTED   = "#555555"
FONT    = ("Consolas", 10)
FONT_SM = ("Consolas", 9)
FONT_XS = ("Consolas", 8)

# ── Estado global ─────────────────────────────────────────────────────────────
clicking              = False
click_thread          = None
click_count           = 0
current_hotkey        = "f6"   # hotkey iniciar/parar
hotkey_label          = "F6"
capturing_which       = None   # None | "main"  — qual hotkey está sendo capturada

# Captura de posição por clique
capturing_pos         = False
capture_target_x      = None
capture_target_y      = None
capture_target_btn    = None
pos_mouse_listener    = None

positions = []   # lista de dicts com widgets de cada linha


# ════════════════════════════════════════════════════════════════════════════
#  UTILITÁRIO — parse de segundos  ("1.5", "8", "0,5")
# ════════════════════════════════════════════════════════════════════════════

def parse_seconds(val, fallback=1.0):
    try:
        return max(0.0, float(str(val).replace(",", ".")))
    except ValueError:
        return fallback


# ════════════════════════════════════════════════════════════════════════════
#  LÓGICA DE CLIQUE
# ════════════════════════════════════════════════════════════════════════════

def get_active_positions():
    result = []
    for p in positions:
        if p["ativo"].get():
            try:
                x   = int(p["x"].get())
                y   = int(p["y"].get())
                sec = parse_seconds(p["delay"].get(), fallback=0.0)
            except Exception:
                x, y, sec = 0, 0, 0.0
            result.append((x, y, sec))
    return result


def do_click_at(btn, double, x, y):
    """Move o cursor para (x, y) e clica. O cursor fica lá."""
    mouse.position = (x, y)
    time.sleep(0.02)
    mouse.click(btn, 2 if double else 1)


def lock_mouse_to_app():
    """
    Retorna a posição (cx, cy) do centro da janela do app.
    Usamos isso para sempre reposicionar o cursor dentro da janela
    nos momentos em que o clicker não está visitando uma posição fixa,
    impedindo que o usuário arraste o mouse para outro lugar.
    """
    cx = root.winfo_rootx() + root.winfo_width()  // 2
    cy = root.winfo_rooty() + root.winfo_height() // 2
    return cx, cy


def click_loop(button, double, max_clicks, use_positions, global_interval_s):
    global clicking, click_count
    click_count = 0
    btn = Button.right if button == "Direito" else Button.left

    while clicking:
        app_cx, app_cy = lock_mouse_to_app()

        if use_positions:
            coords = get_active_positions()

            if not coords:
                # Nenhuma posição ativa: clica onde o mouse estiver
                mouse.click(btn, 2 if double else 1)
                click_count += 1
                root.after(0, update_counter)
                if max_clicks > 0 and click_count >= max_clicks:
                    break
                # Entre ciclos: prende o cursor na janela
                mouse.position = (app_cx, app_cy)
                _sleep_interruptible(global_interval_s)
            else:
                for (x, y, delay_s) in coords:
                    if not clicking:
                        break
                    # 1. Move para a posição e clica
                    do_click_at(btn, double, x, y)
                    click_count += 1
                    root.after(0, update_counter)
                    if max_clicks > 0 and click_count >= max_clicks:
                        clicking = False
                        break
                    # 2. Aguarda o delay DESTA posição (cursor fica lá durante a espera)
                    wait = delay_s if delay_s > 0 else global_interval_s
                    _sleep_interruptible(wait)

                if not clicking:
                    break
                # 3. Após completar todas as posições do ciclo, volta para o app
                mouse.position = (app_cx, app_cy)
        else:
            # Modo livre: clica onde o cursor está
            mouse.click(btn, 2 if double else 1)
            click_count += 1
            root.after(0, update_counter)
            if max_clicks > 0 and click_count >= max_clicks:
                break
            # Prende o cursor na janela entre cliques
            mouse.position = (app_cx, app_cy)
            _sleep_interruptible(global_interval_s)

    clicking = False
    root.after(0, _on_stop)


def _sleep_interruptible(seconds):
    """
    Dorme em fatias de 50 ms para poder parar rapidamente
    quando clicking = False (ex: usuário pressionou a hotkey).
    """
    end = time.time() + seconds
    while clicking and time.time() < end:
        time.sleep(0.05)


def _on_stop():
    btn_toggle.config(text="▶  INICIAR", bg=ACCENT, fg=BG)
    status_var.set("■  Parado")


def toggle_clicking():
    global clicking, click_thread, click_count

    if not PYNPUT_OK:
        messagebox.showerror("Erro", "pynput não instalado!\nRode: pip install pynput")
        return

    if clicking:
        clicking = False
        return

    # ── Lê intervalo global ──────────────────────────────────────────────────
    try:
        h  = int(entry_h.get()  or 0)
        m  = int(entry_m.get()  or 0)
        s  = int(entry_s.get()  or 0)
        ms = int(entry_ms.get() or 100)
        global_interval_ms = (h * 3600 + m * 60 + s) * 1000 + ms
        if global_interval_ms <= 0:
            messagebox.showwarning("Aviso", "Intervalo deve ser maior que 0")
            return
        global_interval_s = global_interval_ms / 1000.0
        max_clicks = int(entry_max.get() or 0)
    except ValueError:
        messagebox.showerror("Erro", "Campos de tempo devem ser números")
        return

    use_positions = coords_var.get()
    button        = btn_type_var.get()
    double        = double_var.get()
    click_count   = 0
    update_counter()

    clicking = True
    btn_toggle.config(text="■  PARAR", bg=DANGER, fg="#ffffff")
    n    = len([p for p in positions if p["ativo"].get()])
    info = f" ({n} pos.)" if use_positions else ""
    status_var.set(f"● Clicando{info}...")

    click_thread = threading.Thread(
        target=click_loop,
        args=(button, double, max_clicks, use_positions, global_interval_s),
        daemon=True
    )
    click_thread.start()


def update_counter():
    lbl_count.config(text=str(click_count))


# ════════════════════════════════════════════════════════════════════════════
#  CAPTURA DE POSIÇÃO POR CLIQUE DO MOUSE
# ════════════════════════════════════════════════════════════════════════════

def start_pos_capture(ex, ey, btn_c):
    global capturing_pos, capture_target_x, capture_target_y
    global capture_target_btn, pos_mouse_listener

    if capturing_pos:
        return  # já capturando outra

    capturing_pos      = True
    capture_target_x   = ex
    capture_target_y   = ey
    capture_target_btn = btn_c
    btn_c.config(text="🖱 Clique!", bg="#332200")
    status_var.set("🎯 Clique em qualquer lugar para capturar a posição...")

    def on_click(x, y, button, pressed):
        if pressed:
            root.after(0, lambda: _finish_pos_capture(int(x), int(y)))
            return False  # encerra o listener

    if PYNPUT_OK:
        pos_mouse_listener = MouseListener(on_click=on_click)
        pos_mouse_listener.start()


def _finish_pos_capture(x, y):
    global capturing_pos, pos_mouse_listener

    capturing_pos = False
    capture_target_x.delete(0, tk.END)
    capture_target_x.insert(0, str(x))
    capture_target_y.delete(0, tk.END)
    capture_target_y.insert(0, str(y))
    capture_target_btn.config(text="📍", bg="#1e1e1e")
    status_var.set("■  Parado")

    if pos_mouse_listener:
        try:
            pos_mouse_listener.stop()
        except Exception:
            pass
        pos_mouse_listener = None


# ════════════════════════════════════════════════════════════════════════════
#  GERENCIAR POSIÇÕES
# ════════════════════════════════════════════════════════════════════════════

def add_position(x=0, y=0, delay=1.0, ativo=True):
    idx = len(positions)

    row = tk.Frame(positions_frame, bg=PANEL)
    row.pack(fill="x", pady=3)

    # Número
    lbl_num = tk.Label(row, text=f"#{idx+1}", bg=PANEL, fg=MUTED,
                       font=FONT_XS, width=3, anchor="w")
    lbl_num.pack(side="left")

    # Checkbox ativo
    ativo_var = tk.BooleanVar(value=ativo)
    ttk.Checkbutton(row, variable=ativo_var, style="C.TCheckbutton").pack(side="left")

    # X
    tk.Label(row, text="X", bg=PANEL, fg=YELLOW, font=FONT_XS).pack(side="left", padx=(6,1))
    entry_xi = tk.Entry(row, width=5, font=FONT, bg="#1a1a1a", fg=YELLOW,
                        insertbackground=YELLOW, relief="flat", bd=0,
                        highlightthickness=1, highlightcolor=YELLOW,
                        highlightbackground=MUTED, justify="center")
    entry_xi.insert(0, str(x))
    entry_xi.pack(side="left", padx=(0,4))

    # Y
    tk.Label(row, text="Y", bg=PANEL, fg=YELLOW, font=FONT_XS).pack(side="left", padx=(0,1))
    entry_yi = tk.Entry(row, width=5, font=FONT, bg="#1a1a1a", fg=YELLOW,
                        insertbackground=YELLOW, relief="flat", bd=0,
                        highlightthickness=1, highlightcolor=YELLOW,
                        highlightbackground=MUTED, justify="center")
    entry_yi.insert(0, str(y))
    entry_yi.pack(side="left", padx=(0,6))

    # Delay em SEGUNDOS
    tk.Label(row, text="⏱", bg=PANEL, fg=ORANGE, font=FONT_XS).pack(side="left", padx=(0,1))
    entry_delay = tk.Entry(row, width=5, font=FONT, bg="#1a1a1a", fg=ORANGE,
                           insertbackground=ORANGE, relief="flat", bd=0,
                           highlightthickness=1, highlightcolor=ORANGE,
                           highlightbackground=MUTED, justify="center")
    entry_delay.insert(0, str(delay))
    entry_delay.pack(side="left", padx=(0,2))
    tk.Label(row, text="s", bg=PANEL, fg=MUTED, font=FONT_XS).pack(side="left", padx=(0,6))

    # Botão capturar
    btn_c = tk.Button(row, text="📍", font=FONT_XS, bg="#1e1e1e", fg=YELLOW,
                      relief="flat", bd=0, padx=5, pady=2, cursor="hand2")
    btn_c.config(command=lambda: start_pos_capture(entry_xi, entry_yi, btn_c))
    btn_c.pack(side="left", padx=(0,4))

    # Botão remover
    ref = {}

    def remove_this():
        positions.remove(ref["self"])
        row.destroy()
        _renumber()

    tk.Button(row, text="✕", font=FONT_XS, bg="#1e1e1e", fg=DANGER,
              relief="flat", bd=0, padx=5, pady=2,
              cursor="hand2", command=remove_this).pack(side="left")

    entry = {
        "x": entry_xi, "y": entry_yi,
        "delay": entry_delay,
        "ativo": ativo_var,
        "row": row, "lbl_num": lbl_num,
    }
    ref["self"] = entry
    positions.append(entry)


def _renumber():
    for i, p in enumerate(positions):
        p["lbl_num"].config(text=f"#{i+1}")


def toggle_coords_section(*_):
    state = "normal" if coords_var.get() else "disabled"
    btn_add_pos.config(state=state)
    for p in positions:
        p["x"].config(state=state)
        p["y"].config(state=state)
        p["delay"].config(state=state)


# ════════════════════════════════════════════════════════════════════════════
#  HOTKEY CONFIGURÁVEL  (única hotkey: iniciar/parar)
# ════════════════════════════════════════════════════════════════════════════

SPECIAL = {}
if PYNPUT_OK and Key:
    SPECIAL = {
        "f1":Key.f1,"f2":Key.f2,"f3":Key.f3,"f4":Key.f4,
        "f5":Key.f5,"f6":Key.f6,"f7":Key.f7,"f8":Key.f8,
        "f9":Key.f9,"f10":Key.f10,"f11":Key.f11,"f12":Key.f12,
        "esc":Key.esc,"tab":Key.tab,"space":Key.space,
        "insert":Key.insert,"home":Key.home,"end":Key.end,
        "page_up":Key.page_up,"page_down":Key.page_down,
    }


def _key_name(key):
    """Extrai o nome/char de uma tecla pressionada."""
    if hasattr(key, "char") and key.char:
        return key.char.lower(), key.char.upper()
    if hasattr(key, "name") and key.name:
        return key.name.lower(), key.name.upper()
    return None, None


def setup_hotkey():
    if not PYNPUT_OK:
        return

    def on_press(key):
        global capturing_which, current_hotkey, hotkey_label

        # ── Modo captura de hotkey ────────────────────────────────────────────
        if capturing_which == "main":
            k_low, k_up = _key_name(key)
            if k_low:
                current_hotkey = k_low
                hotkey_label   = k_up
                root.after(0, lambda: lbl_hotkey_val.config(text=f"[{k_up}]"))
                root.after(0, lambda: btn_set_hotkey.config(
                    text="🎮 Alterar", state="normal"))
            capturing_which = None
            return

        # ── Disparo normal ───────────────────────────────────────────────────
        if capturing_pos:
            return  # não dispara enquanto captura posição

        k_low = current_hotkey.lower()
        matched = False
        if k_low in SPECIAL:
            matched = (key == SPECIAL[k_low])
        elif hasattr(key, "char") and key.char:
            matched = (key.char.lower() == k_low)

        if matched:
            root.after(0, toggle_clicking)

    listener = keyboard.Listener(on_press=on_press)
    listener.daemon = True
    listener.start()


def start_hotkey_capture(which):
    global capturing_which
    capturing_which = which
    if which == "main":
        btn_set_hotkey.config(text="Pressione uma tecla...", state="disabled")
        lbl_hotkey_val.config(text="[...]")


# ════════════════════════════════════════════════════════════════════════════
#  SALVAR / CARREGAR CONFIG
# ════════════════════════════════════════════════════════════════════════════

def get_config():
    return {
        "h": entry_h.get(), "m": entry_m.get(),
        "s": entry_s.get(), "ms": entry_ms.get(),
        "max_clicks":   entry_max.get(),
        "button":       btn_type_var.get(),
        "double":       double_var.get(),
        "use_coords":   coords_var.get(),
        "hotkey":       current_hotkey,
        "hotkey_label": hotkey_label,
        "positions": [
            {
                "x":     p["x"].get(),
                "y":     p["y"].get(),
                "delay": p["delay"].get(),
                "ativo": p["ativo"].get(),
            }
            for p in positions
        ],
    }


def apply_config(cfg):
    global current_hotkey, hotkey_label

    def se(e, v):
        e.delete(0, tk.END); e.insert(0, str(v))

    se(entry_h,   cfg.get("h",   "0"))
    se(entry_m,   cfg.get("m",   "0"))
    se(entry_s,   cfg.get("s",   "0"))
    se(entry_ms,  cfg.get("ms",  "100"))
    se(entry_max, cfg.get("max_clicks", "0"))

    btn_type_var.set(cfg.get("button", "Esquerdo"))
    double_var.set(cfg.get("double", False))
    coords_var.set(cfg.get("use_coords", False))
    toggle_coords_section()

    current_hotkey = cfg.get("hotkey", "f6")
    hotkey_label   = cfg.get("hotkey_label", "F6")
    lbl_hotkey_val.config(text=f"[{hotkey_label}]")

    for p in list(positions):
        p["row"].destroy()
    positions.clear()

    for pos in cfg.get("positions", []):
        add_position(
            pos.get("x", 0), pos.get("y", 0),
            pos.get("delay", 1.0), pos.get("ativo", True)
        )


def save_config():
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(get_config(), f, indent=2, ensure_ascii=False)
        status_var.set("✔  Configuração salva!")
        root.after(2000, lambda: status_var.set("■  Parado"))
    except Exception as e:
        messagebox.showerror("Erro ao salvar", str(e))


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            apply_config(json.load(f))
    except Exception:
        pass


# ════════════════════════════════════════════════════════════════════════════
#  JANELA PRINCIPAL
# ════════════════════════════════════════════════════════════════════════════
root = tk.Tk()
root.title("Auto Clicker")
root.geometry("460x730")
root.resizable(False, False)
root.configure(bg=BG)
root.option_add("*tearOff", False)

# ── Canvas com scroll ────────────────────────────────────────────────────────
canvas    = tk.Canvas(root, bg=BG, highlightthickness=0)
scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
canvas.configure(yscrollcommand=scrollbar.set)
scrollbar.pack(side="right", fill="y")
canvas.pack(side="left", fill="both", expand=True)

inner     = tk.Frame(canvas, bg=BG)
inner_win = canvas.create_window((0, 0), window=inner, anchor="nw")

inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
canvas.bind("<Configure>", lambda e: canvas.itemconfig(inner_win, width=e.width))
canvas.bind_all("<MouseWheel>",
                lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

# ── Estilos ──────────────────────────────────────────────────────────────────
style = ttk.Style()
style.theme_use("clam")
style.configure("C.TRadiobutton", background=PANEL, foreground=TEXT,
                font=FONT, indicatorcolor=ACCENT, focuscolor=PANEL)
style.configure("C.TCheckbutton", background=PANEL, foreground=TEXT,
                font=FONT, indicatorcolor=ACCENT, focuscolor=PANEL)


def section(parent, title):
    f = tk.Frame(parent, bg=PANEL, padx=14, pady=10)
    f.pack(fill="x", padx=12, pady=(0, 8))
    tk.Label(f, text=title, bg=PANEL, fg=MUTED, font=FONT_SM).pack(anchor="w", pady=(0, 6))
    return f


def make_entry(parent, width=5, default="0", fg=ACCENT):
    e = tk.Entry(parent, width=width, font=FONT, bg="#1a1a1a", fg=fg,
                 insertbackground=fg, relief="flat", bd=0,
                 highlightthickness=1, highlightcolor=fg,
                 highlightbackground=MUTED, justify="center")
    e.insert(0, default)
    return e


# ════════════════════════════════════════════════════════════════════════════
#  HEADER
# ════════════════════════════════════════════════════════════════════════════
header = tk.Frame(inner, bg=BG, pady=14)
header.pack(fill="x")
tk.Label(header, text="⚡ AUTO CLICKER", font=("Consolas", 16, "bold"),
         bg=BG, fg=ACCENT).pack()

# Hotkey iniciar/parar
row_hk = tk.Frame(header, bg=BG)
row_hk.pack(pady=(6, 0))
tk.Label(row_hk, text="Hotkey iniciar/parar:",
         bg=BG, fg=MUTED, font=FONT_SM).pack(side="left", padx=(0, 4))
lbl_hotkey_val = tk.Label(row_hk, text="[F6]", bg=BG, fg=PURPLE,
                           font=("Consolas", 9, "bold"))
lbl_hotkey_val.pack(side="left", padx=(0, 8))
btn_set_hotkey = tk.Button(row_hk, text="🎮 Alterar",
                           font=FONT_SM, bg="#1e1e1e", fg=PURPLE,
                           relief="flat", bd=0, padx=8, pady=3,
                           cursor="hand2",
                           command=lambda: start_hotkey_capture("main"))
btn_set_hotkey.pack(side="left")

tk.Frame(inner, height=1, bg=ACCENT).pack(fill="x", padx=12, pady=(8, 10))

# ════════════════════════════════════════════════════════════════════════════
#  INTERVALO PADRÃO
# ════════════════════════════════════════════════════════════════════════════
sec_interval = section(inner, "INTERVALO PADRÃO ENTRE CLIQUES")
row_time = tk.Frame(sec_interval, bg=PANEL)
row_time.pack(fill="x")

for label, default in [("H", "0"), ("M", "0"), ("S", "0"), ("MS", "100")]:
    col = tk.Frame(row_time, bg=PANEL)
    col.pack(side="left", expand=True)
    tk.Label(col, text=label, bg=PANEL, fg=MUTED, font=FONT_SM).pack()
    e = make_entry(col, width=5, default=default)
    e.pack(pady=2)
    globals()[f"entry_{label.lower()}"] = e

tk.Label(sec_interval,
         text="Usado no modo livre ou como fallback quando delay da posição é 0.",
         bg=PANEL, fg=MUTED, font=FONT_XS, wraplength=400, justify="left"
         ).pack(anchor="w", pady=(6, 0))

# ════════════════════════════════════════════════════════════════════════════
#  TIPO DE CLIQUE
# ════════════════════════════════════════════════════════════════════════════
sec_type     = section(inner, "TIPO DE CLIQUE")
btn_type_var = tk.StringVar(value="Esquerdo")
double_var   = tk.BooleanVar(value=False)

row_type = tk.Frame(sec_type, bg=PANEL)
row_type.pack(fill="x")
for lbl in ["Esquerdo", "Direito"]:
    ttk.Radiobutton(row_type, text=lbl, variable=btn_type_var,
                    value=lbl, style="C.TRadiobutton").pack(side="left", padx=10)
ttk.Checkbutton(sec_type, text="Clique duplo", variable=double_var,
                style="C.TCheckbutton").pack(anchor="w", pady=(6, 0))

# ════════════════════════════════════════════════════════════════════════════
#  LIMITE DE CLIQUES
# ════════════════════════════════════════════════════════════════════════════
sec_max   = section(inner, "LIMITE DE CLIQUES  (0 = ilimitado)")
entry_max = make_entry(sec_max, width=10, default="0")
entry_max.pack(anchor="w")

# ════════════════════════════════════════════════════════════════════════════
#  POSIÇÕES FIXAS
# ════════════════════════════════════════════════════════════════════════════
sec_coords = section(inner, "POSIÇÕES FIXAS")

# Checkbox + descrição do modo
row_cv = tk.Frame(sec_coords, bg=PANEL)
row_cv.pack(fill="x")
coords_var = tk.BooleanVar(value=False)
ttk.Checkbutton(row_cv, text="Ativar posições fixas",
                variable=coords_var, style="C.TCheckbutton",
                command=toggle_coords_section).pack(side="left")
tk.Label(row_cv, text="  ← a mesma hotkey inicia/para neste modo também",
         bg=PANEL, fg=MUTED, font=FONT_XS).pack(side="left")

# Legenda colunas
legend = tk.Frame(sec_coords, bg=PANEL)
legend.pack(fill="x", pady=(10, 2))
for txt, fg_c in [("#  ✓", MUTED), ("  X / Y", YELLOW),
                  ("  ⏱ seg após clicar", ORANGE), ("  📍  ✕", MUTED)]:
    tk.Label(legend, text=txt, bg=PANEL, fg=fg_c, font=FONT_XS).pack(side="left", padx=2)
tk.Frame(sec_coords, height=1, bg="#222222").pack(fill="x", pady=(2, 6))

positions_frame = tk.Frame(sec_coords, bg=PANEL)
positions_frame.pack(fill="x")

btn_add_pos = tk.Button(
    sec_coords, text="＋ Adicionar posição",
    font=FONT_SM, bg="#1e1e1e", fg=ACCENT,
    activebackground="#2a2a2a", activeforeground=ACCENT,
    relief="flat", bd=0, padx=10, pady=5,
    cursor="hand2", state="disabled",
    command=lambda: add_position()
)
btn_add_pos.pack(anchor="w", pady=(8, 0))

tk.Label(sec_coords,
         text="📍 clique no botão → clique na tela para capturar.  "
              "⏱ segundos de espera antes de ir para a próxima posição.",
         bg=PANEL, fg=MUTED, font=FONT_XS, wraplength=420, justify="left"
         ).pack(anchor="w", pady=(6, 0))

# ════════════════════════════════════════════════════════════════════════════
#  CONTADOR + STATUS + BOTÕES
# ════════════════════════════════════════════════════════════════════════════
sec_count = section(inner, "CLIQUES REALIZADOS")
lbl_count = tk.Label(sec_count, text="0", font=("Consolas", 28, "bold"),
                     bg=PANEL, fg=ACCENT2)
lbl_count.pack()

status_var = tk.StringVar(value="■  Parado")
tk.Label(inner, textvariable=status_var, font=FONT_SM,
         bg=BG, fg=MUTED).pack(pady=(0, 4))

btn_toggle = tk.Button(
    inner, text="▶  INICIAR",
    font=("Consolas", 12, "bold"),
    bg=ACCENT, fg=BG,
    activebackground="#00cc70", activeforeground=BG,
    relief="flat", bd=0, padx=30, pady=10,
    cursor="hand2", command=toggle_clicking
)
btn_toggle.pack(pady=4)

row_save = tk.Frame(inner, bg=BG)
row_save.pack(pady=(4, 16))
tk.Button(row_save, text="💾 Salvar config", font=FONT_SM, bg="#1e1e1e", fg=ACCENT2,
          relief="flat", bd=0, padx=12, pady=6, cursor="hand2",
          command=save_config).pack(side="left", padx=6)
tk.Button(row_save, text="📂 Carregar config", font=FONT_SM, bg="#1e1e1e", fg=ACCENT2,
          relief="flat", bd=0, padx=12, pady=6, cursor="hand2",
          command=load_config).pack(side="left", padx=6)

if not PYNPUT_OK:
    tk.Label(inner, text="⚠ pynput não encontrado. Rode: pip install pynput",
             font=FONT_SM, bg=BG, fg=DANGER, wraplength=420).pack(pady=4)

# ════════════════════════════════════════════════════════════════════════════
#  INICIALIZAÇÃO
# ════════════════════════════════════════════════════════════════════════════
setup_hotkey()
load_config()
root.mainloop()