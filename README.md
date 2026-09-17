# SkyLine Safe: Mestre da Altura

Simulador 2.5D de inspeção e manutenção em altura, feito em Python + Pygame.

## Instalação

```bash
pip install pygame
python skyline_safe.py
```

No VS Code: abra a pasta `skyline_safe`, selecione o interpretador Python e rode `skyline_safe.py` (F5). Se usar ambiente virtual:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate
pip install -r requirements.txt
python skyline_safe.py
```

## Controles

| Tecla | Ação |
|---|---|
| `A` / `D` ou setas | deslocar na horizontal sobre as vigas |
| `W` / `S` | subir e descer nos montantes |
| `1` | ancorar / liberar o gancho 1 (verde) |
| `2` | ancorar / liberar o gancho 2 (azul) |
| `CTRL` | agachar e firmar o corpo durante rajadas |
| `E` | iniciar tarefa na estação de manutenção |
| `R` | iniciar resgate do colega suspenso |
| `TAB` | abrir a ordem de serviço |
| `ESC` | pausa (com `Q` abandona a missão) |
| `F1` | tela cheia |

## Regra de ouro do talabarte duplo

Para avançar: ancore o gancho livre no próximo ponto, **depois** libere o gancho de trás. O jogo **permite** você soltar os dois — mas mover-se fora do solo sem nenhuma ancoragem encerra a missão imediatamente.

## Sistemas implementados

- **Pré-check de EPI** — 6 itens sorteados por missão, laudo de inspeção com 4 pontos cada, decisão aprovar/descartar. Aprovar item danificado provoca falha do equipamento em serviço (gancho inutilizado, trava-quedas que não bloqueia etc.). Descartar item bom custa tempo e pontos.
- **Física de ancoragem** — talabarte com comprimento útil limitado (`CABO_MAX`); o movimento trava quando a corda tensiona, forçando a alternância dos ganchos.
- **Clima dinâmico** — rajadas que sobem e descem, anemômetro analógico, limite regulamentar de 11 m/s, abrigos marcados no mapa, medidor de equilíbrio e queda contida pelo talabarte.
- **Manutenção** — 4 minijogos: solda de reforço, torque de parafusos (com sub/sobretorque e parafuso espanado), troca de lâmpada de balizamento com sequência LOTO, e ensaio de soldas por líquido penetrante.
- **Resgate em altura** — colega suspenso com contagem regressiva de trauma por suspensão e descida controlada com faixa de velocidade segura.
- **Relatório final** — pontuação de segurança, auditoria do pré-check item a item e registro cronológico de infrações, com classificação ouro/prata/bronze.
- **Modos** — Carreira com 5 obras progressivas (progresso salvo em `skyline_save.json`) e Desafio VR de sprint de ancoragem contra o relógio.

## Ajuste de dificuldade

As constantes no topo do arquivo controlam o balanceamento:

```python
CABO_MAX = 185.0        # comprimento útil do talabarte
RAIO_ANCORAGEM = 200.0  # alcance do braço
LIMITE_VENTO = 11.0     # m/s antes da interrupção obrigatória
ESCALA_METRO = 22.0     # pixels por metro
TEMPO_TRAUMA = 150.0    # segundos até o trauma por suspensão
```

Novas obras são adicionadas à lista `NIVEIS`: basta definir o tamanho da treliça (`cols`, `linhas`, `sx`, `sy`), o perfil de vento, as coordenadas `(coluna, linha)` das tarefas, do resgate e dos abrigos.

## Estrutura do código

| Seção | Conteúdo |
|---|---|
| 1–2 | configuração, paleta e utilitários de desenho |
| 3 | catálogo de EPIs e geração do kit com defeitos |
| 4 | `Estrutura` (grafo de vigas percorríveis) e definição dos níveis |
| 5 | minijogos de manutenção e resgate |
| 6 | `Jogador` (movimento no grafo, ganchos, tensionamento) |
| 7 | cenas: menu, ajuda, seleção, pré-check, jogo, relatório |
| 8 | `App`, persistência e loop principal |

## Observações

O jogo desenha tudo com primitivas do Pygame — não há dependência de assets externos. Para a versão VR/3D descrita no conceito original, esta base serve como protótipo de mecânicas: as regras de ancoragem, o modelo de vento e o sistema de infrações são independentes da renderização.
