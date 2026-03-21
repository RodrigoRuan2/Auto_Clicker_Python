# ⚡ Auto Clicker Configurável

Auto clicker feito em Python com interface gráfica.

## Funcionalidades
- Intervalo configurável (H/M/S/MS)
- Múltiplas posições fixas com delay individual por posição
- Captura de posição por clique
- Hotkey global configurável
- Salva e carrega configurações automaticamente

## Como usar
```bash
pip install pynput
python auto_clicker.py
```

## Gerar .exe
```bash
python -m PyInstaller --onefile --noconsole auto_clicker.py
```
