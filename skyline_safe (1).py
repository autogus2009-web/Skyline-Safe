# -*- coding: utf-8 -*-
"""
===============================================================================
 SKYLINE SAFE: MESTRE DA ALTURA
 Simulacao de Acao / Puzzle de trabalho em altura
 -----------------------------------------------------------------------------
 Requisitos:  Python 3.9+   |   pip install pygame
 Executar:    python skyline_safe.py
===============================================================================
 MECANICAS IMPLEMENTADAS
   * Talabarte duplo  : dois ganchos independentes, alternancia obrigatoria na
                        linha de vida. Mover-se com os dois desconectados fora
                        do solo = falha imediata da missao.
   * Pre-check de EPI : inspecao item a item, aprovar ou descartar. Aprovar um
                        equipamento danificado provoca falha do EPI durante a
                        missao.
   * Clima dinamico   : rajadas de vento, anemometro em tempo real, medidor de
                        equilibrio, abrigos seguros.
   * Manutencao       : minijogos de solda, troca de lampada de balizamento e
                        torque de parafusos.
   * Resgate          : evacuacao de colega suspenso com controle de descida e
                        contagem regressiva de trauma por suspensao.
   * Modos            : Carreira (5 obras) e Desafio VR (ancoragem por tempo).
===============================================================================
"""

import json
import math
import os
import random
import sys

import pygame
from pygame import Vector2

# =============================================================================
# 1. CONFIGURACAO GERAL
# =============================================================================

LARGURA, ALTURA = 1280, 720
FPS = 60
TITULO = "SkyLine Safe: Mestre da Altura"

ARQUIVO_SAVE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skyline_save.json")

# --- Regras de seguranca (parametros de jogo inspirados em normas de altura) --
CABO_MAX = 185.0          # comprimento util do talabarte (px)
RAIO_ANCORAGEM = 200.0    # alcance do braco para encaixar o gancho (px)
LIMITE_VENTO = 11.0       # m/s -> acima disso a atividade deve ser interrompida
ALTURA_MIN_SEGURA = 2.0   # metros; abaixo disso nao ha risco de queda
ESCALA_METRO = 22.0       # px por metro (para converter altura em metros)
TEMPO_TRAUMA = 150.0      # segundos ate o trauma por suspensao do colega

# --- Paleta --------------------------------------------------------------
C_FUNDO_TOPO   = (26, 38, 58)
C_FUNDO_BASE   = (92, 122, 150)
C_ACO          = (118, 128, 140)
C_ACO_ESC      = (72, 80, 92)
C_ACO_LUZ      = (166, 176, 188)
C_PAINEL       = (18, 24, 34)
C_PAINEL_BORDA = (58, 72, 92)
C_TEXTO        = (232, 238, 245)
C_TEXTO_FRACO  = (150, 164, 182)
C_AMARELO      = (247, 196, 40)
C_LARANJA      = (240, 132, 42)
C_VERDE        = (86, 196, 118)
C_VERMELHO     = (222, 72, 72)
C_AZUL         = (78, 158, 226)
C_BRANCO       = (255, 255, 255)
C_PRETO        = (0, 0, 0)

FONTES = {}


def carregar_fontes():
    """Carrega fontes do sistema com varios nomes alternativos."""
    nomes = "consolas,dejavusansmono,couriernew,monospace"
    nomes_ui = "verdana,dejavusans,arial,freesans"
    FONTES["mono"] = pygame.font.SysFont(nomes, 16)
    FONTES["mono_p"] = pygame.font.SysFont(nomes, 13)
    FONTES["ui"] = pygame.font.SysFont(nomes_ui, 17)
    FONTES["ui_p"] = pygame.font.SysFont(nomes_ui, 14)
    FONTES["ui_g"] = pygame.font.SysFont(nomes_ui, 22, bold=True)
    FONTES["titulo"] = pygame.font.SysFont(nomes_ui, 44, bold=True)
    FONTES["sub"] = pygame.font.SysFont(nomes_ui, 26, bold=True)
    FONTES["hud"] = pygame.font.SysFont(nomes, 15, bold=True)


# =============================================================================
# 2. UTILIDADES DE DESENHO
# =============================================================================

def texto(surf, msg, pos, fonte="ui", cor=C_TEXTO, centro=False, direita=False, sombra=False):
    img = FONTES[fonte].render(str(msg), True, cor)
    r = img.get_rect()
    if centro:
        r.center = pos
    elif direita:
        r.midright = pos
    else:
        r.topleft = pos
    if sombra:
        s = FONTES[fonte].render(str(msg), True, (0, 0, 0))
        surf.blit(s, (r.x + 2, r.y + 2))
    surf.blit(img, r)
    return r


def quebrar_texto(msg, fonte, largura_max):
    palavras = str(msg).split(" ")
    linhas, atual = [], ""
    for p in palavras:
        teste = (atual + " " + p).strip()
        if FONTES[fonte].size(teste)[0] <= largura_max:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas


def texto_bloco(surf, msg, pos, largura_max, fonte="ui_p", cor=C_TEXTO, espaco=4):
    x, y = pos
    for linha in quebrar_texto(msg, fonte, largura_max):
        texto(surf, linha, (x, y), fonte, cor)
        y += FONTES[fonte].get_height() + espaco
    return y


def painel(surf, rect, cor=C_PAINEL, borda=C_PAINEL_BORDA, alpha=235, raio=10, larg_borda=2):
    rect = pygame.Rect(rect)
    s = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(s, (*cor, alpha), s.get_rect(), border_radius=raio)
    surf.blit(s, rect.topleft)
    pygame.draw.rect(surf, borda, rect, larg_borda, border_radius=raio)


def barra(surf, rect, frac, cor, fundo=(40, 48, 60), borda=C_PAINEL_BORDA, raio=4):
    rect = pygame.Rect(rect)
    frac = max(0.0, min(1.0, frac))
    pygame.draw.rect(surf, fundo, rect, border_radius=raio)
    if frac > 0:
        r = pygame.Rect(rect.x, rect.y, max(3, int(rect.w * frac)), rect.h)
        pygame.draw.rect(surf, cor, r, border_radius=raio)
    pygame.draw.rect(surf, borda, rect, 1, border_radius=raio)


def gradiente_vertical(surf, rect, cor_topo, cor_base):
    rect = pygame.Rect(rect)
    for i in range(rect.h):
        t = i / max(1, rect.h - 1)
        c = (int(cor_topo[0] + (cor_base[0] - cor_topo[0]) * t),
             int(cor_topo[1] + (cor_base[1] - cor_topo[1]) * t),
             int(cor_topo[2] + (cor_base[2] - cor_topo[2]) * t))
        pygame.draw.line(surf, c, (rect.x, rect.y + i), (rect.right, rect.y + i))


def desenhar_cabo(surf, p1, p2, cor, sag=18, espessura=3):
    """Desenha um talabarte com catenaria (barriga) entre dois pontos."""
    p1, p2 = Vector2(p1), Vector2(p2)
    dist = p1.distance_to(p2)
    barriga = sag * max(0.15, 1.0 - dist / (CABO_MAX + 1.0))
    meio = (p1 + p2) / 2 + Vector2(0, barriga * 4)
    pts = []
    for i in range(15):
        t = i / 14.0
        a = p1 * (1 - t) ** 2 + meio * 2 * (1 - t) * t + p2 * t ** 2
        pts.append((a.x, a.y))
    pygame.draw.lines(surf, (0, 0, 0), False, pts, espessura + 2)
    pygame.draw.lines(surf, cor, False, pts, espessura)


