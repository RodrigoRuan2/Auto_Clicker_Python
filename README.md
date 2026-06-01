# Auto Clicker

Auto clicker compacto janela principal minima
e configuracoes em pequenas janelas separadas.

## Janela principal

So um botao grande: "Pressione F6 para clicar". Tudo o mais fica no menu **Opções**.

## Menu Opções

**Configurações...**
- Intervalo entre cliques em H / M / S / MS
- Botao do mouse (esquerdo / direito)
- Atalho global configuravel (padrao F6) — botao "Alterar"

**Gravar multiplos cliques...** (modo varios pontos)
- "Capturar ponto": clique no botao e depois clique no alvo na tela
- Lista dos pontos gravados (com X, Y e delay) + Remover / Limpar
- Marque "Gravar e repetir multiplos cliques" para usar a lista
- Cada ponto guarda o intervalo definido **no momento da captura**

## Como rodar (desenvolvimento)

```bash
pip install -r requirements.txt
python auto_clicker.py
```

## Gerar o executavel (.exe no Windows)

> Rode no proprio Windows, com o AutoClicker.ico na mesma pasta.

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "AutoClicker" --icon "AutoClicker.ico" --add-data "AutoClicker.ico;." auto_clicker.py
```

Saida em `dist/AutoClicker.exe`.

## Estrutura

```
auto-clicker/
├── auto_clicker.py      # interface + logica de clique
├── AutoClicker.ico      # icone do app
├── requirements.txt     # dependencias (pynput)
└── README.md            # este arquivo
```

## Ideias de melhoria (proximos passos)

- [ ] Editar o delay de um ponto ja gravado (sem recapturar)
- [ ] Reordenar pontos na lista
- [ ] Modo "numero fixo de cliques" (ex: 100 e para)
- [ ] Salvar / carregar configuracoes em config.json
- [ ] Contador de cliques em tempo real
