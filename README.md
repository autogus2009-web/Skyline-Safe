# SkyLine Safe: Mestre da Altura (v2, Obra 01)

Simulador 2.5D de inspeção e manutenção em altura, em Python + Pygame. Esta versão tem **uma fase completa** (Obra 01) e o Desafio VR. As próximas obras entram depois.

## Instalação

```powershell
py -m pip install pygame
py skyline_safe.py
```

No Linux/macOS use `python3`. Se `python` não for reconhecido no Windows, use `py` ou instale o Python em python.org marcando "Add python.exe to PATH".

## Controles

| Tecla | Ação |
|---|---|
| `A` / `D` ou setas | mover na horizontal |
| `W` / `S` | subir e descer |
| `1` / `2` | ancorar ou liberar o gancho 1 (verde) / gancho 2 (azul) |
| `W A S D` ao ancorar | mira o gancho; o anel branco mostra onde ele prende |
| `CTRL` | agachar e firmar o corpo |
| `E` | iniciar tarefa na estação |
| `R` | iniciar resgate |
| `TAB` | ordem de serviço |
| `M` | liga/desliga o som |
| `ESC` | pausa (`Q` abandona) |
| `F1` | tela cheia |

## O que tem na Obra 01

- **Pré-check físico:** lupa com 4 pontos clicáveis (ou teclas 1–4) por EPI. Só dá para aprovar ou descartar depois de inspecionar os 4. Capacete, cinturão, fita de ancoragem, trava-quedas e talabarte sempre aparecem no kit. Demorar mais de 1m30 no pré-check desconta tempo da obra.
- **Talabarte duplo:** a corda tem limite e trava o movimento. Sem nenhum gancho fora do solo, a missão falha.
- **Pontos de ancoragem corroidos:** marrons com X. Ancorar neles gera infração e o gancho cede em 3 s.
- **Clima:** anemômetro, rajadas, abrigos, balanço do personagem e tela tremendo acima do limite de 11 m/s.
- **Tarefas:** solda, torque de parafusos e troca de lâmpada (sequência LOTO).
- **Resgate:** procedimento em 5 passos (1–5) e depois descida controlada, com a contagem de trauma por suspensão correndo.
- **Cada infração** custa pontos e 3 segundos.
- **Relatório:** auditoria do pré-check, infrações e lições da NR-35 ligadas aos seus erros.
- **Som:** efeitos e trilhas gerados por código, sem arquivos externos. A música muda com vento forte, pouco tempo e resgate.
- **Desafio VR:** prazo por alvo, combo até x5, -5 s quando o alvo expira.

## Adicionando novas obras

1. Em `NIVEIS`, copie o modelo comentado e ajuste tamanho, vento, tarefas, resgate e abrigos.
2. Para um visual novo, descomente/crie uma entrada em `TEMAS` e um ramo em `CenaJogo.desenhar_tema()`.
3. A seleção de obras e o "Próxima obra" aparecem sozinhos quando houver mais de uma.