class Botao:
    def __init__(self, rect, rotulo, tecla=None, cor=C_AZUL):
        self.rect = pygame.Rect(rect)
        self.rotulo = rotulo
        self.tecla = tecla
        self.cor = cor
        self.hover = False

    def atualizar(self, mpos):
        self.hover = self.rect.collidepoint(mpos)

    def clicado(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.rect.collidepoint(ev.pos):
            return True
        if self.tecla is not None and ev.type == pygame.KEYDOWN and ev.key == self.tecla:
            return True
        return False

    def desenhar(self, surf):
        c = self.cor if not self.hover else tuple(min(255, v + 40) for v in self.cor)
        painel(surf, self.rect, cor=(c[0] // 4, c[1] // 4, c[2] // 4), borda=c, alpha=230, raio=8)
        texto(surf, self.rotulo, self.rect.center, "ui", C_TEXTO if not self.hover else C_BRANCO, centro=True)


# =============================================================================
# 3. EQUIPAMENTOS (PRE-CHECK)
# =============================================================================

class Equipamento:
    def __init__(self, nome, sigla, pontos_ok, defeito=None, ponto_defeito=None, critico=True):
        self.nome = nome
        self.sigla = sigla
        self.pontos_ok = pontos_ok          # lista de textos de inspecao normais
        self.defeito = defeito              # texto do defeito (None = item bom)
        self.ponto_defeito = ponto_defeito  # indice onde o defeito aparece
        self.critico = critico
        self.inspecionado = False
        self.decisao = None                 # "aprovado" | "descartado"

    @property
    def danificado(self):
        return self.defeito is not None

    def linhas_inspecao(self):
        linhas = list(self.pontos_ok)
        if self.danificado and self.ponto_defeito is not None:
            idx = min(self.ponto_defeito, len(linhas) - 1)
            linhas[idx] = self.defeito
        return linhas


CATALOGO_EPI = [
    dict(nome="Capacete classe B c/ jugular", sigla="CAP",
         ok=["Casco sem trincas, fissuras ou deformacoes.",
             "Jugular de 3 pontos com costura integra.",
             "Suspensao interna firme, catraca funcional.",
             "Etiqueta de validade legivel: dentro do prazo."],
         defeitos=[("Casco apresenta microfissura de 4 cm na lateral direita.", 0),
                   ("Costura da jugular rompida em um dos pontos de fixacao.", 1),
                   ("Catraca da suspensao interna nao trava, casco solto.", 2)]),
    dict(nome="Cinturao tipo paraquedista", sigla="CNT",
         ok=["Fitas sem cortes, queimaduras ou desfiamento.",
             "Argola dorsal em D sem deformacao ou corrosao.",
             "Fivelas engatam e travam com clique audivel.",
             "Numero de serie e inspecao periodica em dia."],
         defeitos=[("Corte transversal de 3 mm na fita da perneira esquerda.", 0),
                   ("Argola dorsal em D com deformacao visivel e oxidacao.", 1),
                   ("Fivela peitoral nao trava, escapa sob tracao manual.", 2)]),
    dict(nome="Talabarte duplo em Y c/ absorvedor", sigla="TAL",
         ok=["Absorvedor de energia lacrado, sem rasgos na capa.",
             "Costuras das pernas do Y completas e simetricas.",
             "Mosquetoes das pontas com trava dupla operante.",
             "Comprimento util dentro do especificado."],
         defeitos=[("Absorvedor de energia acionado: costura ja rasgada.", 0),
                   ("Costura de uma das pernas do Y parcialmente solta.", 1),
                   ("Mosquetao de uma das pontas com trava emperrada.", 2)]),
    dict(nome="Trava-quedas retratil 6 m", sigla="TRQ",
         ok=["Cabo recolhe sozinho sem enroscar.",
             "Teste de tracao brusca: bloqueia instantaneamente.",
             "Carcaca sem trincas, parafusos presentes.",
             "Indicador de impacto na cor verde (nao acionado)."],
         defeitos=[("Cabo de aco com 3 fios rompidos perto do terminal.", 0),
                   ("Teste de tracao brusca: nao bloqueou o cabo.", 1),
                   ("Indicador de impacto vermelho: ja sofreu queda.", 3)]),
    dict(nome="Fita de ancoragem 1,5 m", sigla="FTA",
         ok=["Fita sem abrasao, sem pontos endurecidos.",
             "Alcas costuradas integras nas duas extremidades.",
             "Etiqueta legivel com carga nominal e validade.",
             "Sem contato previo com produto quimico."],
         defeitos=[("Abrasao severa expondo as fibras internas.", 0),
                   ("Alca costurada com fios rompidos na extremidade.", 1),
                   ("Etiqueta ilegivel: rastreabilidade perdida.", 2)]),
    dict(nome="Mosquetao aco trava dupla", sigla="MSQ",
         ok=["Trava retorna sozinha ao ser solta.",
             "Corpo sem empenamento ou desgaste no eixo.",
             "Sem corrosao no rebite e na mola.",
             "Carga nominal gravada e legivel."],
         defeitos=[("Trava nao retorna sozinha: mola vencida.", 0),
                   ("Corpo empenado, gatilho desalinhado do corpo.", 1),
                   ("Corrosao avancada no eixo do gatilho.", 2)]),
    dict(nome="Talabarte de posicionamento", sigla="TPO",
         ok=["Corda sem deformacao de alma, capa uniforme.",
             "Regulador de comprimento desliza e trava.",
             "Terminais costurados protegidos por capa.",
             "Sem sinais de exposicao a solda ou calor."],
         defeitos=[("Capa da corda queimada por respingo de solda.", 3),
                   ("Regulador desliza sob carga: nao trava.", 1)]),
    dict(nome="Cinto porta-ferramentas c/ cabo", sigla="FER",
         ok=["Cabos de retencao de ferramentas integros.",
             "Fecho do cinto sem folga.",
             "Ferramentas com anel de amarracao instalado.",
             "Peso total dentro do limite do cinto."],
         defeitos=[("Cabo de retencao rompido: risco de queda de objeto.", 0),
                   ("Duas ferramentas sem anel de amarracao.", 2)],
         critico=False),
]


def gerar_kit(nivel_idx, qtd_defeitos):
    """Monta o kit de EPI da missao com N itens defeituosos aleatorios."""
    base = list(CATALOGO_EPI)
    random.shuffle(base)
    escolhidos = base[:6]
    # garante que os 3 itens mais criticos sempre estejam no kit
    obrigatorios = [e for e in CATALOGO_EPI if e["sigla"] in ("CNT", "TAL", "TRQ")]
    for o in obrigatorios:
        if o not in escolhidos:
            escolhidos.pop()
            escolhidos.insert(0, o)
    random.shuffle(escolhidos)

    idx_defeito = random.sample(range(len(escolhidos)), min(qtd_defeitos, len(escolhidos)))
    kit = []
    for i, d in enumerate(escolhidos):
        if i in idx_defeito and d["defeitos"]:
            txt, pos = random.choice(d["defeitos"])
            kit.append(Equipamento(d["nome"], d["sigla"], d["ok"], txt, pos, d.get("critico", True)))
        else:
            kit.append(Equipamento(d["nome"], d["sigla"], d["ok"], None, None, d.get("critico", True)))
    return kit


# =============================================================================
# 4. ESTRUTURA (GRAFO DE VIGAS) E NIVEIS
# =============================================================================

class Estrutura:
    """Grafo de vigas percorriveis. Cada no e um ponto de ancoragem."""

    def __init__(self, cols, linhas, sx, sy, origem):
        self.cols, self.linhas = cols, linhas
        self.sx, self.sy = sx, sy
        self.nodes = []
        self.indice = {}
        ox, oy = origem
        for c in range(cols):
            for r in range(linhas):
                self.indice[(c, r)] = len(self.nodes)
                self.nodes.append(Vector2(ox + c * sx, oy - r * sy))

        self.edges = []
        for c in range(cols):
            for r in range(linhas):
                if c + 1 < cols:
                    self.edges.append((self.indice[(c, r)], self.indice[(c + 1, r)]))
                if r + 1 < linhas:
                    self.edges.append((self.indice[(c, r)], self.indice[(c, r + 1)]))

        self.adj = {i: [] for i in range(len(self.nodes))}
        for a, b in self.edges:
            self.adj[a].append(b)
            self.adj[b].append(a)

        self.solo = {self.indice[(c, 0)] for c in range(cols)}
        self.chao_y = oy + 46
        self.rect = pygame.Rect(ox - 120, oy - (linhas - 1) * sy - 160,
                                (cols - 1) * sx + 240, (linhas - 1) * sy + 300)

    def n(self, c, r):
        return self.indice[(c, r)]

    def pos(self, i):
        return self.nodes[i]

    def altura_metros(self, ponto):
        return max(0.0, (self.chao_y - ponto.y) / ESCALA_METRO)

    def mais_proximo(self, ponto, raio, excluir=()):
        melhor, melhor_d = None, raio
        for i, p in enumerate(self.nodes):
            if i in excluir:
                continue
            d = p.distance_to(ponto)
            if d < melhor_d:
                melhor, melhor_d = i, d
        return melhor


NIVEIS = [
    dict(
        nome="OBRA 01 - Poco de Elevador Residencial",
        local="Edificio Solar das Palmeiras - 6 pavimentos",
        cols=4, linhas=6, sx=150, sy=110,
        vento_base=1.5, vento_pico=4.0, rajada_intervalo=(18, 26),
        defeitos=1, tempo=360,
        tarefas=[((1, 2), "sequencia"), ((3, 4), "aperto")],
        resgate=None,
        abrigos=[(0, 0), (3, 0)],
        briefing="Instalacao de linha de vida temporaria no poco de elevador. "
                 "Ambiente protegido, vento fraco. Use a missao para dominar a "
                 "alternancia dos ganchos do talabarte duplo.",
    ),
    dict(
        nome="OBRA 02 - Ponte Estaiada Rio Verde",
        local="Vao central - 48 m sobre a agua",
        cols=6, linhas=7, sx=160, sy=118,
        vento_base=4.0, vento_pico=10.0, rajada_intervalo=(14, 22),
        defeitos=1, tempo=420,
        tarefas=[((1, 3), "solda"), ((4, 2), "aperto"), ((5, 6), "lampada")],
        resgate=None,
        abrigos=[(0, 0), (2, 3)],
        briefing="Inspecao e solda de reforco em pendural do vao central. "
                 "O vento sobre a agua e instavel: monitore o anemometro e "
                 "recolha-se ao abrigo quando a rajada passar de 11 m/s.",
    ),
    dict(
        nome="OBRA 03 - Torre de Transmissao 138 kV",
        local="LT Norte - vao 14, circuito desenergizado",
        cols=5, linhas=9, sx=150, sy=112,
        vento_base=5.0, vento_pico=13.5, rajada_intervalo=(12, 19),
        defeitos=2, tempo=480,
        tarefas=[((0, 4), "aperto"), ((4, 6), "lampada")],
        resgate=(2, 7),
        abrigos=[(0, 0), (4, 0), (2, 4)],
        briefing="Troca da sinalizacao de balizamento noturno. ATENCAO: um "
                 "eletricista ficou suspenso apos queda contida no topo. "
                 "Conclua as tarefas e execute o resgate antes do trauma por "
                 "suspensao.",
    ),
    dict(
        nome="OBRA 04 - Turbina Eolica GX-120",
        local="Parque eolico Serra do Vento - nacele a 96 m",
        cols=4, linhas=12, sx=140, sy=110,
        vento_base=7.0, vento_pico=16.0, rajada_intervalo=(10, 16),
        defeitos=2, tempo=520,
        tarefas=[((0, 5), "solda"), ((3, 8), "aperto"), ((1, 11), "lampada")],
        resgate=(3, 10),
        abrigos=[(0, 0), (1, 5)],
        briefing="Manutencao na torre da turbina. Vento forte e constante em "
                 "grande altura. Trabalhe sempre com os dois ganchos ancorados "
                 "na estacao e use os abrigos entre as rajadas.",
    ),
    dict(
        nome="OBRA 05 - Megaestrutura Urbana Atlas",
        local="Coroamento da torre - 212 m",
        cols=6, linhas=13, sx=150, sy=108,
        vento_base=8.0, vento_pico=18.0, rajada_intervalo=(9, 15),
        defeitos=3, tempo=600,
        tarefas=[((0, 4), "aperto"), ((5, 7), "solda"), ((2, 10), "lampada"), ((4, 12), "sequencia")],
        resgate=(1, 9),
        abrigos=[(0, 0), (3, 6), (5, 11)],
        briefing="Certificacao final do coroamento da torre Atlas. Todas as "
                 "variaveis em jogo: rajadas severas, quatro estacoes de "
                 "manutencao e resgate em altura. Nenhuma infracao e tolerada "
                 "para a classificacao ouro.",
    ),
]


# =============================================================================
# 5. MINIJOGOS DE MANUTENCAO
# =============================================================================

class MiniJogo:
    """Base dos minijogos. Sub-classes implementam atualizar() e desenhar_corpo()."""
    titulo = "TAREFA"
    instrucao = ""

    def __init__(self):
        self.progresso = 0.0
        self.erros = 0
        self.concluido = False
        self.falhou = False
        self.rect = pygame.Rect(0, 0, 640, 300)
        self.rect.center = (LARGURA // 2, ALTURA // 2 + 30)

    def evento(self, ev):
        pass

    def atualizar(self, dt):
        pass

    def desenhar_corpo(self, surf):
        pass

    def desenhar(self, surf):
        veu = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        veu.fill((0, 0, 0, 140))
        surf.blit(veu, (0, 0))
        painel(surf, self.rect, raio=12)
        texto(surf, self.titulo, (self.rect.centerx, self.rect.y + 26), "sub", C_AMARELO, centro=True)
        texto(surf, self.instrucao, (self.rect.centerx, self.rect.y + 58), "ui_p", C_TEXTO_FRACO, centro=True)
        self.desenhar_corpo(surf)
        barra(surf, (self.rect.x + 40, self.rect.bottom - 52, self.rect.w - 80, 16),
              self.progresso, C_VERDE)
        texto(surf, "PROGRESSO {:.0f}%   ERROS: {}".format(self.progresso * 100, self.erros),
              (self.rect.centerx, self.rect.bottom - 24), "mono_p", C_TEXTO_FRACO, centro=True)


class MiniSolda(MiniJogo):
    titulo = "SOLDA DE REFORCO"
    instrucao = "Mantenha o arco na faixa verde. Segure ESPACO para soldar."

    def __init__(self):
        super().__init__()
        self.cursor = 0.5
        self.vel = 0.0
        self.alvo = random.uniform(0.25, 0.75)
        self.larg_alvo = 0.14
        self.dir_alvo = random.choice([-1, 1])
        self.soldando = False
        self.calor = 0.0

    def evento(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_SPACE:
            self.soldando = True
        if ev.type == pygame.KEYUP and ev.key == pygame.K_SPACE:
            self.soldando = False

    def atualizar(self, dt):
        teclas = pygame.key.get_pressed()
        acel = 0.0
        if teclas[pygame.K_a] or teclas[pygame.K_LEFT]:
            acel -= 1.6
        if teclas[pygame.K_d] or teclas[pygame.K_RIGHT]:
            acel += 1.6
        self.vel = (self.vel + acel * dt) * 0.92
        self.cursor = max(0.0, min(1.0, self.cursor + self.vel * dt))

        # alvo deriva
        self.alvo += self.dir_alvo * 0.09 * dt
        if self.alvo < 0.15 or self.alvo > 0.85:
            self.dir_alvo *= -1
            self.alvo = max(0.15, min(0.85, self.alvo))

        dentro = abs(self.cursor - self.alvo) < self.larg_alvo / 2
        if self.soldando:
            if dentro:
                self.progresso += 0.20 * dt
                self.calor = min(1.0, self.calor + dt * 0.8)
            else:
                self.progresso = max(0.0, self.progresso - 0.22 * dt)
                self.calor = min(1.0, self.calor + dt * 1.4)
                if random.random() < dt * 1.2:
                    self.erros += 1
        else:
            self.calor = max(0.0, self.calor - dt * 0.6)

        if self.progresso >= 1.0:
            self.progresso = 1.0
            self.concluido = True

    def desenhar_corpo(self, surf):
        trilho = pygame.Rect(self.rect.x + 50, self.rect.y + 120, self.rect.w - 100, 34)
        pygame.draw.rect(surf, (36, 44, 56), trilho, border_radius=6)
        ax = trilho.x + int((self.alvo - self.larg_alvo / 2) * trilho.w)
        aw = int(self.larg_alvo * trilho.w)
        pygame.draw.rect(surf, (40, 120, 70), (ax, trilho.y, aw, trilho.h), border_radius=6)
        pygame.draw.rect(surf, C_VERDE, (ax, trilho.y, aw, trilho.h), 2, border_radius=6)
        cx = trilho.x + int(self.cursor * trilho.w)
        cor = C_AMARELO if self.soldando else C_TEXTO_FRACO
        pygame.draw.rect(surf, cor, (cx - 4, trilho.y - 10, 8, trilho.h + 20), border_radius=3)
        if self.soldando:
            for _ in range(8):
                fx = cx + random.randint(-10, 10)
                fy = trilho.centery + random.randint(-14, 14)
                pygame.draw.circle(surf, random.choice([C_AMARELO, C_LARANJA, C_BRANCO]), (fx, fy), random.randint(1, 3))
        texto(surf, "A / D  movem o eletrodo", (self.rect.centerx, trilho.bottom + 26), "ui_p", C_TEXTO_FRACO, centro=True)


class MiniAperto(MiniJogo):
    titulo = "TORQUE DE PARAFUSOS ESTRUTURAIS"
    instrucao = "Segure ESPACO para aplicar torque e solte dentro da faixa verde."

    def __init__(self):
        super().__init__()
        self.valor = 0.0
        self.aplicando = False
        self.alvo = random.uniform(0.45, 0.8)
        self.tol = 0.09
        self.feitos = 0
        self.total = 4
        self.msg = ""
        self.msg_t = 0.0

    def novo_parafuso(self):
        self.valor = 0.0
        self.alvo = random.uniform(0.40, 0.82)
        self.tol = max(0.055, 0.095 - self.feitos * 0.008)

    def evento(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_SPACE:
            self.aplicando = True
        if ev.type == pygame.KEYUP and ev.key == pygame.K_SPACE and self.aplicando:
            self.aplicando = False
            if abs(self.valor - self.alvo) <= self.tol:
                self.feitos += 1
                self.msg, self.msg_t = "TORQUE CORRETO", 1.0
            else:
                self.erros += 1
                self.msg = "SUBTORQUE" if self.valor < self.alvo else "SOBRETORQUE"
                self.msg_t = 1.0
            self.progresso = self.feitos / self.total
            if self.feitos >= self.total:
                self.concluido = True
            else:
                self.novo_parafuso()

    def atualizar(self, dt):
        if self.aplicando:
            self.valor = min(1.05, self.valor + dt * 0.46)
            if self.valor >= 1.04:
                self.aplicando = False
                self.erros += 1
                self.msg, self.msg_t = "PARAFUSO ESPANADO", 1.0
                self.novo_parafuso()
        self.msg_t = max(0.0, self.msg_t - dt)

    def desenhar_corpo(self, surf):
        trilho = pygame.Rect(self.rect.x + 50, self.rect.y + 130, self.rect.w - 100, 30)
        pygame.draw.rect(surf, (36, 44, 56), trilho, border_radius=6)
        ax = trilho.x + int((self.alvo - self.tol) * trilho.w)
        aw = int(2 * self.tol * trilho.w)
        pygame.draw.rect(surf, (40, 120, 70), (ax, trilho.y, aw, trilho.h), border_radius=6)
        pygame.draw.rect(surf, (140, 60, 60), (trilho.x + int(0.95 * trilho.w), trilho.y,
                                               int(0.05 * trilho.w), trilho.h), border_radius=6)
        pygame.draw.rect(surf, C_LARANJA, (trilho.x, trilho.y, int(self.valor * trilho.w), trilho.h), border_radius=6)
        pygame.draw.rect(surf, C_PAINEL_BORDA, trilho, 2, border_radius=6)
        texto(surf, "PARAFUSO {}/{}".format(self.feitos + 1 if not self.concluido else self.total, self.total),
              (self.rect.centerx, trilho.y - 30), "ui", C_TEXTO, centro=True)
        if self.msg_t > 0:
            cor = C_VERDE if "CORRETO" in self.msg else C_VERMELHO
            texto(surf, self.msg, (self.rect.centerx, trilho.bottom + 26), "ui_g", cor, centro=True)


class MiniLampada(MiniJogo):
    titulo = "TROCA DE LAMPADA DE BALIZAMENTO"
    instrucao = "Execute a sequencia de procedimento na ordem indicada."

    PASSOS = [
        ("Bloquear e etiquetar o circuito (LOTO)", pygame.K_1),
        ("Testar ausencia de tensao", pygame.K_2),
        ("Remover a cupula de protecao", pygame.K_3),
        ("Substituir a lampada de balizamento", pygame.K_4),
        ("Recolocar cupula e vedacao", pygame.K_5),
        ("Retirar o bloqueio e testar o farol", pygame.K_6),
    ]

    def __init__(self):
        super().__init__()
        self.rect = pygame.Rect(0, 0, 680, 360)
        self.rect.center = (LARGURA // 2, ALTURA // 2 + 20)
        self.passo = 0
        self.msg_t = 0.0
        self.msg = ""

    def evento(self, ev):
        if ev.type != pygame.KEYDOWN:
            return
        teclas = [p[1] for p in self.PASSOS]
        if ev.key in teclas:
            idx = teclas.index(ev.key)
            if idx == self.passo:
                self.passo += 1
                self.progresso = self.passo / len(self.PASSOS)
                self.msg, self.msg_t = "OK", 0.6
                if self.passo >= len(self.PASSOS):
                    self.concluido = True
            else:
                self.erros += 1
                self.msg, self.msg_t = "FORA DE SEQUENCIA!", 1.0

    def atualizar(self, dt):
        self.msg_t = max(0.0, self.msg_t - dt)

    def desenhar_corpo(self, surf):
        y = self.rect.y + 92
        for i, (txt, tecla) in enumerate(self.PASSOS):
            feito = i < self.passo
            atual = i == self.passo
            cor = C_VERDE if feito else (C_AMARELO if atual else C_TEXTO_FRACO)
            marca = "[X]" if feito else ("[>]" if atual else "[ ]")
            texto(surf, "{} {}. {}".format(marca, i + 1, txt), (self.rect.x + 44, y), "ui_p", cor)
            y += 24
        if self.msg_t > 0:
            cor = C_VERDE if self.msg == "OK" else C_VERMELHO
            texto(surf, self.msg, (self.rect.centerx, self.rect.bottom - 76), "ui", cor, centro=True)


class MiniSequencia(MiniJogo):
    titulo = "INSPECAO DE SOLDAS COM LIQUIDO PENETRANTE"
    instrucao = "Digite a sequencia de teclas exibida antes do tempo acabar."

    def __init__(self):
        super().__init__()
        self.teclas_pool = [pygame.K_q, pygame.K_w, pygame.K_e, pygame.K_r, pygame.K_a, pygame.K_s, pygame.K_d]
        self.nomes = {pygame.K_q: "Q", pygame.K_w: "W", pygame.K_e: "E", pygame.K_r: "R",
                      pygame.K_a: "A", pygame.K_s: "S", pygame.K_d: "D"}
        self.rodadas = 0
        self.total = 3
        self.nova_rodada()

    def nova_rodada(self):
        n = 4 + self.rodadas
        self.seq = [random.choice(self.teclas_pool) for _ in range(n)]
        self.i = 0
        self.tempo = 2.2 + n * 0.75

    def evento(self, ev):
        if ev.type != pygame.KEYDOWN:
            return
        if ev.key == self.seq[self.i]:
            self.i += 1
            if self.i >= len(self.seq):
                self.rodadas += 1
                self.progresso = self.rodadas / self.total
                if self.rodadas >= self.total:
                    self.concluido = True
                else:
                    self.nova_rodada()
        elif ev.key in self.teclas_pool:
            self.erros += 1
            self.i = 0

    def atualizar(self, dt):
        self.tempo -= dt
        if self.tempo <= 0:
            self.erros += 1
            self.nova_rodada()

    def desenhar_corpo(self, surf):
        larg = 46
        total_w = len(self.seq) * (larg + 10)
        x0 = self.rect.centerx - total_w // 2
        for i, k in enumerate(self.seq):
            r = pygame.Rect(x0 + i * (larg + 10), self.rect.y + 118, larg, larg)
            feito = i < self.i
            pygame.draw.rect(surf, (40, 120, 70) if feito else (36, 44, 56), r, border_radius=6)
            pygame.draw.rect(surf, C_VERDE if feito else C_PAINEL_BORDA, r, 2, border_radius=6)
            texto(surf, self.nomes[k], r.center, "ui_g", C_TEXTO, centro=True)
        barra(surf, (self.rect.x + 120, self.rect.y + 186, self.rect.w - 240, 10),
              max(0.0, self.tempo / 6.0), C_LARANJA)
        texto(surf, "RODADA {}/{}".format(min(self.rodadas + 1, self.total), self.total),
              (self.rect.centerx, self.rect.y + 210), "ui_p", C_TEXTO_FRACO, centro=True)


class MiniResgate(MiniJogo):
    titulo = "RESGATE EM ALTURA - DESCIDA CONTROLADA"
    instrucao = "Segure ESPACO para descer. Mantenha a velocidade na faixa verde."

    def __init__(self, altura_m):
        super().__init__()
        self.altura = altura_m
        self.restante = altura_m
        self.vel = 0.0
        self.descendo = False
        self.alerta = 0.0

    def evento(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_SPACE:
            self.descendo = True
        if ev.type == pygame.KEYUP and ev.key == pygame.K_SPACE:
            self.descendo = False

    def atualizar(self, dt):
        if self.descendo:
            self.vel += 1.55 * dt
        else:
            self.vel -= 2.10 * dt
        self.vel = max(0.0, min(3.2, self.vel))
        self.restante = max(0.0, self.restante - self.vel * dt)
        self.progresso = 1.0 - self.restante / max(1.0, self.altura)
        if self.vel > 2.0:
            self.alerta += dt
            if self.alerta > 0.8:
                self.alerta = 0.0
                self.erros += 1
        else:
            self.alerta = max(0.0, self.alerta - dt * 0.5)
        if self.restante <= 0.01:
            self.concluido = True

    def desenhar_corpo(self, surf):
        trilho = pygame.Rect(self.rect.x + 50, self.rect.y + 120, self.rect.w - 100, 28)
        pygame.draw.rect(surf, (36, 44, 56), trilho, border_radius=6)
        # faixa segura 0.6 - 1.6 m/s em escala 0..3.2
        ax = trilho.x + int(0.6 / 3.2 * trilho.w)
        aw = int(1.0 / 3.2 * trilho.w)
        pygame.draw.rect(surf, (40, 120, 70), (ax, trilho.y, aw, trilho.h), border_radius=6)
        cx = trilho.x + int(self.vel / 3.2 * trilho.w)
        cor = C_VERMELHO if self.vel > 2.0 else C_AMARELO
        pygame.draw.rect(surf, cor, (cx - 4, trilho.y - 8, 8, trilho.h + 16), border_radius=3)
        texto(surf, "VELOCIDADE DE DESCIDA: {:.2f} m/s".format(self.vel),
              (self.rect.centerx, trilho.y - 28), "mono", C_TEXTO, centro=True)
        texto(surf, "ALTURA RESTANTE: {:.1f} m".format(self.restante),
              (self.rect.centerx, trilho.bottom + 22), "mono", C_TEXTO, centro=True)


MINIJOGOS = {
    "solda": MiniSolda,
    "aperto": MiniAperto,
    "lampada": MiniLampada,
    "sequencia": MiniSequencia,
}

NOME_TAREFA = {
    "solda": "Solda de reforco",
    "aperto": "Torque de parafusos",
    "lampada": "Lampada de balizamento",
    "sequencia": "Ensaio de soldas",
}


# =============================================================================
# 6. JOGADOR
# =============================================================================

class Jogador:
    def __init__(self, estrutura, no_inicial):
        self.est = estrutura
        self.a = no_inicial
        self.b = None
        self.u = 0.0
        self.pos = Vector2(estrutura.pos(no_inicial))
        self.ganchos = [None, None]     # indices de no ancorados
        self.vel_base = 128.0
        self.equilibrio = 100.0
        self.agachado = False
        self.suspenso = 0.0             # tempo em queda contida
        self.olhando = 1
        self.anim = 0.0
        self.bloqueado_msg = 0.0

    # -- estado ------------------------------------------------------------
    @property
    def ancorado(self):
        return sum(1 for g in self.ganchos if g is not None)

    def no_solo(self):
        if self.b is None:
            return self.a in self.est.solo
        return self.a in self.est.solo and self.b in self.est.solo

    def altura(self):
        return self.est.altura_metros(self.pos)

    def atualizar_pos(self):
        if self.b is None:
            self.pos = Vector2(self.est.pos(self.a))
        else:
            pa, pb = self.est.pos(self.a), self.est.pos(self.b)
            self.pos = pa + (pb - pa) * self.u

    # -- ancoragem ---------------------------------------------------------
    def alternar_gancho(self, idx):
        """Retorna (sucesso, mensagem)."""
        if self.ganchos[idx] is not None:
            outro = self.ganchos[1 - idx]
            self.ganchos[idx] = None
            if outro is None and not self.no_solo():
                # o jogo permite o erro, mas ele e grave: sem ancoragem em altura
                return True, "PERIGO: voce ficou SEM NENHUMA ancoragem!"
            return True, "Gancho {} liberado".format(idx + 1)

        excluir = tuple(g for g in self.ganchos if g is not None)
        alvo = self.est.mais_proximo(self.pos, RAIO_ANCORAGEM, excluir)
        if alvo is None:
            return False, "Nenhum ponto de ancoragem ao alcance"
        if self.pos.distance_to(self.est.pos(alvo)) > CABO_MAX:
            return False, "Ponto fora do comprimento do talabarte"
        self.ganchos[idx] = alvo
        return True, "Gancho {} ancorado".format(idx + 1)

    def tensionado(self, ponto):
        for g in self.ganchos:
            if g is not None and ponto.distance_to(self.est.pos(g)) > CABO_MAX:
                return True
        return False

    # -- movimento ---------------------------------------------------------
    def mover(self, direcao, dt):
        """direcao: Vector2 normalizavel. Retorna codigo de evento ou None."""
        if direcao.length_squared() == 0:
            return None
        d = direcao.normalize()

        if self.ancorado == 0 and not self.no_solo():
            return "QUEDA_LIVRE"

        if self.ancorado == 0 and self.no_solo() and self.b is None:
            # no solo: so pode iniciar a subida com pelo menos um gancho ancorado
            saida_perigosa = False
            for n in self.est.adj[self.a]:
                v = self.est.pos(n) - self.est.pos(self.a)
                if v.length_squared() > 0 and v.normalize().dot(d) > 0.45 and n not in self.est.solo:
                    saida_perigosa = True
            if saida_perigosa:
                return "BLOQUEADO_SOLO"

        if self.b is None:
            melhor, melhor_dot = None, 0.45
            for n in self.est.adj[self.a]:
                v = (self.est.pos(n) - self.est.pos(self.a))
                if v.length_squared() == 0:
                    continue
                dot = v.normalize().dot(d)
                if dot > melhor_dot:
                    melhor, melhor_dot = n, dot
            if melhor is None:
                return None
            self.b = melhor
            self.u = 0.0

        pa, pb = self.est.pos(self.a), self.est.pos(self.b)
        vetor = pb - pa
        comp = vetor.length()
        if comp <= 0:
            self.b = None
            return None
        sentido = 1 if vetor.normalize().dot(d) > 0 else -1
        vel = self.vel_base * (0.45 if self.agachado else 1.0)
        vel *= 0.55 + 0.45 * (self.equilibrio / 100.0)
        novo_u = self.u + sentido * vel * dt / comp
        novo_u_c = max(0.0, min(1.0, novo_u))
        tentativa = pa + vetor * novo_u_c

        if self.tensionado(tentativa):
            self.bloqueado_msg = 1.2
            return "TENSIONADO"

        self.u = novo_u_c
        self.olhando = 1 if vetor.x * sentido >= 0 else -1
        self.anim += dt * 8
        if novo_u >= 1.0:
            self.a, self.b, self.u = self.b, None, 0.0
        elif novo_u <= 0.0:
            self.b, self.u = None, 0.0
        self.atualizar_pos()
        return None

    # -- desenho -----------------------------------------------------------
    def desenhar(self, surf, cam):
        p = self.pos - cam
        cores = [C_VERDE, C_AZUL]
        for i, g in enumerate(self.ganchos):
            if g is not None:
                desenhar_cabo(surf, p + Vector2(0, -16), self.est.pos(g) - cam, cores[i], sag=10, espessura=3)

        bal = math.sin(self.anim) * 2 if not self.agachado else 0
        altura_corpo = 22 if not self.agachado else 15
        cx, cy = int(p.x), int(p.y)

        # pernas
        pygame.draw.line(surf, (40, 48, 60), (cx, cy), (cx - 6, cy + 12 + bal), 4)
        pygame.draw.line(surf, (40, 48, 60), (cx, cy), (cx + 6, cy + 12 - bal), 4)
        # tronco com cinturao
        corpo = pygame.Rect(cx - 8, cy - altura_corpo, 16, altura_corpo)
        pygame.draw.rect(surf, C_LARANJA, corpo, border_radius=4)
        pygame.draw.rect(surf, (150, 70, 20), corpo, 1, border_radius=4)
        pygame.draw.line(surf, (30, 34, 42), (cx - 8, cy - altura_corpo // 2), (cx + 8, cy - altura_corpo // 2), 3)
        # fitas do paraquedista
        pygame.draw.line(surf, (235, 235, 235), (cx - 6, cy - altura_corpo), (cx + 4, cy - altura_corpo // 2), 2)
        pygame.draw.line(surf, (235, 235, 235), (cx + 6, cy - altura_corpo), (cx - 4, cy - altura_corpo // 2), 2)
        # bracos
        pygame.draw.line(surf, C_LARANJA, (cx, cy - altura_corpo + 4),
                         (cx + 11 * self.olhando, cy - altura_corpo + 12 - bal), 4)
        # cabeca + capacete
        hy = cy - altura_corpo - 9
        pygame.draw.circle(surf, (222, 190, 160), (cx, hy), 7)
        pygame.draw.circle(surf, C_AMARELO, (cx, hy - 2), 8)
        pygame.draw.rect(surf, C_AMARELO, (cx - 9, hy - 3, 18, 4), border_radius=2)
        pygame.draw.line(surf, (60, 60, 60), (cx - 5, hy + 4), (cx + 5, hy + 4), 1)  # jugular


# =============================================================================
# 7. CENAS
# =============================================================================

class Cena:
    def __init__(self, app):
        self.app = app

    def evento(self, ev):
        pass

    def atualizar(self, dt):
        pass

    def desenhar(self, surf):
        pass


# ---------------------------------------------------------------- FUNDO ----
class Fundo:
    """Ceu, nuvens e skyline em parallax."""

    _ceu = None  # cache compartilhado do gradiente do ceu

    def __init__(self, seed=1):
        rnd = random.Random(seed)
        if Fundo._ceu is None:
            Fundo._ceu = pygame.Surface((LARGURA, ALTURA))
            gradiente_vertical(Fundo._ceu, Fundo._ceu.get_rect(), C_FUNDO_TOPO, C_FUNDO_BASE)

        # predios pre-renderizados (com janelas) para nao redesenhar por frame
        self.predios = []
        for _ in range(26):
            bx = rnd.randint(-200, LARGURA + 200)
            bh = rnd.randint(120, 380)
            bw = rnd.randint(60, 150)
            par = rnd.uniform(0.15, 0.35)
            tom = int(40 + par * 90)
            s = pygame.Surface((bw, bh + 400))
            s.fill((tom, tom + 8, tom + 22))
            for jx in range(8, bw - 6, 16):
                for jy in range(12, bh - 10, 22):
                    if (jx + jy + int(bx)) % 3 == 0:
                        pygame.draw.rect(s, (tom + 34, tom + 38, tom + 24), (jx, jy, 6, 9))
            self.predios.append((s, bx, bh, par))

        # nuvens pre-renderizadas
        self.nuvens = []
        for _ in range(9):
            w = rnd.randint(60, 150)
            s = pygame.Surface((w * 2, 44), pygame.SRCALPHA)
            for i in range(4):
                pygame.draw.ellipse(s, (255, 255, 255, 26), (i * w // 3, 6 + (i % 2) * 6, w, 32))
            self.nuvens.append([float(rnd.randint(0, LARGURA)), rnd.randint(40, 320),
                                rnd.uniform(0.05, 0.16), s])

    def desenhar(self, surf, cam, vento=0.0):
        surf.blit(Fundo._ceu, (0, 0))
        for n in self.nuvens:
            n[0] -= (6 + vento * 2) * 0.016
            if n[0] < -400:
                n[0] = LARGURA + 200
            x = n[0] - cam.x * n[2]
            y = n[1] - cam.y * n[2] * 0.5
            surf.blit(n[3], (x % (LARGURA + 400) - 200, y))
        for (s, bx, bh, par) in self.predios:
            x = bx - cam.x * par
            y = ALTURA - bh - cam.y * par * 0.35
            if -260 < x < LARGURA + 60 and y < ALTURA:
                surf.blit(s, (x, y))


# ------------------------------------------------------------------ MENU ----
class CenaMenu(Cena):
    def __init__(self, app):
        super().__init__(app)
        self.fundo = Fundo(7)
        self.cam = Vector2(0, 0)
        self.t = 0.0
        self.opcoes = ["MODO CARREIRA", "DESAFIO VR - SPRINT DE ANCORAGEM",
                       "COMO JOGAR / NORMAS", "ZERAR PROGRESSO", "SAIR"]
        self.sel = 0
        self.botoes = []
        for i, o in enumerate(self.opcoes):
            self.botoes.append(Botao((LARGURA // 2 - 230, 300 + i * 58, 460, 46), o))

    def evento(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_DOWN, pygame.K_s):
                self.sel = (self.sel + 1) % len(self.opcoes)
            elif ev.key in (pygame.K_UP, pygame.K_w):
                self.sel = (self.sel - 1) % len(self.opcoes)
            elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.executar(self.sel)
        for i, b in enumerate(self.botoes):
            if b.clicado(ev):
                self.sel = i
                self.executar(i)

    def executar(self, i):
        if i == 0:
            self.app.trocar(CenaSelecaoObra(self.app))
        elif i == 1:
            self.app.trocar(CenaPreCheck(self.app, nivel_idx=2, vr=True))
        elif i == 2:
            self.app.trocar(CenaAjuda(self.app))
        elif i == 3:
            self.app.progresso = {"desbloqueado": 1, "melhores": {}, "recorde_vr": 0}
            self.app.salvar()
        elif i == 4:
            self.app.rodando = False

    def atualizar(self, dt):
        self.t += dt
        self.cam.x += dt * 12
        mpos = pygame.mouse.get_pos()
        for i, b in enumerate(self.botoes):
            b.atualizar(mpos)
            if b.hover:
                self.sel = i

    def desenhar(self, surf):
        self.fundo.desenhar(surf, self.cam, 3)
        # torre decorativa
        for i in range(9):
            y = 80 + i * 66
            pygame.draw.line(surf, C_ACO_ESC, (120, y), (300, y), 6)
        pygame.draw.line(surf, C_ACO, (130, 60), (130, 660), 8)
        pygame.draw.line(surf, C_ACO, (290, 60), (290, 660), 8)

        texto(surf, "SKYLINE SAFE", (LARGURA // 2, 130), "titulo", C_AMARELO, centro=True, sombra=True)
        texto(surf, "M E S T R E   D A   A L T U R A", (LARGURA // 2, 182), "sub", C_TEXTO, centro=True, sombra=True)
        texto(surf, "Simulador de inspecao e manutencao em altura", (LARGURA // 2, 222),
              "ui_p", C_TEXTO_FRACO, centro=True)

        for i, b in enumerate(self.botoes):
            b.cor = C_AMARELO if i == self.sel else C_AZUL
            b.desenhar(surf)

        n = self.app.progresso["desbloqueado"]
        texto(surf, "Obras liberadas: {}/{}   |   Recorde VR: {} ancoragens".format(
            n, len(NIVEIS), self.app.progresso.get("recorde_vr", 0)),
            (LARGURA // 2, ALTURA - 54), "mono_p", C_TEXTO_FRACO, centro=True)
        texto(surf, "Setas/WASD navegam  -  ENTER confirma", (LARGURA // 2, ALTURA - 30),
              "mono_p", C_TEXTO_FRACO, centro=True)


# ----------------------------------------------------------------- AJUDA ----
class CenaAjuda(Cena):
    TEXTO = [
        ("MOVIMENTACAO", [
            "A / D  ou  SETAS  -  deslocar na horizontal sobre as vigas",
            "W / S  -  subir e descer nos montantes verticais",
            "CTRL   -  agachar e firmar o corpo (reduz efeito do vento)",
        ]),
        ("TALABARTE DUPLO (regra de ouro)", [
            "1  -  ancorar / liberar o GANCHO 1 (verde)",
            "2  -  ancorar / liberar o GANCHO 2 (azul)",
            "Para avancar: ancore o gancho livre no proximo ponto,",
            "depois libere o gancho de tras. NUNCA os dois soltos.",
            "Mover-se fora do solo com os dois ganchos soltos = FALHA.",
        ]),
        ("TRABALHO E RESGATE", [
            "E  -  iniciar tarefa na estacao (exige os 2 ganchos ancorados)",
            "R  -  iniciar resgate do colega suspenso (exige 2 ganchos)",
            "TAB  -  abrir a ordem de servico / lista de tarefas",
        ]),
        ("CLIMA", [
            "Acima de {:.0f} m/s a atividade deve ser interrompida.".format(LIMITE_VENTO),
            "Va ate um ABRIGO (marcado em azul) ou agache com 2 ganchos.",
            "O medidor de EQUILIBRIO zera se voce insistir na rajada.",
        ]),
        ("PRE-CHECK", [
            "Inspecione TODOS os itens antes de subir.",
            "Aprovar um EPI danificado causa falha do equipamento na obra.",
            "Descartar um EPI bom gasta tempo com reposicao.",
        ]),
    ]

    def __init__(self, app):
        super().__init__(app)
        self.fundo = Fundo(3)
        self.voltar = Botao((LARGURA // 2 - 90, ALTURA - 62, 180, 40), "VOLTAR (ESC)", pygame.K_ESCAPE)

    def evento(self, ev):
        if self.voltar.clicado(ev):
            self.app.trocar(CenaMenu(self.app))

    def atualizar(self, dt):
        self.voltar.atualizar(pygame.mouse.get_pos())

    def desenhar(self, surf):
        self.fundo.desenhar(surf, Vector2(0, 0))
        painel(surf, (70, 50, LARGURA - 140, ALTURA - 130))
        texto(surf, "MANUAL DO INSPETOR", (LARGURA // 2, 84), "sub", C_AMARELO, centro=True)
        col_x = [110, 690]
        col_y = [130, 130]
        c = 0
        for titulo_sec, linhas in self.TEXTO:
            if col_y[c] > ALTURA - 220 and c == 0:
                c = 1
            texto(surf, titulo_sec, (col_x[c], col_y[c]), "ui_g", C_LARANJA)
            col_y[c] += 30
            for l in linhas:
                texto(surf, l, (col_x[c] + 10, col_y[c]), "ui_p", C_TEXTO)
                col_y[c] += 22
            col_y[c] += 16
        self.voltar.desenhar(surf)


# --------------------------------------------------------- SELECAO OBRA ----
class CenaSelecaoObra(Cena):
    def __init__(self, app):
        super().__init__(app)
        self.fundo = Fundo(11)
        self.sel = 0
        self.cards = []
        for i in range(len(NIVEIS)):
            self.cards.append(pygame.Rect(80, 150 + i * 96, 520, 82))
        self.voltar = Botao((60, ALTURA - 66, 160, 40), "ESC - MENU", pygame.K_ESCAPE)

    def evento(self, ev):
        if self.voltar.clicado(ev):
            self.app.trocar(CenaMenu(self.app))
            return
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_DOWN, pygame.K_s):
                self.sel = (self.sel + 1) % len(NIVEIS)
            elif ev.key in (pygame.K_UP, pygame.K_w):
                self.sel = (self.sel - 1) % len(NIVEIS)
            elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.iniciar()
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for i, c in enumerate(self.cards):
                if c.collidepoint(ev.pos):
                    self.sel = i
                    self.iniciar()

    def iniciar(self):
        if self.sel < self.app.progresso["desbloqueado"]:
            self.app.trocar(CenaPreCheck(self.app, self.sel))

    def atualizar(self, dt):
        self.voltar.atualizar(pygame.mouse.get_pos())

    def desenhar(self, surf):
        self.fundo.desenhar(surf, Vector2(0, 0))
        texto(surf, "MODO CARREIRA - ORDENS DE SERVICO", (LARGURA // 2, 70), "sub", C_AMARELO, centro=True, sombra=True)
        for i, c in enumerate(self.cards):
            liberado = i < self.app.progresso["desbloqueado"]
            ativo = i == self.sel
            painel(surf, c, borda=C_AMARELO if ativo else C_PAINEL_BORDA,
                   cor=(24, 32, 46) if liberado else (16, 18, 22))
            cor = C_TEXTO if liberado else (86, 92, 104)
            texto(surf, NIVEIS[i]["nome"], (c.x + 18, c.y + 14), "ui", cor)
            texto(surf, NIVEIS[i]["local"], (c.x + 18, c.y + 40), "ui_p",
                  C_TEXTO_FRACO if liberado else (70, 74, 84))
            best = self.app.progresso["melhores"].get(str(i))
            if not liberado:
                texto(surf, "BLOQUEADA", (c.right - 18, c.centery), "mono", (120, 90, 90), direita=True)
            elif best:
                texto(surf, "{} pts".format(best), (c.right - 18, c.centery), "mono", C_VERDE, direita=True)
            else:
                texto(surf, "NAO EXECUTADA", (c.right - 18, c.centery), "mono_p", C_TEXTO_FRACO, direita=True)

        nv = NIVEIS[self.sel]
        det = pygame.Rect(640, 150, LARGURA - 720, 420)
        painel(surf, det)
        texto(surf, "BRIEFING", (det.x + 24, det.y + 20), "ui_g", C_LARANJA)
        y = texto_bloco(surf, nv["briefing"], (det.x + 24, det.y + 56), det.w - 48, "ui_p")
        y += 14
        texto(surf, "Vento previsto : {:.0f} a {:.0f} m/s".format(nv["vento_base"], nv["vento_pico"]),
              (det.x + 24, y), "mono_p", C_TEXTO); y += 24
        texto(surf, "Tarefas        : {}".format(len(nv["tarefas"])), (det.x + 24, y), "mono_p", C_TEXTO); y += 24
        texto(surf, "Resgate        : {}".format("SIM" if nv["resgate"] else "nao"),
              (det.x + 24, y), "mono_p", C_VERMELHO if nv["resgate"] else C_TEXTO); y += 24
        texto(surf, "Altura maxima  : {:.0f} m".format((nv["linhas"] - 1) * nv["sy"] / ESCALA_METRO),
              (det.x + 24, y), "mono_p", C_TEXTO); y += 24
        texto(surf, "Tempo limite   : {:02d}:{:02d}".format(nv["tempo"] // 60, nv["tempo"] % 60),
              (det.x + 24, y), "mono_p", C_TEXTO)
        texto(surf, "ENTER para iniciar o pre-check", (det.centerx, det.bottom - 34), "ui_p", C_AMARELO, centro=True)
        self.voltar.desenhar(surf)


# ------------------------------------------------------------- PRE-CHECK ----
class CenaPreCheck(Cena):
    def __init__(self, app, nivel_idx, vr=False):
        super().__init__(app)
        self.nivel_idx = nivel_idx
        self.vr = vr
        nv = NIVEIS[nivel_idx]
        self.kit = gerar_kit(nivel_idx, 0 if vr else nv["defeitos"])
        self.sel = 0
        self.fundo = Fundo(21)
        self.msg, self.msg_t = "", 0.0
        self.cards = []
        for i in range(len(self.kit)):
            cx = 70 + (i % 2) * 300
            cy = 170 + (i // 2) * 116
            self.cards.append(pygame.Rect(cx, cy, 275, 96))
        self.b_aprovar = Botao((700, 560, 200, 46), "APROVAR  [A]", pygame.K_a, C_VERDE)
        self.b_descartar = Botao((920, 560, 200, 46), "DESCARTAR  [D]", pygame.K_d, C_VERMELHO)
        self.b_subir = Botao((LARGURA // 2 - 170, ALTURA - 62, 340, 44), "CONCLUIR PRE-CHECK  [ENTER]", pygame.K_RETURN)
        self.b_voltar = Botao((60, ALTURA - 62, 150, 40), "ESC", pygame.K_ESCAPE)

    @property
    def item(self):
        return self.kit[self.sel]

    def evento(self, ev):
        if self.b_voltar.clicado(ev):
            self.app.trocar(CenaMenu(self.app) if self.vr else CenaSelecaoObra(self.app))
            return
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for i, c in enumerate(self.cards):
                if c.collidepoint(ev.pos):
                    self.sel = i
                    self.kit[i].inspecionado = True
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_DOWN, pygame.K_s):
                self.sel = (self.sel + 1) % len(self.kit)
                self.item.inspecionado = True
            elif ev.key in (pygame.K_UP, pygame.K_w):
                self.sel = (self.sel - 1) % len(self.kit)
                self.item.inspecionado = True
        if self.b_aprovar.clicado(ev):
            self.decidir("aprovado")
        if self.b_descartar.clicado(ev):
            self.decidir("descartado")
        if self.b_subir.clicado(ev):
            self.concluir()

    def decidir(self, d):
        self.item.inspecionado = True
        self.item.decisao = d
        self.msg = "{} -> {}".format(self.item.sigla, d.upper())
        self.msg_t = 1.4
        # avanca para o proximo item pendente
        for k in range(1, len(self.kit) + 1):
            j = (self.sel + k) % len(self.kit)
            if self.kit[j].decisao is None:
                self.sel = j
                self.kit[j].inspecionado = True
                break

    def concluir(self):
        pendentes = [e for e in self.kit if e.decisao is None]
        if pendentes:
            self.msg = "Ha {} item(ns) sem decisao no pre-check.".format(len(pendentes))
            self.msg_t = 2.2
            return
        self.app.trocar(CenaJogo(self.app, self.nivel_idx, self.kit, vr=self.vr))

    def atualizar(self, dt):
        self.msg_t = max(0.0, self.msg_t - dt)
        mpos = pygame.mouse.get_pos()
        for b in (self.b_aprovar, self.b_descartar, self.b_subir, self.b_voltar):
            b.atualizar(mpos)
        self.item.inspecionado = True

    def desenhar(self, surf):
        self.fundo.desenhar(surf, Vector2(0, 0))
        veu = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        veu.fill((0, 0, 0, 120))
        surf.blit(veu, (0, 0))

        texto(surf, "INSPECAO PRE-USO DE EPI", (LARGURA // 2, 52), "sub", C_AMARELO, centro=True, sombra=True)
        nome = "DESAFIO VR" if self.vr else NIVEIS[self.nivel_idx]["nome"]
        texto(surf, nome, (LARGURA // 2, 90), "ui_p", C_TEXTO_FRACO, centro=True)

        for i, c in enumerate(self.cards):
            it = self.kit[i]
            ativo = i == self.sel
            cor_borda = C_AMARELO if ativo else C_PAINEL_BORDA
            if it.decisao == "aprovado":
                cor_borda = C_VERDE
            elif it.decisao == "descartado":
                cor_borda = C_VERMELHO
            painel(surf, c, borda=cor_borda)
            texto(surf, it.sigla, (c.x + 14, c.y + 12), "ui_g", C_LARANJA)
            texto_bloco(surf, it.nome, (c.x + 14, c.y + 42), c.w - 28, "ui_p")
            marca = {"aprovado": "APROVADO", "descartado": "DESCARTADO", None: "pendente"}[it.decisao]
            cor_m = {"aprovado": C_VERDE, "descartado": C_VERMELHO, None: C_TEXTO_FRACO}[it.decisao]
            texto(surf, marca, (c.right - 12, c.y + 20), "mono_p", cor_m, direita=True)

        # painel de inspecao detalhada
        det = pygame.Rect(680, 150, LARGURA - 740, 380)
        painel(surf, det)
        it = self.item
        texto(surf, "LUPA DE INSPECAO", (det.x + 22, det.y + 18), "ui_g", C_AMARELO)
        texto(surf, it.nome, (det.x + 22, det.y + 52), "ui", C_TEXTO)
        pygame.draw.line(surf, C_PAINEL_BORDA, (det.x + 22, det.y + 82), (det.right - 22, det.y + 82), 1)
        y = det.y + 96
        for linha in it.linhas_inspecao():
            pygame.draw.circle(surf, C_TEXTO_FRACO, (det.x + 30, y + 8), 3)
            y = texto_bloco(surf, linha, (det.x + 44, y), det.w - 70, "ui_p") + 8
        texto(surf, "Julgue pelo laudo acima. Item fora de conformidade deve ser descartado.",
              (det.x + 22, det.bottom - 44), "ui_p", C_TEXTO_FRACO)

        self.b_aprovar.desenhar(surf)
        self.b_descartar.desenhar(surf)
        self.b_subir.desenhar(surf)
        self.b_voltar.desenhar(surf)
        if self.msg_t > 0:
            texto(surf, self.msg, (LARGURA // 2, ALTURA - 96), "ui", C_AMARELO, centro=True)


# ------------------------------------------------------------------ JOGO ----
class CenaJogo(Cena):
    def __init__(self, app, nivel_idx, kit, vr=False):
        super().__init__(app)
        self.nivel_idx = nivel_idx
        self.nv = NIVEIS[nivel_idx]
        self.kit = kit
        self.vr = vr
        self.fundo = Fundo(nivel_idx + 4)

        nv = self.nv
        origem = (240, 560)
        self.est = Estrutura(nv["cols"], nv["linhas"], nv["sx"], nv["sy"], origem)
        self.jog = Jogador(self.est, self.est.n(0, 0))
        self.cam = Vector2(0, 0)
        self.atualizar_camera(instantaneo=True)

        # tarefas
        self.tarefas = []
        if not vr:
            for (cr, tipo) in nv["tarefas"]:
                self.tarefas.append(dict(no=self.est.n(*cr), tipo=tipo, feito=False))
        self.abrigos = [self.est.n(*cr) for cr in nv["abrigos"]]
        self.no_resgate = self.est.n(*nv["resgate"]) if (nv["resgate"] and not vr) else None
        self.resgate_feito = False
        self.trauma = TEMPO_TRAUMA

        # estado
        self.tempo = float(nv["tempo"]) if not vr else 90.0
        self.pontos = 100.0
        self.infracoes = []
        self.mini = None
        self.mini_ref = None
        self.msg, self.msg_t, self.msg_cor = "", 0.0, C_TEXTO
        self.terminou = None       # None | "sucesso" | "falha"
        self.motivo = ""
        self.mostrar_os = False
        self.pausado = False
        self.altura_max = 0.0
        self.flash = 0.0
        self.queda_anim = 0.0

        # clima
        self.vento = nv["vento_base"]
        self.vento_alvo = nv["vento_base"]
        self.rajada_t = random.uniform(*nv["rajada_intervalo"]) * 0.5
        self.em_rajada = False

        # falha de EPI (itens danificados aprovados por engano)
        self.epi_ruins = [e for e in kit if e.danificado and e.decisao == "aprovado"]
        self.epi_descartados_bons = [e for e in kit if (not e.danificado) and e.decisao == "descartado"]
        self.falha_epi_t = random.uniform(25, 55) if self.epi_ruins else 1e9
        self.ganchos_ok = [True, True]
        self.tempo_total = self.tempo

        # penalidades / bonus do pre-check
        for e in self.epi_descartados_bons:
            self.pontos -= 3
            self.tempo -= 15
        if self.epi_ruins:
            self.registrar("Pre-check falho: EPI danificado liberado para uso ({})".format(
                ", ".join(e.sigla for e in self.epi_ruins)), 12)

        # VR
        self.vr_alvo = None
        self.vr_score = 0
        self.vr_ultimo_gancho = None
        if vr:
            self.jog.ganchos[0] = self.est.n(0, 0)
            self.novo_alvo_vr()

        self.avisar("Pre-check concluido. Ancore o gancho 1 (tecla 1) e comece a subir.", C_AMARELO, 4.5)

    # ---------------------------------------------------------------- util
    def avisar(self, txt, cor=C_TEXTO, t=2.4):
        self.msg, self.msg_cor, self.msg_t = txt, cor, t

    def registrar(self, texto_inf, pontos):
        agora = max(0, int(self.tempo_total - self.tempo))
        for (t, tx, p) in self.infracoes[-3:]:
            if tx == texto_inf and agora - t < 4:
                return
        self.infracoes.append((agora, texto_inf, pontos))
        self.pontos = max(0.0, self.pontos - pontos)
        self.flash = 0.35
        self.avisar("INFRACAO: " + texto_inf, C_VERMELHO, 3.0)

    def tarefas_pendentes(self):
        return [t for t in self.tarefas if not t["feito"]]

    def novo_alvo_vr(self):
        atual = self.jog.a
        candidatos = []
        for i in range(len(self.est.nodes)):
            d = self.est.pos(i).distance_to(self.est.pos(atual))
            if 1.5 * self.nv["sx"] < d < 3.5 * self.nv["sx"]:
                candidatos.append(i)
        self.vr_alvo = random.choice(candidatos) if candidatos else random.randrange(len(self.est.nodes))

    # ------------------------------------------------------------- eventos
    def evento(self, ev):
        if self.terminou:
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.app.trocar(CenaRelatorio(self.app, self))
            return

        if self.mini:
            self.mini.evento(ev)
            return

        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                self.pausado = not self.pausado
            elif ev.key == pygame.K_TAB:
                self.mostrar_os = not self.mostrar_os
            elif ev.key in (pygame.K_1, pygame.K_KP1):
                self.acionar_gancho(0)
            elif ev.key in (pygame.K_2, pygame.K_KP2):
                self.acionar_gancho(1)
            elif ev.key == pygame.K_e:
                self.tentar_tarefa()
            elif ev.key == pygame.K_r:
                self.tentar_resgate()

    def acionar_gancho(self, i):
        if not self.ganchos_ok[i]:
            self.avisar("Gancho {} inoperante (EPI danificado)!".format(i + 1), C_VERMELHO)
            return
        ok, msg = self.jog.alternar_gancho(i)
        if not ok:
            self.avisar(msg, C_VERMELHO)
            if "NEGADO" in msg:
                self.registrar("Tentativa de desconectar os dois ganchos em altura", 6)
        elif msg.startswith("PERIGO"):
            self.avisar(msg, C_VERMELHO, 3.0)
            self.registrar("Permanencia em altura sem nenhum ponto de ancoragem", 10)
        else:
            self.avisar(msg, C_VERDE, 1.2)
            if self.vr and self.jog.ganchos[i] == self.vr_alvo:
                if self.vr_ultimo_gancho == i:
                    self.avisar("Alterne os ganchos! Use o outro talabarte.", C_LARANJA)
                else:
                    self.vr_score += 1
                    self.vr_ultimo_gancho = i
                    self.tempo = min(90.0, self.tempo + 4.0)
                    self.avisar("ANCORAGEM CORRETA +4s", C_VERDE, 1.2)
                    self.novo_alvo_vr()

    def tentar_tarefa(self):
        if self.vr:
            return
        for t in self.tarefas:
            if t["feito"]:
                continue
            if self.jog.pos.distance_to(self.est.pos(t["no"])) < 46:
                if self.jog.ancorado < 2:
                    self.registrar("Trabalho iniciado sem os dois ganchos ancorados", 8)
                    self.avisar("Ancore os DOIS ganchos antes de trabalhar!", C_VERMELHO)
                    return
                if self.vento > LIMITE_VENTO:
                    self.registrar("Tarefa iniciada com vento acima do limite", 10)
                    self.avisar("Vento acima do limite! Aguarde no abrigo.", C_VERMELHO)
                    return
                self.mini = MINIJOGOS[t["tipo"]]()
                self.mini_ref = t
                return
        self.avisar("Nenhuma estacao de manutencao ao alcance.", C_TEXTO_FRACO, 1.5)

    def tentar_resgate(self):
        if self.no_resgate is None or self.resgate_feito:
            return
        if self.jog.pos.distance_to(self.est.pos(self.no_resgate)) > 52:
            self.avisar("Aproxime-se do colega suspenso.", C_TEXTO_FRACO, 1.5)
            return
        if self.jog.ancorado < 2:
            self.registrar("Manobra de resgate sem dupla ancoragem", 10)
            self.avisar("Resgate exige os DOIS ganchos ancorados!", C_VERMELHO)
            return
        altura = self.est.altura_metros(self.est.pos(self.no_resgate))
        self.mini = MiniResgate(altura)
        self.mini_ref = "resgate"

    # ----------------------------------------------------------- atualizar
    def atualizar(self, dt):
        if self.terminou:
            self.queda_anim += dt
            return
        if self.pausado:
            return

        if self.mini:
            self.mini.atualizar(dt)
            self.atualizar_clima(dt)
            if self.mini.concluido:
                self.concluir_mini()
            return

        self.tempo -= dt
        self.msg_t = max(0.0, self.msg_t - dt)
        self.flash = max(0.0, self.flash - dt)
        self.jog.bloqueado_msg = max(0.0, self.jog.bloqueado_msg - dt)

        if self.tempo <= 0:
            if self.vr:
                self.finalizar(True, "Tempo esgotado - sessao VR encerrada")
            else:
                self.finalizar(False, "Tempo da ordem de servico esgotado")
            return

        self.atualizar_clima(dt)
        self.atualizar_epi(dt)

        teclas = pygame.key.get_pressed()
        self.jog.agachado = teclas[pygame.K_LCTRL] or teclas[pygame.K_RCTRL]

        d = Vector2(0, 0)
        if teclas[pygame.K_a] or teclas[pygame.K_LEFT]:
            d.x -= 1
        if teclas[pygame.K_d] or teclas[pygame.K_RIGHT]:
            d.x += 1
        if teclas[pygame.K_w] or teclas[pygame.K_UP]:
            d.y -= 1
        if teclas[pygame.K_s] or teclas[pygame.K_DOWN]:
            d.y += 1

        if self.jog.suspenso > 0:
            self.jog.suspenso -= dt
        else:
            res = self.jog.mover(d, dt)
            if res == "QUEDA_LIVRE":
                self.registrar("Deslocamento em altura com os dois ganchos desconectados", 100)
                self.finalizar(False, "QUEDA LIVRE: deslocamento sem nenhum gancho ancorado")
                return
            if res == "TENSIONADO":
                self.avisar("Talabarte esticado - reposicione um gancho.", C_LARANJA, 1.0)
            elif res == "BLOQUEADO_SOLO":
                self.avisar("Ancore um gancho (tecla 1 ou 2) antes de subir.", C_LARANJA, 1.2)

        self.altura_max = max(self.altura_max, self.jog.altura())

        self.atualizar_equilibrio(dt, d)
        self.atualizar_objetivos(dt)
        self.atualizar_camera()

    def atualizar_clima(self, dt):
        self.rajada_t -= dt
        if self.rajada_t <= 0:
            self.em_rajada = not self.em_rajada
            if self.em_rajada:
                self.vento_alvo = random.uniform(self.nv["vento_base"] + 2, self.nv["vento_pico"])
                self.rajada_t = random.uniform(5, 11)
                if self.vento_alvo > LIMITE_VENTO:
                    self.avisar("ALERTA: rajada acima do limite! Procure abrigo.", C_LARANJA, 3.0)
            else:
                self.vento_alvo = random.uniform(self.nv["vento_base"] * 0.6, self.nv["vento_base"] + 1.5)
                self.rajada_t = random.uniform(*self.nv["rajada_intervalo"])
        self.vento += (self.vento_alvo - self.vento) * min(1.0, dt * 0.9)
        self.vento += math.sin(pygame.time.get_ticks() * 0.004) * 0.05

    def atualizar_epi(self, dt):
        self.falha_epi_t -= dt
        if self.falha_epi_t <= 0 and self.epi_ruins:
            e = self.epi_ruins.pop(0)
            self.falha_epi_t = random.uniform(35, 70) if self.epi_ruins else 1e9
            if e.sigla in ("TAL", "MSQ") and all(self.ganchos_ok):
                idx = random.choice([0, 1])
                self.ganchos_ok[idx] = False
                if self.jog.ganchos[idx] is not None:
                    self.jog.ganchos[idx] = None
                self.registrar("Falha do {}: gancho {} inutilizado em servico".format(e.sigla, idx + 1), 15)
            elif e.sigla == "TRQ":
                self.registrar("Trava-quedas nao bloqueou em teste de campo", 15)
                self.jog.equilibrio = min(self.jog.equilibrio, 40)
            else:
                self.registrar("Falha em servico do EPI {} aprovado no pre-check".format(e.sigla), 12)
                self.jog.equilibrio = max(10, self.jog.equilibrio - 25)

    def em_abrigo(self):
        for n in self.abrigos:
            if self.jog.pos.distance_to(self.est.pos(n)) < 60:
                return True
        return self.jog.no_solo()

    def atualizar_equilibrio(self, dt, direcao):
        excesso = self.vento - LIMITE_VENTO
        protegido = self.em_abrigo() or (self.jog.agachado and self.jog.ancorado >= 2)
        if excesso > 0 and not protegido:
            dreno = (6 + excesso * 5) * dt
            if direcao.length_squared() > 0:
                dreno *= 1.9
            self.jog.equilibrio -= dreno
            if random.random() < dt * 0.6:
                self.registrar("Atividade mantida com vento de {:.1f} m/s".format(self.vento), 4)
        else:
            self.jog.equilibrio = min(100.0, self.jog.equilibrio + 13 * dt)

        if self.jog.equilibrio <= 0:
            self.jog.equilibrio = 0
            if self.jog.ancorado == 0:
                self.finalizar(False, "Perda de equilibrio sem ancoragem: queda fatal")
            else:
                self.jog.equilibrio = 55.0
                self.jog.suspenso = 2.6
                self.registrar("Queda contida pelo talabarte apos perda de equilibrio", 18)
                self.avisar("QUEDA CONTIDA! Reestabelecendo posicao...", C_VERMELHO, 2.6)

    def atualizar_objetivos(self, dt):
        if self.vr:
            return
        if self.no_resgate is not None and not self.resgate_feito:
            self.trauma -= dt
            if self.trauma <= 0:
                self.finalizar(False, "Trauma por suspensao: o colega nao resistiu a espera")
                return
        if not self.tarefas_pendentes() and (self.no_resgate is None or self.resgate_feito):
            if self.jog.no_solo():
                self.finalizar(True, "Servico concluido e equipe no solo")
            else:
                self.avisar("Todas as tarefas concluidas. Desca ate o solo com seguranca.", C_VERDE, 2.0)

    def concluir_mini(self):
        m = self.mini
        if self.mini_ref == "resgate":
            self.resgate_feito = True
            penal = m.erros * 5
            if penal:
                self.registrar("Descida de resgate acima da velocidade segura ({} eventos)".format(m.erros), penal)
            self.avisar("RESGATE CONCLUIDO. Vitima entregue ao socorro.", C_VERDE, 3.5)
        else:
            self.mini_ref["feito"] = True
            penal = m.erros * 2
            if penal:
                self.registrar("Erros de execucao em {}".format(NOME_TAREFA[self.mini_ref["tipo"]]), min(12, penal))
            else:
                self.pontos = min(100.0, self.pontos + 2)
                self.avisar("Tarefa concluida sem erros. +2 pts", C_VERDE, 2.5)
        self.mini = None
        self.mini_ref = None

    def finalizar(self, sucesso, motivo):
        if self.terminou:
            return
        self.terminou = "sucesso" if sucesso else "falha"
        self.motivo = motivo
        if self.vr:
            rec = self.app.progresso.get("recorde_vr", 0)
            if self.vr_score > rec:
                self.app.progresso["recorde_vr"] = self.vr_score
        elif sucesso:
            nota = int(self.pontos)
            best = self.app.progresso["melhores"].get(str(self.nivel_idx), 0)
            self.app.progresso["melhores"][str(self.nivel_idx)] = max(best, nota)
            if self.nivel_idx + 1 >= self.app.progresso["desbloqueado"]:
                self.app.progresso["desbloqueado"] = min(len(NIVEIS), self.nivel_idx + 2)
        self.app.salvar()

    def atualizar_camera(self, instantaneo=False):
        alvo = Vector2(self.jog.pos.x - LARGURA * 0.42, self.jog.pos.y - ALTURA * 0.56)
        r = self.est.rect
        alvo.x = max(r.left - 60, min(r.right + 60 - LARGURA, alvo.x))
        alvo.y = max(r.top - 80, min(r.bottom + 40 - ALTURA, alvo.y))
        if instantaneo:
            self.cam = alvo
        else:
            self.cam += (alvo - self.cam) * 0.11

    # -------------------------------------------------------------- desenho
    def desenhar(self, surf):
        self.fundo.desenhar(surf, self.cam, self.vento)
        self.desenhar_estrutura(surf)
        self.desenhar_estacoes(surf)
        self.jog.desenhar(surf, self.cam)
        self.desenhar_particulas_vento(surf)
        self.desenhar_hud(surf)
        if self.mostrar_os:
            self.desenhar_os(surf)
        if self.mini:
            self.mini.desenhar(surf)
        if self.flash > 0:
            v = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
            v.fill((220, 40, 40, int(90 * self.flash / 0.35)))
            surf.blit(v, (0, 0))
        if self.pausado:
            self.desenhar_pausa(surf)
        if self.terminou:
            self.desenhar_fim(surf)

    def desenhar_estrutura(self, surf):
        cam = self.cam
        # chao
        chao_y = self.est.chao_y - cam.y
        if chao_y < ALTURA:
            pygame.draw.rect(surf, (46, 52, 46), (0, chao_y, LARGURA, ALTURA - chao_y))
            pygame.draw.line(surf, (70, 78, 70), (0, chao_y), (LARGURA, chao_y), 3)

        # diagonais decorativas
        for c in range(self.est.cols - 1):
            for r in range(self.est.linhas - 1):
                p1 = self.est.pos(self.est.n(c, r)) - cam
                p2 = self.est.pos(self.est.n(c + 1, r + 1)) - cam
                if -100 < p1.y < ALTURA + 100:
                    pygame.draw.line(surf, C_ACO_ESC, p1, p2, 3)

        # vigas
        for (a, b) in self.est.edges:
            p1 = self.est.pos(a) - cam
            p2 = self.est.pos(b) - cam
            if max(p1.y, p2.y) < -60 or min(p1.y, p2.y) > ALTURA + 60:
                continue
            pygame.draw.line(surf, C_ACO_ESC, p1, p2, 9)
            pygame.draw.line(surf, C_ACO, p1, p2, 6)
            pygame.draw.line(surf, C_ACO_LUZ, (p1.x, p1.y - 2), (p2.x, p2.y - 2), 1)

        # nos / pontos de ancoragem
        for i, p0 in enumerate(self.est.nodes):
            p = p0 - cam
            if not (-40 < p.y < ALTURA + 40):
                continue
            ancorado = i in self.jog.ganchos
            perto = self.jog.pos.distance_to(p0) <= min(RAIO_ANCORAGEM, CABO_MAX)
            if i in self.abrigos:
                pygame.draw.circle(surf, C_AZUL, (int(p.x), int(p.y)), 15, 2)
                texto(surf, "ABRIGO", (int(p.x), int(p.y) - 26), "mono_p", C_AZUL, centro=True)
            cor = C_VERDE if ancorado else (C_AMARELO if perto else (110, 108, 86))
            pygame.draw.circle(surf, (25, 28, 34), (int(p.x), int(p.y)), 9)
            pygame.draw.circle(surf, cor, (int(p.x), int(p.y)), 8, 2)
            pygame.draw.circle(surf, cor, (int(p.x), int(p.y)), 3)

        if self.vr and self.vr_alvo is not None:
            p = self.est.pos(self.vr_alvo) - self.cam
            raio = 18 + math.sin(pygame.time.get_ticks() * 0.008) * 5
            pygame.draw.circle(surf, C_LARANJA, (int(p.x), int(p.y)), int(raio), 3)
            texto(surf, "ANCORAR AQUI", (int(p.x), int(p.y) - 34), "mono_p", C_LARANJA, centro=True)

    def desenhar_estacoes(self, surf):
        for t in self.tarefas:
            p = self.est.pos(t["no"]) - self.cam
            if not (-60 < p.y < ALTURA + 60):
                continue
            if t["feito"]:
                pygame.draw.circle(surf, C_VERDE, (int(p.x), int(p.y - 26)), 12, 2)
                texto(surf, "OK", (int(p.x), int(p.y - 26)), "mono_p", C_VERDE, centro=True)
                continue
            pulso = 3 + math.sin(pygame.time.get_ticks() * 0.006) * 2
            r = pygame.Rect(0, 0, 30, 30)
            r.center = (int(p.x), int(p.y - 30))
            pygame.draw.rect(surf, (52, 42, 20), r, border_radius=6)
            pygame.draw.rect(surf, C_AMARELO, r.inflate(pulso, pulso), 2, border_radius=6)
            icone = {"solda": "SLD", "aperto": "TRQ", "lampada": "LMP", "sequencia": "END"}[t["tipo"]]
            texto(surf, icone, r.center, "mono_p", C_AMARELO, centro=True)
            if self.jog.pos.distance_to(self.est.pos(t["no"])) < 46:
                texto(surf, "[E] " + NOME_TAREFA[t["tipo"]], (int(p.x), int(p.y - 58)), "ui_p", C_BRANCO, centro=True)

        if self.no_resgate is not None and not self.resgate_feito:
            p = self.est.pos(self.no_resgate) - self.cam
            bal = math.sin(pygame.time.get_ticks() * 0.002) * 6
            cx, cy = int(p.x + bal), int(p.y + 44)
            desenhar_cabo(surf, p, (cx, cy - 14), C_VERMELHO, sag=6, espessura=2)
            pygame.draw.rect(surf, (200, 60, 60), (cx - 7, cy - 14, 14, 20), border_radius=4)
            pygame.draw.circle(surf, (222, 190, 160), (cx, cy - 20), 6)
            pygame.draw.circle(surf, C_BRANCO, (cx, cy - 22), 7)
            pygame.draw.line(surf, (200, 60, 60), (cx, cy + 6), (cx - 5, cy + 18), 3)
            pygame.draw.line(surf, (200, 60, 60), (cx, cy + 6), (cx + 5, cy + 18), 3)
            texto(surf, "COLEGA SUSPENSO", (cx, cy - 46), "mono_p", C_VERMELHO, centro=True)
            if self.jog.pos.distance_to(self.est.pos(self.no_resgate)) < 52:
                texto(surf, "[R] INICIAR RESGATE", (cx, cy - 66), "ui_p", C_BRANCO, centro=True)

    def desenhar_particulas_vento(self, surf):
        if self.vento < 4:
            return
        n = int(self.vento * 3)
        t = pygame.time.get_ticks() * 0.35
        for i in range(n):
            x = (i * 137 + t * (1 + self.vento * 0.16)) % (LARGURA + 200) - 100
            y = (i * 271 + self.cam.y * 0.4) % ALTURA
            comp = 8 + self.vento * 2
            alpha = 60 if self.vento < LIMITE_VENTO else 120
            s = pygame.Surface((int(comp), 2), pygame.SRCALPHA)
            s.fill((255, 255, 255, alpha))
            surf.blit(s, (x, y))

    def desenhar_hud(self, surf):
        # topo
        painel(surf, (16, 12, 420, 96), alpha=210)
        cor_p = C_VERDE if self.pontos >= 85 else (C_AMARELO if self.pontos >= 60 else C_VERMELHO)
        texto(surf, "SEGURANCA", (32, 24), "mono_p", C_TEXTO_FRACO)
        texto(surf, "{:.0f}".format(self.pontos), (150, 18), "sub", cor_p)
        barra(surf, (32, 50, 180, 10), self.pontos / 100.0, cor_p)

        texto(surf, "ALTURA", (250, 24), "mono_p", C_TEXTO_FRACO)
        texto(surf, "{:.1f} m".format(self.jog.altura()), (250, 40), "hud", C_TEXTO)
        mm, ss = int(self.tempo) // 60, int(self.tempo) % 60
        texto(surf, "TEMPO", (340, 24), "mono_p", C_TEXTO_FRACO)
        texto(surf, "{:02d}:{:02d}".format(mm, ss), (340, 40),
              "hud", C_VERMELHO if self.tempo < 45 else C_TEXTO)
        texto(surf, "EQUILIBRIO", (32, 70), "mono_p", C_TEXTO_FRACO)
        barra(surf, (120, 70, 290, 12), self.jog.equilibrio / 100.0,
              C_VERDE if self.jog.equilibrio > 50 else (C_AMARELO if self.jog.equilibrio > 25 else C_VERMELHO))

        # anemometro
        self.desenhar_anemometro(surf, (LARGURA - 118, 96))

        # ganchos
        painel(surf, (16, ALTURA - 96, 360, 80), alpha=210)
        texto(surf, "TALABARTE DUPLO", (32, ALTURA - 88), "mono_p", C_TEXTO_FRACO)
        for i in range(2):
            y = ALTURA - 64 + i * 26
            g = self.jog.ganchos[i]
            cor = [C_VERDE, C_AZUL][i]
            if not self.ganchos_ok[i]:
                estado, cor = "INOPERANTE (EPI danificado)", C_VERMELHO
            elif g is None:
                estado, cor = "LIVRE", C_VERMELHO
            else:
                d = self.jog.pos.distance_to(self.est.pos(g))
                estado = "ANCORADO  ({:.0f}/{:.0f} cm)".format(d, CABO_MAX)
                if d > CABO_MAX * 0.85:
                    cor = C_LARANJA
            pygame.draw.circle(surf, cor, (40, y + 7), 7)
            texto(surf, "[{}] GANCHO {} : {}".format(i + 1, i + 1, estado), (56, y), "mono_p", cor)

        if self.jog.ancorado == 0 and not self.jog.no_solo():
            if (pygame.time.get_ticks() // 300) % 2 == 0:
                texto(surf, "!! SEM ANCORAGEM - NAO SE MOVA !!", (LARGURA // 2, 140),
                      "ui_g", C_VERMELHO, centro=True, sombra=True)

        # objetivos resumidos
        if not self.vr:
            pend = len(self.tarefas_pendentes())
            painel(surf, (LARGURA - 300, ALTURA - 96, 284, 80), alpha=210)
            texto(surf, "ORDEM DE SERVICO  [TAB]", (LARGURA - 286, ALTURA - 88), "mono_p", C_TEXTO_FRACO)
            texto(surf, "Tarefas restantes: {}".format(pend), (LARGURA - 286, ALTURA - 64), "ui_p", C_TEXTO)
            if self.no_resgate is not None and not self.resgate_feito:
                cor = C_VERMELHO if self.trauma < 45 else C_LARANJA
                texto(surf, "Resgate - trauma em {:02d}:{:02d}".format(int(self.trauma) // 60, int(self.trauma) % 60),
                      (LARGURA - 286, ALTURA - 40), "ui_p", cor)
            elif self.resgate_feito:
                texto(surf, "Resgate concluido", (LARGURA - 286, ALTURA - 40), "ui_p", C_VERDE)
        else:
            painel(surf, (LARGURA - 300, ALTURA - 96, 284, 80), alpha=210)
            texto(surf, "DESAFIO VR", (LARGURA - 286, ALTURA - 88), "mono_p", C_TEXTO_FRACO)
            texto(surf, "Ancoragens corretas: {}".format(self.vr_score),
                  (LARGURA - 286, ALTURA - 62), "ui", C_AMARELO)
            texto(surf, "Recorde: {}".format(self.app.progresso.get("recorde_vr", 0)),
                  (LARGURA - 286, ALTURA - 38), "ui_p", C_TEXTO_FRACO)

        if self.msg_t > 0:
            largura_msg = FONTES["ui"].size(self.msg)[0] + 40
            r = pygame.Rect(0, 0, largura_msg, 40)
            r.center = (LARGURA // 2, ALTURA - 130)
            painel(surf, r, alpha=225, borda=self.msg_cor)
            texto(surf, self.msg, r.center, "ui", self.msg_cor, centro=True)

    def desenhar_anemometro(self, surf, centro):
        cx, cy = centro
        raio = 52
        painel(surf, (cx - 100, cy - 84, 200, 168), alpha=215)
        texto(surf, "ANEMOMETRO", (cx, cy - 70), "mono_p", C_TEXTO_FRACO, centro=True)
        pygame.draw.circle(surf, (30, 36, 46), (cx, cy), raio)
        for i in range(0, 21, 2):
            ang = math.radians(210 - i * 10)
            r1 = raio - (10 if i % 4 == 0 else 5)
            cor = C_VERMELHO if i > LIMITE_VENTO else C_TEXTO_FRACO
            pygame.draw.line(surf, cor,
                             (cx + math.cos(ang) * r1, cy - math.sin(ang) * r1),
                             (cx + math.cos(ang) * raio, cy - math.sin(ang) * raio), 2)
        v = max(0.0, min(20.0, self.vento))
        ang = math.radians(210 - v * 10)
        cor_ag = C_VERMELHO if self.vento > LIMITE_VENTO else C_VERDE
        pygame.draw.line(surf, cor_ag, (cx, cy),
                         (cx + math.cos(ang) * (raio - 8), cy - math.sin(ang) * (raio - 8)), 4)
        pygame.draw.circle(surf, C_ACO_LUZ, (cx, cy), 5)
        texto(surf, "{:.1f} m/s".format(self.vento), (cx, cy + 34), "hud", cor_ag, centro=True)
        if self.vento > LIMITE_VENTO:
            texto(surf, "ACIMA DO LIMITE", (cx, cy + 58), "mono_p", C_VERMELHO, centro=True)
        else:
            texto(surf, "limite {:.0f} m/s".format(LIMITE_VENTO), (cx, cy + 58), "mono_p", C_TEXTO_FRACO, centro=True)

    def desenhar_os(self, surf):
        r = pygame.Rect(0, 0, 640, 440)
        r.center = (LARGURA // 2, ALTURA // 2)
        veu = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        veu.fill((0, 0, 0, 130))
        surf.blit(veu, (0, 0))
        painel(surf, r)
        texto(surf, "ORDEM DE SERVICO", (r.centerx, r.y + 26), "sub", C_AMARELO, centro=True)
        texto(surf, self.nv["nome"], (r.centerx, r.y + 60), "ui_p", C_TEXTO_FRACO, centro=True)
        y = r.y + 96
        for t in self.tarefas:
            cor = C_VERDE if t["feito"] else C_TEXTO
            marca = "[X]" if t["feito"] else "[ ]"
            alt = self.est.altura_metros(self.est.pos(t["no"]))
            texto(surf, "{} {}  -  {:.0f} m".format(marca, NOME_TAREFA[t["tipo"]], alt),
                  (r.x + 40, y), "ui_p", cor)
            y += 28
        if self.no_resgate is not None:
            cor = C_VERDE if self.resgate_feito else C_VERMELHO
            texto(surf, "{} Resgate do colega suspenso".format("[X]" if self.resgate_feito else "[ ]"),
                  (r.x + 40, y), "ui_p", cor)
            y += 28
        y += 10
        texto(surf, "EPI EM USO", (r.x + 40, y), "ui_g", C_LARANJA); y += 28
        for e in self.kit:
            if e.decisao == "aprovado":
                texto(surf, "- {} ({})".format(e.nome, e.sigla), (r.x + 50, y), "ui_p", C_TEXTO)
                y += 22
        texto(surf, "TAB para fechar", (r.centerx, r.bottom - 26), "ui_p", C_TEXTO_FRACO, centro=True)

    def desenhar_pausa(self, surf):
        veu = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        veu.fill((0, 0, 0, 170))
        surf.blit(veu, (0, 0))
        texto(surf, "PAUSA", (LARGURA // 2, ALTURA // 2 - 40), "titulo", C_AMARELO, centro=True)
        texto(surf, "ESC retoma  |  Q abandona a missao", (LARGURA // 2, ALTURA // 2 + 20),
              "ui", C_TEXTO_FRACO, centro=True)
        if pygame.key.get_pressed()[pygame.K_q]:
            self.finalizar(False, "Missao abandonada pelo inspetor")
            self.pausado = False

    def desenhar_fim(self, surf):
        veu = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        veu.fill((0, 0, 0, min(200, int(self.queda_anim * 320))))
        surf.blit(veu, (0, 0))
        ok = self.terminou == "sucesso"
        texto(surf, "MISSAO CONCLUIDA" if ok else "MISSAO FALHOU",
              (LARGURA // 2, ALTURA // 2 - 50), "titulo", C_VERDE if ok else C_VERMELHO, centro=True, sombra=True)
        texto(surf, self.motivo, (LARGURA // 2, ALTURA // 2 + 10), "ui", C_TEXTO, centro=True)
        texto(surf, "ENTER para ver o relatorio", (LARGURA // 2, ALTURA // 2 + 60),
              "ui_p", C_TEXTO_FRACO, centro=True)


# ------------------------------------------------------------- RELATORIO ----
class CenaRelatorio(Cena):
    def __init__(self, app, jogo):
        super().__init__(app)
        self.j = jogo
        self.fundo = Fundo(31)
        self.b_menu = Botao((LARGURA // 2 - 260, ALTURA - 76, 240, 46), "MENU PRINCIPAL [ESC]", pygame.K_ESCAPE)
        self.b_rep = Botao((LARGURA // 2 + 20, ALTURA - 76, 240, 46), "REPETIR OBRA [ENTER]", pygame.K_RETURN, C_AMARELO)
        self.scroll = 0

    def evento(self, ev):
        if self.b_menu.clicado(ev):
            self.app.trocar(CenaMenu(self.app))
        if self.b_rep.clicado(ev):
            self.app.trocar(CenaPreCheck(self.app, self.j.nivel_idx, vr=self.j.vr))
        if ev.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, self.scroll - ev.y * 30)

    def atualizar(self, dt):
        mpos = pygame.mouse.get_pos()
        self.b_menu.atualizar(mpos)
        self.b_rep.atualizar(mpos)

    def classificacao(self):
        p = self.j.pontos
        if self.j.terminou != "sucesso":
            return "REPROVADO", C_VERMELHO
        if p >= 95 and not self.j.infracoes:
            return "OURO - CONFORMIDADE TOTAL", C_AMARELO
        if p >= 80:
            return "PRATA - CONFORME COM RESSALVAS", (196, 206, 216)
        if p >= 60:
            return "BRONZE - AJUSTES NECESSARIOS", C_LARANJA
        return "APROVADO COM RESTRICOES", C_VERMELHO

    def desenhar(self, surf):
        self.fundo.desenhar(surf, Vector2(0, 0))
        veu = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        veu.fill((0, 0, 0, 150))
        surf.blit(veu, (0, 0))

        r = pygame.Rect(90, 40, LARGURA - 180, ALTURA - 140)
        painel(surf, r)
        titulo = "RELATORIO DE SEGURANCA - SESSAO VR" if self.j.vr else "RELATORIO DE SEGURANCA DO SERVICO"
        texto(surf, titulo, (r.centerx, r.y + 26), "sub", C_AMARELO, centro=True)
        nome = "Desafio VR - Sprint de Ancoragem" if self.j.vr else self.j.nv["nome"]
        texto(surf, nome, (r.centerx, r.y + 62), "ui_p", C_TEXTO_FRACO, centro=True)

        cls, cor_cls = self.classificacao()
        texto(surf, cls, (r.centerx, r.y + 100), "ui_g", cor_cls, centro=True)

        # coluna esquerda: numeros
        x = r.x + 40
        y = r.y + 150
        if self.j.vr:
            texto(surf, "Ancoragens corretas : {}".format(self.j.vr_score), (x, y), "mono", C_TEXTO); y += 26
            texto(surf, "Recorde pessoal     : {}".format(self.app.progresso.get("recorde_vr", 0)),
                  (x, y), "mono", C_AMARELO); y += 26
        else:
            feitas = sum(1 for t in self.j.tarefas if t["feito"])
            texto(surf, "Pontuacao final     : {:.0f} / 100".format(self.j.pontos), (x, y), "mono", C_TEXTO); y += 26
            texto(surf, "Tarefas concluidas  : {}/{}".format(feitas, len(self.j.tarefas)),
                  (x, y), "mono", C_TEXTO); y += 26
            if self.j.no_resgate is not None:
                texto(surf, "Resgate             : {}".format("CONCLUIDO" if self.j.resgate_feito else "NAO REALIZADO"),
                      (x, y), "mono", C_VERDE if self.j.resgate_feito else C_VERMELHO); y += 26
            texto(surf, "Altura maxima       : {:.1f} m".format(self.j.altura_max),
                  (x, y), "mono", C_TEXTO); y += 26
        texto(surf, "Total de infracoes  : {}".format(len(self.j.infracoes)), (x, y), "mono",
              C_VERDE if not self.j.infracoes else C_VERMELHO); y += 36

        # pre-check
        texto(surf, "AUDITORIA DO PRE-CHECK", (x, y), "ui_g", C_LARANJA); y += 30
        acertos = 0
        for e in self.j.kit:
            correto = (e.decisao == "descartado") == e.danificado
            acertos += 1 if correto else 0
            marca = "OK " if correto else "ERRO"
            cor = C_VERDE if correto else C_VERMELHO
            detalhe = e.defeito if e.danificado else "conforme"
            texto(surf, "[{}] {} - {}".format(marca, e.sigla, detalhe[:52]), (x + 8, y), "mono_p", cor)
            y += 21
        y += 6
        texto(surf, "Acertos no pre-check: {}/{}".format(acertos, len(self.j.kit)), (x + 8, y), "mono",
              C_VERDE if acertos == len(self.j.kit) else C_LARANJA)

        # coluna direita: infracoes
        x2 = r.centerx + 30
        y2 = r.y + 150
        texto(surf, "REGISTRO DE INFRACOES", (x2, y2), "ui_g", C_LARANJA); y2 += 30
        if not self.j.infracoes:
            texto(surf, "Nenhuma infracao registrada. Excelente trabalho.", (x2 + 8, y2), "ui_p", C_VERDE)
        else:
            area = r.bottom - 60 - y2
            visiveis = int(area // 44)
            lista = self.j.infracoes[self.scroll // 44:][:visiveis]
            for (t, txt, p) in lista:
                texto(surf, "{:02d}:{:02d}  -{} pts".format(t // 60, t % 60, p), (x2 + 8, y2), "mono_p", C_VERMELHO)
                y2 = texto_bloco(surf, txt, (x2 + 8, y2 + 18), r.right - x2 - 50, "ui_p", C_TEXTO) + 8
            if len(self.j.infracoes) > visiveis:
                texto(surf, "... role a roda do mouse para ver mais",
                      (x2 + 8, r.bottom - 50), "mono_p", C_TEXTO_FRACO)

        self.b_menu.desenhar(surf)
        self.b_rep.desenhar(surf)


# =============================================================================
# 8. APLICACAO
# =============================================================================

class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITULO)
        self.tela = pygame.display.set_mode((LARGURA, ALTURA))
        self.relogio = pygame.time.Clock()
        carregar_fontes()
        self.rodando = True
        self.progresso = {"desbloqueado": 1, "melhores": {}, "recorde_vr": 0}
        self.carregar()
        self.cena = CenaMenu(self)

    # ---- persistencia ----
    def carregar(self):
        try:
            with open(ARQUIVO_SAVE, "r", encoding="utf-8") as f:
                d = json.load(f)
            self.progresso["desbloqueado"] = int(d.get("desbloqueado", 1))
            self.progresso["melhores"] = dict(d.get("melhores", {}))
            self.progresso["recorde_vr"] = int(d.get("recorde_vr", 0))
        except Exception:
            pass

    def salvar(self):
        try:
            with open(ARQUIVO_SAVE, "w", encoding="utf-8") as f:
                json.dump(self.progresso, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def trocar(self, cena):
        self.cena = cena

    def rodar(self):
        while self.rodando:
            dt = min(0.05, self.relogio.tick(FPS) / 1000.0)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.rodando = False
                elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_F1:
                    pygame.display.toggle_fullscreen()
                else:
                    self.cena.evento(ev)
            self.cena.atualizar(dt)
            self.cena.desenhar(self.tela)
            pygame.display.flip()
        self.salvar()
        pygame.quit()
        sys.exit(0)


def main():
    App().rodar()


if __name__ == "__main__":
    main()
