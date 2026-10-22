# -*- coding: utf-8 -*-
"""
===============================================================================
 SKYLINE SAFE: MESTRE DA ALTURA   (versao 6 - Obras 01 a 05)
 Simulacao de Acao / Puzzle de trabalho em altura
 -----------------------------------------------------------------------------
 Requisitos:  Python 3.9+   |   pip install pygame
 Executar:    python skyline_safe.py
===============================================================================
 COMO ADICIONAR NOVAS OBRAS
   Inclua um novo dicionario na lista NIVEIS (secao 6). Ha um modelo
   comentado la. Para um visual novo, adicione uma entrada em TEMAS e um
   ramo em CenaJogo.desenhar_tema().
===============================================================================
"""

import json
import math
import os
import random
import sys
import threading
from array import array

import pygame
from pygame import Vector2

# =============================================================================
# 1. CONFIGURACAO GERAL
# =============================================================================

LARGURA, ALTURA = 1280, 720
FPS = 60
TITULO = "SkyLine Safe: Mestre da Altura"
ARQUIVO_SAVE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skyline_save.json")

CABO_MAX = 185.0          # comprimento util do talabarte (px)
RAIO_ANCORAGEM = 200.0    # alcance do braco (px)
LIMITE_VENTO = 11.0       # m/s: acima disso o servico deve parar
ESCALA_METRO = 22.0       # px por metro
TEMPO_TRAUMA = 150.0      # s ate o trauma por suspensao do colega
TEMPO_PRECHECK_LIVRE = 90.0   # s de pre-check sem penalidade

C_PAINEL = (18, 24, 34)
C_PAINEL_BORDA = (58, 72, 92)
C_TEXTO = (232, 238, 245)
C_TEXTO_FRACO = (150, 164, 182)
C_ACO = (118, 128, 140)
C_ACO_ESC = (72, 80, 92)
C_ACO_LUZ = (166, 176, 188)
C_AMARELO = (247, 196, 40)
C_LARANJA = (240, 132, 42)
C_VERDE = (86, 196, 118)
C_VERMELHO = (222, 72, 72)
C_AZUL = (78, 158, 226)
C_BRANCO = (255, 255, 255)

FONTES = {}


def carregar_fontes():
    mono = "consolas,dejavusansmono,couriernew,monospace"
    ui = "verdana,dejavusans,arial,freesans"
    FONTES["mono"] = pygame.font.SysFont(mono, 16)
    FONTES["mono_p"] = pygame.font.SysFont(mono, 13)
    FONTES["ui"] = pygame.font.SysFont(ui, 17)
    FONTES["ui_p"] = pygame.font.SysFont(ui, 14)
    FONTES["ui_g"] = pygame.font.SysFont(ui, 22, bold=True)
    FONTES["titulo"] = pygame.font.SysFont(ui, 44, bold=True)
    FONTES["sub"] = pygame.font.SysFont(ui, 26, bold=True)
    FONTES["hud"] = pygame.font.SysFont(mono, 15, bold=True)


# =============================================================================
# 2. UTILIDADES DE DESENHO
# =============================================================================

_CACHE_TEXTO = {}


def _render(fonte, msg, cor):
    """Renderiza texto com cache: o mesmo texto nao e redesenhado a cada quadro."""
    try:
        k = (fonte, msg, tuple(cor))
        img = _CACHE_TEXTO.get(k)
        if img is None:
            if len(_CACHE_TEXTO) > 900:
                _CACHE_TEXTO.clear()
            img = FONTES[fonte].render(msg, True, cor)
            _CACHE_TEXTO[k] = img
        return img
    except TypeError:
        return FONTES[fonte].render(msg, True, cor)


def texto(surf, msg, pos, fonte="ui", cor=C_TEXTO, centro=False, direita=False, sombra=False):
    msg = str(msg)
    img = _render(fonte, msg, cor)
    r = img.get_rect()
    if centro:
        r.center = pos
    elif direita:
        r.midright = pos
    else:
        r.topleft = pos
    if sombra:
        surf.blit(_render(fonte, msg, (0, 0, 0)), (r.x + 2, r.y + 2))
    surf.blit(img, r)
    return r


def quebrar_texto(msg, fonte, largura_max):
    linhas, atual = [], ""
    for p in str(msg).split(" "):
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


_CACHE_RISCO = {}


def risco_vento(larg, alpha):
    """Superficie translucida reaproveitada (evita criar dezenas por quadro)."""
    k = (larg, alpha)
    s = _CACHE_RISCO.get(k)
    if s is None:
        s = pygame.Surface((larg, 2), pygame.SRCALPHA)
        s.fill((255, 255, 255, alpha))
        _CACHE_RISCO[k] = s
    return s


_CACHE_PAINEL = {}


def painel(surf, rect, cor=C_PAINEL, borda=C_PAINEL_BORDA, alpha=235, raio=10, larg_borda=2):
    rect = pygame.Rect(rect)
    k = (rect.size, tuple(cor), alpha, raio)
    s = _CACHE_PAINEL.get(k)
    if s is None:
        if len(_CACHE_PAINEL) > 160:
            _CACHE_PAINEL.clear()
        s = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (*cor, alpha), s.get_rect(), border_radius=raio)
        _CACHE_PAINEL[k] = s
    surf.blit(s, rect.topleft)
    pygame.draw.rect(surf, borda, rect, larg_borda, border_radius=raio)


def barra(surf, rect, frac, cor, fundo=(40, 48, 60), borda=C_PAINEL_BORDA, raio=4):
    rect = pygame.Rect(rect)
    frac = max(0.0, min(1.0, frac))
    pygame.draw.rect(surf, fundo, rect, border_radius=raio)
    if frac > 0:
        pygame.draw.rect(surf, cor, (rect.x, rect.y, max(3, int(rect.w * frac)), rect.h), border_radius=raio)
    pygame.draw.rect(surf, borda, rect, 1, border_radius=raio)


def gradiente_vertical(surf, rect, cor_topo, cor_base):
    rect = pygame.Rect(rect)
    for i in range(rect.h):
        t = i / max(1, rect.h - 1)
        c = tuple(int(cor_topo[k] + (cor_base[k] - cor_topo[k]) * t) for k in range(3))
        pygame.draw.line(surf, c, (rect.x, rect.y + i), (rect.right, rect.y + i))


def desenhar_cabo(surf, p1, p2, cor, sag=18, espessura=3):
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
        return self.tecla is not None and ev.type == pygame.KEYDOWN and ev.key == self.tecla

    def desenhar(self, surf):
        c = self.cor if not self.hover else tuple(min(255, v + 40) for v in self.cor)
        painel(surf, self.rect, cor=(c[0] // 4, c[1] // 4, c[2] // 4), borda=c, alpha=230, raio=8)
        texto(surf, self.rotulo, self.rect.center, "ui", C_BRANCO if self.hover else C_TEXTO, centro=True)


# =============================================================================
# 3. AUDIO (tudo sintetizado por codigo - sem arquivos externos)
# =============================================================================

def _hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12.0)


class Audio:
    """Efeitos e trilhas gerados proceduralmente. Sem placa de som o jogo
    segue normalmente em silencio. Tecla M liga/desliga."""

    def __init__(self):
        self.ativo = False
        self.mudo = False
        self.sons = {}
        self.faixas = {}
        self.desejada = None
        self.tocando = None
        self.nivel_vento = 0.0
        self.ultimo = {}
        self.volume = 1.0
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            info = pygame.mixer.get_init()
            if not info or info[1] not in (-16, 32784):
                return
            self.sr, _fmt, self.ch = info
            pygame.mixer.set_num_channels(16)
            pygame.mixer.set_reserved(2)
            self.c_musica = pygame.mixer.Channel(0)
            self.c_vento = pygame.mixer.Channel(1)
            self._gerar_efeitos()
            self.ativo = True
            threading.Thread(target=self._gerar_faixas, daemon=True).start()
        except Exception:
            self.ativo = False

    # ---- sintese ---------------------------------------------------------
    def _som(self, amostras, vol=1.0):
        a = array("h")
        for s in amostras:
            v = int(max(-1.0, min(1.0, s * vol)) * 30000)
            for _ in range(self.ch):
                a.append(v)
        return pygame.mixer.Sound(buffer=a.tobytes())

    def _n(self, dur):
        return int(self.sr * dur)

    def _tom(self, f, dur, vol=1.0, atk=0.005, rel=0.04, forma="seno"):
        sr, n, w = self.sr, self._n(dur), 6.283185307 * f
        out = []
        for i in range(n):
            t = i / sr
            e = max(0.0, min(1.0, t / atk, (dur - t) / rel))
            x = math.sin(w * t)
            if forma == "quad":
                x = 1.0 if x >= 0 else -1.0
            out.append(x * vol * e)
        return out

    def _ruido(self, dur, vol=1.0, decai=6.0, suave=0.0):
        n, y, out = self._n(dur), 0.0, []
        for i in range(n):
            y = y * suave + random.uniform(-1, 1) * (1 - suave)
            out.append(y * vol * math.exp(-decai * i / n))
        return out

    def _mix(self, *camadas):
        n = max(int(self.sr * o) + len(l) for o, l in camadas)
        out = [0.0] * n
        for o, l in camadas:
            k = int(self.sr * o)
            for i, v in enumerate(l):
                out[k + i] += v
        return out

    def _gerar_efeitos(self):
        T, R, M, S = self._tom, self._ruido, self._mix, self._som
        s = self.sons
        s["clique"] = S(M((0, R(0.04, 0.9, 30)), (0, T(2200, 0.05, 0.35, 0.001, 0.03)),
                          (0.07, R(0.05, 0.8, 26)), (0.07, T(1500, 0.06, 0.35, 0.001, 0.04))))
        s["solta"] = S(M((0, R(0.05, 0.8, 22, 0.5)), (0, T(900, 0.07, 0.35, 0.001, 0.05))))
        s["bip"] = S(T(1300, 0.13, 0.5))
        s["estalo"] = S(R(0.28, 0.9, 9, 0.55))
        s["alarme"] = S(M((0, T(880, 0.18, 0.45, 0.005, 0.03, "quad")),
                          (0.2, T(620, 0.18, 0.45, 0.005, 0.03, "quad"))), 0.7)
        s["ok"] = S(M((0, T(660, 0.09, 0.5)), (0.09, T(990, 0.14, 0.5, 0.005, 0.08))))
        s["erro"] = S(T(170, 0.22, 0.6, 0.005, 0.08, "quad"), 0.7)
        s["ui"] = S(T(1000, 0.03, 0.4, 0.002, 0.02))
        s["sucesso"] = S(M((0, T(523, 0.2, 0.45)), (0.18, T(659, 0.2, 0.45)),
                           (0.36, T(784, 0.2, 0.45)), (0.54, T(1047, 0.6, 0.5, 0.01, 0.4))))
        s["falha"] = S(M((0, T(392, 0.3, 0.5)), (0.28, T(330, 0.3, 0.5)),
                         (0.56, T(262, 0.3, 0.5)), (0.84, T(196, 0.8, 0.5, 0.01, 0.5))))
        # vento (loop sem emenda)
        n, x = self._n(3.0), self._n(0.25)
        y, ruido = 0.0, []
        for _ in range(n + x):
            y = y * 0.93 + random.uniform(-1, 1) * 0.07
            ruido.append(y)
        loop = []
        for i in range(n):
            v = ruido[i] * (i / x) + ruido[n + i] * (1 - i / x) if i < x else ruido[i]
            loop.append(v * 4.0 * (0.65 + 0.35 * math.sin(6.283185307 * i / n)))
        s["vento"] = S(loop, 0.8)

    def _ciclo(self, f):
        p = max(2, int(round(self.sr / f)))
        return [math.sin(6.283185307 * k / p) for k in range(p)], p

    def _faixa(self, acordes, dur, vol=1.0, pluck=None, pluck_int=1.5, tremolo=0.0, batida=0.0):
        sr = self.sr
        passo = dur / 2.0
        total = self._n(passo * len(acordes))
        out = [0.0] * total
        n = self._n(dur)
        env = [math.sin(math.pi * i / n) ** 2 for i in range(n)]
        for ci, notas in enumerate(acordes):
            ini = self._n(passo * ci)
            ciclos = []
            for m in notas:
                c1, p1 = self._ciclo(_hz(m))
                c2, p2 = self._ciclo(_hz(m) * 1.006)
                ciclos.append((c1, p1, c2, p2))
            k = 0.5 / len(notas)
            for i in range(n):
                v = 0.0
                for (c1, p1, c2, p2) in ciclos:
                    v += c1[i % p1] + 0.6 * c2[i % p2]
                out[(ini + i) % total] += v * env[i] * k
        secs = total / sr
        if pluck:
            dl = self._n(1.0)
            for k in range(int(secs / pluck_int)):
                w = 6.283185307 * _hz(pluck[k % len(pluck)]) / sr
                ini = self._n(k * pluck_int)
                for i in range(dl):
                    out[(ini + i) % total] += math.sin(w * i) * math.exp(-4.5 * i / dl) * 0.35
        if batida:
            dl = self._n(0.22)
            for k in range(int(secs / batida)):
                for off, g in ((0.0, 1.0), (0.22, 0.6)):
                    ini = self._n(k * batida + off)
                    for i in range(dl):
                        out[(ini + i) % total] += math.sin(6.283185307 * 58 * i / sr) * math.exp(-14.0 * i / dl) * 0.9 * g
        if tremolo:
            for i in range(total):
                out[i] *= (1.0 - tremolo) + tremolo * (0.5 + 0.5 * math.sin(6.283185307 * 3.0 * i / sr))
        pico = max(0.001, max(abs(v) for v in out))
        k = 0.8 * vol / pico
        return [v * k for v in out]

    def _gerar_faixas(self):
        try:
            self.faixas["menu"] = self._som(self._faixa(
                [[45, 52, 57, 64], [41, 48, 55, 60], [43, 50, 55, 62], [40, 47, 55, 59]], 6.0,
                pluck=[69, 72, 76, 74, 71, 67], pluck_int=2.0))
            self.faixas["jogo"] = self._som(self._faixa(
                [[38, 45, 50], [36, 43, 48], [41, 48, 53], [36, 43, 48]], 6.0,
                pluck=[62, 65, 69, 67], pluck_int=3.0))
            self.faixas["tensao"] = self._som(self._faixa(
                [[38, 44, 50], [37, 43, 49], [38, 44, 50], [35, 41, 47]], 4.0,
                pluck=[74, 73], pluck_int=1.0, tremolo=0.5))
            self.faixas["resgate"] = self._som(self._faixa(
                [[45, 51, 57], [44, 50, 56]], 4.0, batida=1.0, tremolo=0.3))
        except Exception:
            pass

    # ---- uso -------------------------------------------------------------
    def tocar(self, nome, vol=1.0, intervalo=0.0):
        if not self.ativo or self.mudo:
            return
        agora = pygame.time.get_ticks()
        if intervalo and agora - self.ultimo.get(nome, -10 ** 9) < intervalo * 1000:
            return
        self.ultimo[nome] = agora
        snd = self.sons.get(nome)
        if snd:
            snd.set_volume(min(1.0, vol * self.volume))
            snd.play()

    def musica(self, nome):
        self.desejada = nome

    def atualizar(self):
        if not self.ativo:
            return
        if self.mudo:
            self.c_musica.stop()
            self.c_vento.stop()
            self.tocando = None
            return
        self.c_musica.set_volume(0.32 * self.volume)
        if self.desejada != self.tocando:
            if self.desejada is None:
                self.c_musica.fadeout(600)
                self.tocando = None
            elif self.desejada in self.faixas:
                self.c_musica.set_volume(0.32)
                self.c_musica.play(self.faixas[self.desejada], loops=-1, fade_ms=900)
                self.tocando = self.desejada
        if self.nivel_vento > 0.02:
            if not self.c_vento.get_busy():
                self.c_vento.play(self.sons["vento"], loops=-1)
            self.c_vento.set_volume(min(1.0, self.nivel_vento) * self.volume)
        elif self.c_vento.get_busy():
            self.c_vento.fadeout(400)


# =============================================================================
# 4. CONTEUDO EDUCATIVO, CARGOS E PERSONAGEM
# =============================================================================

DICAS_NR35 = [
    "Trabalho em altura e toda atividade acima de 2 m do nivel inferior com risco de queda (NR-35).",
    "Mantenha SEMPRE ao menos um gancho ancorado: e para isso que o talabarte e duplo.",
    "Inspecione o EPI antes de cada uso. Dano visivel significa descarte, nunca remendo.",
    "Ponto de ancoragem com corrosao, trinca ou deformacao nao deve ser usado.",
    "Vento forte, chuva e raios sao motivos para interromper o servico em altura.",
    "Ferramentas devem ser amarradas: um parafuso caindo de 100 m e um projetil.",
    "A jugular evita que o capacete saia da cabeca durante uma queda.",
    "Quem fica suspenso apos uma queda corre risco de trauma por suspensao: resgate rapido.",
    "Todo trabalho em altura exige planejamento e plano de resgate antes de comecar.",
    "Absorvedor de energia ja acionado deve ser descartado, mesmo parecendo intacto.",
]

LICOES = [
    ("sem nenhum", "Mantenha SEMPRE um gancho ancorado. Para trocar de ponto, ancore o gancho livre antes de soltar o outro."),
    ("dois ganchos", "Trabalhe sempre com a dupla ancoragem confirmada antes de iniciar qualquer tarefa."),
    ("Trabalho iniciado", "So inicie a tarefa com os dois ganchos ancorados."),
    ("vento", "Vento acima do limite: interrompa o servico e recolha-se ao abrigo. Nenhum prazo justifica o risco."),
    ("Pre-check", "Inspecione cada ponto do EPI antes de subir. Dano visivel significa descarte."),
    ("corroido", "Verifique tambem o ponto de ancoragem: corrosao, trincas ou deformacao o invalidam."),
    ("cedeu", "Um ponto ruim pode ceder sem aviso. Por isso o segundo gancho precisa estar em ponto bom."),
    ("resgate", "No resgate: acione ajuda, ancore-se, conecte o sistema, transfira o peso e so entao libere a vitima."),
    ("Queda contida", "Apos queda contida a vitima corre risco de trauma por suspensao: o plano de resgate e obrigatorio."),
    ("Falha", "EPI aprovado com defeito falha na hora errada. Na duvida, descarte."),
    ("Erros de execucao", "Todo procedimento tem ordem por um motivo. Pressa gera erro e erro em altura gera acidente."),
    ("Tentativa de subir", "Nunca saia do solo sem ancoragem. Prenda o primeiro gancho antes de subir."),
]


def licoes_para(infracoes):
    vistas, saida = set(), []
    for (_t, txt, _p) in infracoes:
        for chave, licao in LICOES:
            if chave.lower() in txt.lower() and licao not in vistas:
                vistas.add(licao)
                saida.append(licao)
                break
    return saida[:3]


CARGOS = ["Aprendiz de Altura", "Tecnico de Altura", "Tecnico Senior",
          "Supervisor de Altura", "Inspetor de Seguranca", "Mestre da Altura"]


def cargo_do_jogador(progresso):
    n = len(progresso.get("melhores", {}))
    return CARGOS[min(n, len(CARGOS) - 1)]


FALAS_RAFA = ["Primeira regra: eu volto pra casa hoje. Segunda regra: todo mundo volta."]
FALA_VR = "Agilidade sem perder a tecnica: ancora certo, alterna o gancho e segue."


def desenhar_rafa(surf, cx, cy, e=1.0):
    """Retrato do Rafa (Rafael Lima), inspetor de seguranca."""
    def P(x, y):
        return (int(cx + x * e), int(cy + y * e))

    def R(x, y, w, h):
        return pygame.Rect(int(cx + x * e), int(cy + y * e), int(w * e), int(h * e))
    pygame.draw.rect(surf, C_LARANJA, R(-48, 0, 96, 92), border_radius=int(16 * e))
    pygame.draw.rect(surf, (150, 70, 20), R(-48, 0, 96, 92), 2, border_radius=int(16 * e))
    pygame.draw.line(surf, (235, 235, 235), P(-34, 0), P(10, 60), max(2, int(5 * e)))
    pygame.draw.line(surf, (235, 235, 235), P(34, 0), P(-10, 60), max(2, int(5 * e)))
    pygame.draw.line(surf, (30, 34, 42), P(-48, 60), P(48, 60), max(2, int(6 * e)))
    pygame.draw.circle(surf, C_ACO_LUZ, P(0, 24), int(8 * e), 2)
    pygame.draw.rect(surf, (222, 190, 160), R(-10, -14, 20, 18))
    pygame.draw.circle(surf, (222, 190, 160), P(0, -44), int(34 * e))
    pygame.draw.circle(surf, (40, 30, 24), P(-12, -46), max(2, int(4 * e)))
    pygame.draw.circle(surf, (40, 30, 24), P(12, -46), max(2, int(4 * e)))
    pygame.draw.line(surf, (120, 70, 60), P(-10, -28), P(10, -28), max(2, int(3 * e)))
    pygame.draw.circle(surf, C_AMARELO, P(0, -56), int(38 * e))
    pygame.draw.rect(surf, (30, 36, 50), R(-40, -56, 80, 20))
    pygame.draw.rect(surf, (214, 160, 20), R(-44, -62, 88, 12), border_radius=int(5 * e))
    pygame.draw.line(surf, (60, 60, 60), P(-30, -42), P(-26, -14), max(1, int(2 * e)))
    pygame.draw.line(surf, (60, 60, 60), P(30, -42), P(26, -14), max(1, int(2 * e)))


# =============================================================================
# 5. EQUIPAMENTOS (PRE-CHECK)
# =============================================================================

class Equipamento:
    def __init__(self, nome, sigla, pontos_ok, defeito=None, ponto_defeito=None):
        self.nome = nome
        self.sigla = sigla
        self.pontos_ok = pontos_ok
        self.defeito = defeito
        self.ponto_defeito = ponto_defeito
        self.revelados = set()
        self.decisao = None  # "aprovado" | "descartado"

    @property
    def danificado(self):
        return self.defeito is not None

    def linhas_inspecao(self):
        linhas = list(self.pontos_ok)
        if self.danificado and self.ponto_defeito is not None:
            linhas[min(self.ponto_defeito, len(linhas) - 1)] = self.defeito
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
                   ("Duas ferramentas sem anel de amarracao.", 2)]),
]


def gerar_kit(qtd_defeitos):
    """Capacete, cinturao, fita de ancoragem, trava-quedas e talabarte sempre
    presentes (+1 item extra sorteado). Alguns saem de fabrica com defeito."""
    base = {e["sigla"]: e for e in CATALOGO_EPI}
    escolhidos = [base[k] for k in ("CAP", "CNT", "FTA", "TRQ", "TAL")]
    escolhidos.append(base[random.choice(["MSQ", "TPO", "FER"])])
    random.shuffle(escolhidos)
    com_defeito = random.sample(range(len(escolhidos)), min(qtd_defeitos, len(escolhidos)))
    kit = []
    for i, d in enumerate(escolhidos):
        if i in com_defeito:
            txt, pos = random.choice(d["defeitos"])
            kit.append(Equipamento(d["nome"], d["sigla"], d["ok"], txt, pos))
        else:
            kit.append(Equipamento(d["nome"], d["sigla"], d["ok"]))
    return kit


def kit_aprovado():
    kit = gerar_kit(0)
    for e in kit:
        e.decisao = "aprovado"
    return kit


def icone_epi(surf, sigla, rect):
    pygame.draw.rect(surf, (28, 36, 50), rect, border_radius=10)
    pygame.draw.rect(surf, C_PAINEL_BORDA, rect, 2, border_radius=10)
    cx, cy = rect.center
    s = rect.w / 200.0

    def P(x, y):
        return (int(cx + x * s), int(cy + y * s))

    def R(x, y, w, h):
        return pygame.Rect(int(cx + x * s), int(cy + y * s), int(w * s), int(h * s))
    L = max(2, int(5 * s))
    if sigla == "CAP":
        pygame.draw.circle(surf, C_AMARELO, P(0, 15), int(62 * s))
        pygame.draw.rect(surf, (28, 36, 50), R(-70, 15, 140, 60))
        pygame.draw.rect(surf, (214, 160, 20), R(-78, 12, 156, 14), border_radius=6)
        pygame.draw.line(surf, (110, 110, 118), P(-55, 26), P(-30, 74), L)
        pygame.draw.line(surf, (110, 110, 118), P(55, 26), P(30, 74), L)
        pygame.draw.line(surf, (110, 110, 118), P(-30, 74), P(30, 74), L)
    elif sigla == "CNT":
        for sx in (-1, 1):
            pygame.draw.line(surf, (220, 220, 225), P(sx * 38, -85), P(sx * 20, 15), L + 2)
            pygame.draw.circle(surf, (220, 220, 225), P(sx * 36, 62), int(26 * s), L)
        pygame.draw.line(surf, (220, 220, 225), P(-30, -40), P(30, -40), L + 2)
        pygame.draw.line(surf, (220, 220, 225), P(-24, 15), P(24, 15), L + 2)
        pygame.draw.circle(surf, C_ACO_LUZ, P(0, -68), int(11 * s), L)
    elif sigla == "TAL":
        pygame.draw.line(surf, C_LARANJA, P(0, -85), P(0, -5), L + 2)
        pygame.draw.rect(surf, (230, 230, 235), R(-11, -70, 22, 40), border_radius=5)
        pygame.draw.line(surf, C_LARANJA, P(0, -5), P(-52, 52), L + 2)
        pygame.draw.line(surf, C_LARANJA, P(0, -5), P(52, 52), L + 2)
        for sx in (-1, 1):
            pygame.draw.rect(surf, C_ACO_LUZ, R(sx * 52 - 14, 48, 28, 44), max(1, L - 1), border_radius=8)
    elif sigla == "TRQ":
        pygame.draw.rect(surf, C_ACO, R(-46, -80, 92, 86), border_radius=12)
        pygame.draw.circle(surf, C_ACO_ESC, P(0, -36), int(30 * s))
        pygame.draw.circle(surf, C_ACO_LUZ, P(0, -36), int(8 * s))
        pygame.draw.line(surf, (230, 230, 235), P(0, 6), P(0, 70), L)
        pygame.draw.circle(surf, C_ACO_LUZ, P(0, 76), int(10 * s), L)
    elif sigla == "FTA":
        pygame.draw.rect(surf, C_LARANJA, R(-76, -34, 152, 68), L * 2, border_radius=int(34 * s))
        for k in (-62, 62):
            pygame.draw.line(surf, (30, 30, 30), P(k, -30), P(k, 30), 2)
    elif sigla == "MSQ":
        pygame.draw.rect(surf, C_ACO_LUZ, R(-40, -76, 80, 150), L + 3, border_radius=int(30 * s))
        pygame.draw.line(surf, C_VERMELHO, P(-40, -10), P(40, -10), L)
    elif sigla == "TPO":
        pts = [P(-80 + i * 16, math.sin(i * 0.9) * 22) for i in range(11)]
        pygame.draw.lines(surf, C_LARANJA, False, pts, L + 3)
        pygame.draw.rect(surf, C_ACO_LUZ, R(-18, -22, 36, 44), max(1, L - 1), border_radius=6)
    else:  # FER
        pygame.draw.rect(surf, (110, 84, 60), R(-86, 22, 172, 24), border_radius=8)
        pygame.draw.line(surf, C_ACO_LUZ, P(-50, 22), P(-50, -50), L + 1)
        pygame.draw.rect(surf, C_ACO_LUZ, R(-68, -62, 36, 16), border_radius=3)
        pygame.draw.line(surf, C_ACO_LUZ, P(10, 22), P(30, -60), L + 1)
        pygame.draw.circle(surf, C_ACO_LUZ, P(32, -66), int(12 * s), L)
        pygame.draw.line(surf, C_AMARELO, P(-50, 22), P(-70, 60), 2)


# =============================================================================
# 6. ESTRUTURA (GRAFO DE VIGAS) E OBRAS
# =============================================================================

class Estrutura:
    """Cada no e um ponto de ancoragem; as arestas sao as vigas percorriveis."""

    def __init__(self, cols, linhas, sx, sy, origem):
        self.cols, self.linhas, self.sx, self.sy = cols, linhas, sx, sy
        ox, oy = origem
        self.nodes, self.indice = [], {}
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


TEMAS = {
    None: dict(ceu=((26, 38, 58), (92, 122, 150)), predios=True, noite=False, chao=(46, 52, 46)),
    "predio": dict(ceu=((84, 138, 198), (212, 230, 242)), predios=True, noite=False, chao=(72, 76, 70)),
    "ponte": dict(ceu=((70, 120, 180), (196, 220, 238)), predios=False, noite=False, chao=(28, 84, 132)),
    "torre": dict(ceu=((92, 64, 112), (244, 176, 112)), predios=False, noite=False, chao=(74, 62, 46)),
    # Modelos para futuras obras (descomente / ajuste):
    "turbina": dict(ceu=((70, 140, 205), (214, 238, 250)), predios=False, noite=False, chao=(64, 112, 56)),
    "arranha": dict(ceu=((6, 8, 26), (52, 62, 112)), predios=True, noite=True, chao=(36, 40, 50)),
}

NIVEIS = [
    dict(
        nome="OBRA 01 - Edificio Solar das Palmeiras",
        local="Estrutura de 7 pavimentos - obra residencial",
        tema="predio",
        cols=5, linhas=7, sx=150, sy=110,
        vento_base=2.5, vento_pico=12.5, rajada_intervalo=(14, 22),
        defeitos=1,                 # EPIs com defeito no kit
        ruins=2,                    # pontos de ancoragem corroidos
        tempo=420,
        tarefas=[((1, 2), "solda"), ((3, 4), "aperto"), ((2, 6), "lampada")],
        resgate=(4, 5),             # (coluna, linha) do colega suspenso; None = sem resgate
        abrigos=[(0, 0), (4, 0), (2, 3)],
        fala=FALAS_RAFA[0],
        briefing="Instalacao de sinalizacao e reforco estrutural no edificio residencial em obra. "
                 "Antes de subir, inspecione o EPI. Na estrutura, ancoragens enferrujadas nao "
                 "seguram: escolha bem onde prender o gancho. Na altura do 6o pavimento um "
                 "colega ficou suspenso apos uma queda contida: conclua a manutencao e execute "
                 "o resgate antes do trauma por suspensao.",
    ),
    dict(
        nome="OBRA 02 - Ponte Estaiada Rio Verde",
        local="Pilone central - 38 m sobre a agua",
        tema="ponte",
        cols=6, linhas=7, sx=160, sy=118,
        vento_base=5.0, vento_pico=15.0, rajada_intervalo=(11, 18),
        defeitos=2,
        ruins=3,
        tempo=480,
        tarefas=[((1, 2), "solda"), ((4, 3), "aperto"), ((5, 5), "sequencia"), ((2, 6), "lampada")],
        resgate=None,
        abrigos=[(0, 0), (5, 0), (3, 3)],
        fala="Vento sobre a agua nao avisa. Se a rajada passou do limite, eu paro e espero.",
        briefing="Inspecao e reforco no pilone da ponte estaiada. O vento sobre o rio e mais forte "
                 "e mais instavel, e o kit de EPI chega com dois itens suspeitos. Ha tres pontos de "
                 "ancoragem corroidos, quatro tarefas (incluindo o ensaio de soldas por liquido "
                 "penetrante) e nenhum resgate: aqui o desafio e disciplina. Acima de 11 m/s, "
                 "recolha-se ao abrigo.",
    ),
    dict(
        nome="OBRA 03 - Torre de Transmissao 138 kV",
        local="LT Norte, vao 14 - torre de 40 m, circuito desenergizado",
        tema="torre",
        cols=5, linhas=9, sx=150, sy=112,
        vento_base=6.0, vento_pico=16.0, rajada_intervalo=(10, 16),
        defeitos=2,
        ruins=3,
        tempo=540,
        trauma=240,                 # segundos ate o trauma por suspensao (padrao 150)
        tarefas=[((0, 3), "aperto"), ((2, 5), "sequencia"), ((4, 6), "lampada")],
        resgate=(2, 7),
        abrigos=[(0, 0), (4, 0), (2, 4)],
        fala="Um colega ficou pendurado la em cima. Eu respiro, sigo o procedimento e ele desce comigo.",
        briefing="Troca da sinalizacao de balizamento da torre de transmissao. ATENCAO: um eletricista "
                 "ficou suspenso apos uma queda contida perto do topo e o trauma por suspensao corre "
                 "contra o relogio. Nao existe heroi sem ancoragem: planeje a subida, evite os pontos "
                 "corroidos, execute as tarefas e faca o resgate com o procedimento completo "
                 "(comunicar, ancorar, conectar, tensionar, liberar).",
    ),
    dict(
        nome="OBRA 04 - Turbina Eolica GX-120",
        local="Parque eolico Serra Azul - torre de 55 m ate a nacele",
        tema="turbina",
        cols=4, linhas=12, sx=140, sy=110,
        vento_base=7.0, vento_pico=17.0, rajada_intervalo=(9, 15),
        defeitos=2,
        ruins=4,
        tempo=600,
        trauma=200,
        tarefas=[((0, 4), "aperto"), ((3, 7), "solda"), ((1, 10), "sequencia"), ((2, 11), "lampada")],
        resgate=(3, 9),
        abrigos=[(0, 0), (3, 0), (1, 5), (2, 8)],
        fala="Em torre eolica o vento e o chefe. Eu so subo com a janela de vento aberta e saio quando ela fecha.",
        briefing="Manutencao da nacele e do balizamento de uma turbina eolica de grande porte. "
                 "O vento aqui e constante e castiga o equilibrio: use os abrigos intermediarios. "
                 "Quatro tarefas, quatro pontos de ancoragem corroidos e um tecnico suspenso perto "
                 "do topo. Planeje a rota, nao abra mao da dupla ancoragem e respeite o limite de vento.",
    ),
    dict(
        nome="OBRA 05 - Arranha-ceu Torre Horizonte",
        local="Coroamento de 56 m - servico noturno com fachada espelhada",
        tema="arranha",
        cols=6, linhas=12, sx=150, sy=112,
        vento_base=7.5, vento_pico=18.0, rajada_intervalo=(8, 13),
        defeitos=3,
        ruins=5,
        tempo=720,
        trauma=220,
        tarefas=[((1, 3), "solda"), ((4, 5), "aperto"), ((2, 8), "sequencia"), ((5, 9), "lampada"),
                 ((3, 11), "sequencia")],
        resgate=(4, 10),
        abrigos=[(0, 0), (5, 0), (2, 4), (3, 7)],
        fala="Ultima obra da jornada: nenhum prazo vale uma vida. Sigo o procedimento do primeiro ao ultimo passo.",
        briefing="Servico noturno no coroamento do arranha-ceu: reforco de fixacoes, ensaio de soldas e "
                 "balizamento aeronautico. Tres EPIs suspeitos no kit, cinco ancoragens corroidas, cinco "
                 "tarefas e um colega suspenso perto do topo. E o exame final: vento forte, pouco "
                 "tempo e zero margem para atalhos.",
    ),
    # ---- MODELO PARA A PROXIMA OBRA (copie, cole e ajuste) -------------------
    # dict(nome="OBRA 06 - ...", local="...", tema="predio",
    #      cols=4, linhas=12, sx=140, sy=110, vento_base=7.0, vento_pico=17.0,
    #      rajada_intervalo=(9, 15), defeitos=2, ruins=4, tempo=600,
    #      tarefas=[((0, 5), "solda"), ((3, 8), "aperto"), ((1, 11), "lampada")],
    #      resgate=(3, 10), abrigos=[(0, 0), (1, 5)], fala="...", briefing="..."),
]


# =============================================================================
# 7. MINIJOGOS DE MANUTENCAO E RESGATE
# =============================================================================

class MiniJogo:
    titulo = "TAREFA"
    instrucao = ""

    def __init__(self):
        self.progresso = 0.0
        self.erros = 0
        self.concluido = False
        self.rect = pygame.Rect(0, 0, 680, 330)
        self.rect.center = (LARGURA // 2, ALTURA // 2 + 25)

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
        barra(surf, (self.rect.x + 40, self.rect.bottom - 52, self.rect.w - 80, 16), self.progresso, C_VERDE)
        texto(surf, "PROGRESSO {:.0f}%   ERROS: {}".format(self.progresso * 100, self.erros),
              (self.rect.centerx, self.rect.bottom - 24), "mono_p", C_TEXTO_FRACO, centro=True)


class MiniSolda(MiniJogo):
    titulo = "SOLDA DE REFORCO"
    instrucao = "A / D movem o eletrodo. Segure ESPACO para soldar mantendo o arco na faixa verde."

    def __init__(self):
        super().__init__()
        self.cursor, self.vel = 0.5, 0.0
        self.alvo = random.uniform(0.25, 0.75)
        self.larg_alvo = 0.14
        self.dir_alvo = random.choice([-1, 1])
        self.soldando = False

    def evento(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_SPACE:
            self.soldando = True
        if ev.type == pygame.KEYUP and ev.key == pygame.K_SPACE:
            self.soldando = False

    def atualizar(self, dt):
        t = pygame.key.get_pressed()
        acel = (1.6 if (t[pygame.K_d] or t[pygame.K_RIGHT]) else 0) - (1.6 if (t[pygame.K_a] or t[pygame.K_LEFT]) else 0)
        self.vel = (self.vel + acel * dt) * 0.92
        self.cursor = max(0.0, min(1.0, self.cursor + self.vel * dt))
        self.alvo += self.dir_alvo * 0.09 * dt
        if self.alvo < 0.15 or self.alvo > 0.85:
            self.dir_alvo *= -1
            self.alvo = max(0.15, min(0.85, self.alvo))
        if self.soldando:
            if abs(self.cursor - self.alvo) < self.larg_alvo / 2:
                self.progresso += 0.20 * dt
            else:
                self.progresso = max(0.0, self.progresso - 0.22 * dt)
                if random.random() < dt * 1.2:
                    self.erros += 1
        if self.progresso >= 1.0:
            self.progresso, self.concluido = 1.0, True

    def desenhar_corpo(self, surf):
        tr = pygame.Rect(self.rect.x + 50, self.rect.y + 120, self.rect.w - 100, 34)
        pygame.draw.rect(surf, (36, 44, 56), tr, border_radius=6)
        ax, aw = tr.x + int((self.alvo - self.larg_alvo / 2) * tr.w), int(self.larg_alvo * tr.w)
        pygame.draw.rect(surf, (40, 120, 70), (ax, tr.y, aw, tr.h), border_radius=6)
        pygame.draw.rect(surf, C_VERDE, (ax, tr.y, aw, tr.h), 2, border_radius=6)
        cx = tr.x + int(self.cursor * tr.w)
        pygame.draw.rect(surf, C_AMARELO if self.soldando else C_TEXTO_FRACO,
                         (cx - 4, tr.y - 10, 8, tr.h + 20), border_radius=3)
        if self.soldando:
            for _ in range(8):
                pygame.draw.circle(surf, random.choice([C_AMARELO, C_LARANJA, C_BRANCO]),
                                   (cx + random.randint(-10, 10), tr.centery + random.randint(-14, 14)),
                                   random.randint(1, 3))


class MiniAperto(MiniJogo):
    titulo = "TORQUE DE PARAFUSOS ESTRUTURAIS"
    instrucao = "Segure ESPACO para aplicar torque e solte dentro da faixa verde."

    def __init__(self):
        super().__init__()
        self.valor, self.aplicando = 0.0, False
        self.feitos, self.total = 0, 4
        self.msg, self.msg_t = "", 0.0
        self.novo()

    def novo(self):
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
                self.msg = "TORQUE CORRETO"
            else:
                self.erros += 1
                self.msg = "SUBTORQUE" if self.valor < self.alvo else "SOBRETORQUE"
            self.msg_t = 1.0
            self.progresso = self.feitos / self.total
            if self.feitos >= self.total:
                self.concluido = True
            else:
                self.novo()

    def atualizar(self, dt):
        if self.aplicando:
            self.valor = min(1.05, self.valor + dt * 0.46)
            if self.valor >= 1.04:
                self.aplicando = False
                self.erros += 1
                self.msg, self.msg_t = "PARAFUSO ESPANADO", 1.0
                self.novo()
        self.msg_t = max(0.0, self.msg_t - dt)

    def desenhar_corpo(self, surf):
        tr = pygame.Rect(self.rect.x + 50, self.rect.y + 130, self.rect.w - 100, 30)
        pygame.draw.rect(surf, (36, 44, 56), tr, border_radius=6)
        pygame.draw.rect(surf, (40, 120, 70), (tr.x + int((self.alvo - self.tol) * tr.w), tr.y,
                                               int(2 * self.tol * tr.w), tr.h), border_radius=6)
        pygame.draw.rect(surf, (140, 60, 60), (tr.x + int(0.95 * tr.w), tr.y, int(0.05 * tr.w), tr.h), border_radius=6)
        pygame.draw.rect(surf, C_LARANJA, (tr.x, tr.y, int(self.valor * tr.w), tr.h), border_radius=6)
        pygame.draw.rect(surf, C_PAINEL_BORDA, tr, 2, border_radius=6)
        texto(surf, "PARAFUSO {}/{}".format(min(self.feitos + 1, self.total), self.total),
              (self.rect.centerx, tr.y - 30), "ui", C_TEXTO, centro=True)
        if self.msg_t > 0:
            texto(surf, self.msg, (self.rect.centerx, tr.bottom + 26), "ui_g",
                  C_VERDE if "CORRETO" in self.msg else C_VERMELHO, centro=True)


class MiniLampada(MiniJogo):
    titulo = "TROCA DE LAMPADA DE BALIZAMENTO"
    instrucao = "Execute o procedimento na ordem (teclas 1 a 6)."
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
        self.passo, self.msg, self.msg_t = 0, "", 0.0

    def evento(self, ev):
        if ev.type != pygame.KEYDOWN:
            return
        teclas = [p[1] for p in self.PASSOS]
        if ev.key in teclas:
            if teclas.index(ev.key) == self.passo:
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
        for i, (txt, _k) in enumerate(self.PASSOS):
            feito, atual = i < self.passo, i == self.passo
            cor = C_VERDE if feito else (C_AMARELO if atual else C_TEXTO_FRACO)
            marca = "[X]" if feito else ("[>]" if atual else "[ ]")
            texto(surf, "{} {}. {}".format(marca, i + 1, txt), (self.rect.x + 44, y), "ui_p", cor)
            y += 24
        if self.msg_t > 0:
            texto(surf, self.msg, (self.rect.centerx, self.rect.bottom - 76), "ui",
                  C_VERDE if self.msg == "OK" else C_VERMELHO, centro=True)


class MiniSequencia(MiniJogo):
    titulo = "ENSAIO DE SOLDAS - LIQUIDO PENETRANTE"
    instrucao = "Digite a sequencia de teclas antes que o tempo acabe."
    POOL = [pygame.K_q, pygame.K_w, pygame.K_e, pygame.K_r, pygame.K_a, pygame.K_s, pygame.K_d]
    NOMES = {pygame.K_q: "Q", pygame.K_w: "W", pygame.K_e: "E", pygame.K_r: "R",
             pygame.K_a: "A", pygame.K_s: "S", pygame.K_d: "D"}

    def __init__(self):
        super().__init__()
        self.rodadas, self.total = 0, 3
        self.nova_rodada()

    def nova_rodada(self):
        n = 4 + self.rodadas
        self.seq = [random.choice(self.POOL) for _ in range(n)]
        self.i = 0
        self.tempo_max = 2.5 + n * 0.8
        self.tempo = self.tempo_max

    def evento(self, ev):
        if ev.type != pygame.KEYDOWN or ev.key not in self.POOL:
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
        else:
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
            r = pygame.Rect(x0 + i * (larg + 10), self.rect.y + 110, larg, larg)
            feito = i < self.i
            pygame.draw.rect(surf, (40, 120, 70) if feito else (36, 44, 56), r, border_radius=6)
            pygame.draw.rect(surf, C_VERDE if feito else C_PAINEL_BORDA, r, 2, border_radius=6)
            texto(surf, self.NOMES[k], r.center, "ui_g", C_TEXTO, centro=True)
        barra(surf, (self.rect.x + 120, self.rect.y + 182, self.rect.w - 240, 10),
              self.tempo / self.tempo_max, C_LARANJA)
        texto(surf, "RODADA {}/{}".format(min(self.rodadas + 1, self.total), self.total),
              (self.rect.centerx, self.rect.y + 214), "ui_p", C_TEXTO_FRACO, centro=True)


class MiniResgate(MiniJogo):
    titulo = "RESGATE EM ALTURA"
    PASSOS = [
        ("Acionar a equipe de emergencia pelo radio", pygame.K_1),
        ("Ancorar-se com os dois ganchos acima da vitima", pygame.K_2),
        ("Conectar o sistema de descida a argola da vitima", pygame.K_3),
        ("Tensionar o sistema e transferir o peso da vitima", pygame.K_4),
        ("Liberar a vitima do ponto de ancoragem original", pygame.K_5),
    ]

    def __init__(self, altura_m):
        super().__init__()
        self.rect = pygame.Rect(0, 0, 700, 360)
        self.rect.center = (LARGURA // 2, ALTURA // 2 + 20)
        self.altura = max(1.0, altura_m)
        self.restante = self.altura
        self.fase, self.passo = 0, 0
        self.vel, self.descendo, self.alerta = 0.0, False, 0.0
        self.msg, self.msg_t = "", 0.0
        self.instrucao = "Fase 1: execute o procedimento na ordem (teclas 1 a 5)."

    def evento(self, ev):
        if self.fase == 0:
            if ev.type != pygame.KEYDOWN:
                return
            teclas = [p[1] for p in self.PASSOS]
            if ev.key in teclas:
                if teclas.index(ev.key) == self.passo:
                    self.passo += 1
                    self.msg, self.msg_t = "OK", 0.6
                    if self.passo >= len(self.PASSOS):
                        self.fase = 1
                        self.instrucao = "Fase 2: segure ESPACO para descer. Velocidade na faixa verde."
                else:
                    self.erros += 1
                    self.msg, self.msg_t = "FORA DE SEQUENCIA!", 1.0
        else:
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_SPACE:
                self.descendo = True
            if ev.type == pygame.KEYUP and ev.key == pygame.K_SPACE:
                self.descendo = False

    def atualizar(self, dt):
        self.msg_t = max(0.0, self.msg_t - dt)
        if self.fase == 0:
            self.progresso = self.passo / len(self.PASSOS) * 0.25
            return
        self.vel += (1.55 if self.descendo else -2.10) * dt
        self.vel = max(0.0, min(3.2, self.vel))
        self.restante = max(0.0, self.restante - self.vel * dt)
        self.progresso = 0.25 + 0.75 * (1.0 - self.restante / self.altura)
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
        if self.fase == 0:
            y = self.rect.y + 92
            for i, (txt, _k) in enumerate(self.PASSOS):
                feito, atual = i < self.passo, i == self.passo
                cor = C_VERDE if feito else (C_AMARELO if atual else C_TEXTO_FRACO)
                marca = "[X]" if feito else ("[>]" if atual else "[ ]")
                texto(surf, "{} {}. {}".format(marca, i + 1, txt), (self.rect.x + 44, y), "ui_p", cor)
                y += 28
            if self.msg_t > 0:
                texto(surf, self.msg, (self.rect.centerx, self.rect.bottom - 76), "ui",
                      C_VERDE if self.msg == "OK" else C_VERMELHO, centro=True)
            return
        tr = pygame.Rect(self.rect.x + 50, self.rect.y + 130, self.rect.w - 100, 28)
        pygame.draw.rect(surf, (36, 44, 56), tr, border_radius=6)
        pygame.draw.rect(surf, (40, 120, 70), (tr.x + int(0.6 / 3.2 * tr.w), tr.y, int(1.0 / 3.2 * tr.w), tr.h),
                         border_radius=6)
        cx = tr.x + int(self.vel / 3.2 * tr.w)
        pygame.draw.rect(surf, C_VERMELHO if self.vel > 2.0 else C_AMARELO, (cx - 4, tr.y - 8, 8, tr.h + 16),
                         border_radius=3)
        texto(surf, "VELOCIDADE DE DESCIDA: {:.2f} m/s".format(self.vel), (self.rect.centerx, tr.y - 28),
              "mono", C_TEXTO, centro=True)
        texto(surf, "ALTURA RESTANTE: {:.1f} m".format(self.restante), (self.rect.centerx, tr.bottom + 22),
              "mono", C_TEXTO, centro=True)


MINIJOGOS = {"solda": MiniSolda, "aperto": MiniAperto, "lampada": MiniLampada, "sequencia": MiniSequencia}
NOME_TAREFA = {"solda": "Solda de reforco", "aperto": "Torque de parafusos",
               "lampada": "Lampada de balizamento", "sequencia": "Ensaio de soldas"}


# =============================================================================
# 8. JOGADOR (RAFA)
# =============================================================================

class Jogador:
    def __init__(self, estrutura, no_inicial):
        self.est = estrutura
        self.a, self.b, self.u = no_inicial, None, 0.0
        self.pos = Vector2(estrutura.pos(no_inicial))
        self.ganchos = [None, None]
        self.vel_base = 128.0
        self.equilibrio = 100.0
        self.agachado = False
        self.suspenso = 0.0
        self.olhando = 1
        self.anim = 0.0
        self.sway = 0.0

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

    # ---- ancoragem -------------------------------------------------------
    def alvo_gancho(self, direcao=None):
        """No onde o proximo gancho prenderia. Com direcao (WASD) ele mira
        no ponto que esta naquela direcao; sem direcao, no mais proximo."""
        usados = {g for g in self.ganchos if g is not None}
        alcance = min(RAIO_ANCORAGEM, CABO_MAX)
        mira = direcao is not None and direcao.length_squared() > 0
        melhor, melhor_s = None, 1e9
        for i, p in enumerate(self.est.nodes):
            if i in usados:
                continue
            d = self.pos.distance_to(p)
            if d > alcance:
                continue
            s = d
            if mira:
                if d > 12:
                    v = (p - self.pos).normalize().dot(direcao.normalize())
                    s = d * (1.7 - 0.9 * v)
                else:
                    s = d + 200
            if s < melhor_s:
                melhor, melhor_s = i, s
        return melhor

    def alternar_gancho(self, idx, direcao=None):
        if self.ganchos[idx] is not None:
            outro = self.ganchos[1 - idx]
            self.ganchos[idx] = None
            if outro is None and not self.no_solo():
                return True, "PERIGO: voce ficou SEM NENHUMA ancoragem!"
            return True, "Gancho {} liberado".format(idx + 1)
        alvo = self.alvo_gancho(direcao)
        if alvo is None:
            return False, "Nenhum ponto de ancoragem ao alcance"
        self.ganchos[idx] = alvo
        return True, "Gancho {} ancorado".format(idx + 1)

    def tensionado(self, ponto):
        return any(g is not None and ponto.distance_to(self.est.pos(g)) > CABO_MAX for g in self.ganchos)

    # ---- movimento -------------------------------------------------------
    def mover(self, direcao, dt):
        if direcao.length_squared() == 0:
            return None
        d = direcao.normalize()
        if self.ancorado == 0 and not self.no_solo():
            return "QUEDA_LIVRE"
        if self.b is None:
            if self.ancorado == 0:
                for n in self.est.adj[self.a]:
                    v = self.est.pos(n) - self.est.pos(self.a)
                    if v.length_squared() > 0 and v.normalize().dot(d) > 0.45 and n not in self.est.solo:
                        return "BLOQUEADO_SOLO"
            melhor, melhor_dot = None, 0.45
            for n in self.est.adj[self.a]:
                v = self.est.pos(n) - self.est.pos(self.a)
                if v.length_squared() == 0:
                    continue
                dot = v.normalize().dot(d)
                if dot > melhor_dot:
                    melhor, melhor_dot = n, dot
            if melhor is None:
                return None
            self.b, self.u = melhor, 0.0
        pa, pb = self.est.pos(self.a), self.est.pos(self.b)
        vetor = pb - pa
        comp = vetor.length()
        if comp <= 0:
            self.b = None
            return None
        sentido = 1 if vetor.normalize().dot(d) > 0 else -1
        vel = self.vel_base * (0.45 if self.agachado else 1.0) * (0.55 + 0.45 * (self.equilibrio / 100.0))
        novo_u = self.u + sentido * vel * dt / comp
        novo_u_c = max(0.0, min(1.0, novo_u))
        if self.tensionado(pa + vetor * novo_u_c):
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

    # ---- desenho ---------------------------------------------------------
    def desenhar(self, surf, cam):
        p = self.pos - cam
        cores = [C_VERDE, C_AZUL]
        for i, g in enumerate(self.ganchos):
            if g is not None:
                tens = self.pos.distance_to(self.est.pos(g)) / CABO_MAX
                cor = cores[i] if tens < 0.85 else (C_LARANJA if tens < 0.97 else C_VERMELHO)
                desenhar_cabo(surf, p + Vector2(self.sway * 0.4, -16), self.est.pos(g) - cam, cor, 10, 3)
        bal = math.sin(self.anim) * 2 if not self.agachado else 0
        alt = 22 if not self.agachado else 15
        cx, cy, sw = int(p.x), int(p.y), self.sway
        pygame.draw.line(surf, (40, 48, 60), (cx, cy), (cx - 6, cy + 12 + bal), 4)
        pygame.draw.line(surf, (40, 48, 60), (cx, cy), (cx + 6, cy + 12 - bal), 4)
        corpo = pygame.Rect(int(cx - 8 + sw * 0.5), cy - alt, 16, alt)
        pygame.draw.rect(surf, C_LARANJA, corpo, border_radius=4)
        pygame.draw.rect(surf, (150, 70, 20), corpo, 1, border_radius=4)
        pygame.draw.line(surf, (30, 34, 42), (cx - 8 + sw * 0.5, cy - alt // 2), (cx + 8 + sw * 0.5, cy - alt // 2), 3)
        pygame.draw.line(surf, (235, 235, 235), (cx - 6 + sw * 0.6, cy - alt), (cx + 4 + sw * 0.3, cy - alt // 2), 2)
        pygame.draw.line(surf, (235, 235, 235), (cx + 6 + sw * 0.6, cy - alt), (cx - 4 + sw * 0.3, cy - alt // 2), 2)
        pygame.draw.circle(surf, (110, 84, 60), (cx - 9 * self.olhando, cy - alt // 2 + 2), 3)
        pygame.draw.line(surf, C_LARANJA, (cx + sw * 0.6, cy - alt + 4),
                         (cx + 11 * self.olhando + sw, cy - alt + 12 - bal), 4)
        hx, hy = int(cx + sw), cy - alt - 9
        pygame.draw.circle(surf, (222, 190, 160), (hx, hy), 7)
        pygame.draw.circle(surf, C_AMARELO, (hx, hy - 2), 8)
        pygame.draw.rect(surf, C_AMARELO, (hx - 9, hy - 3, 18, 4), border_radius=2)
        pygame.draw.line(surf, (60, 60, 60), (hx - 5, hy + 4), (hx + 5, hy + 4), 1)


# =============================================================================
# 9. CENAS
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


def estrela(surf, cx, cy, r, cor, borda=(60, 50, 10)):
    """Estrela de 5 pontas desenhada com poligono (sem depender de fonte)."""
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + math.cos(ang) * rr, cy + math.sin(ang) * rr))
    pygame.draw.polygon(surf, cor, pts)
    pygame.draw.polygon(surf, borda, pts, 2)


def estrelas_de(pontos, infracoes):
    """Classificacao em estrelas (1 a 3) de uma obra concluida."""
    if pontos >= 95 and not infracoes:
        return 3
    return 2 if pontos >= 80 else 1


def desenhar_estrelas(surf, cx, cy, n, r=14, total=3):
    for i in range(total):
        x = cx + (i - (total - 1) / 2.0) * (r * 2.4)
        estrela(surf, x, cy, r, C_AMARELO if i < n else (52, 58, 70),
                (60, 50, 10) if i < n else (34, 38, 48))


class Particulas:
    """Fagulhas, poeira e confete: efeitos leves de polimento visual."""

    def __init__(self):
        self.lista = []

    def explodir(self, pos, n, cores, vel=(40, 190), vida=(0.35, 0.8), grav=420.0, tam=(2, 4)):
        for _ in range(n):
            ang = random.uniform(0, 6.283185)
            v = random.uniform(*vel)
            t = random.uniform(*vida)
            self.lista.append([pos[0], pos[1], math.cos(ang) * v, math.sin(ang) * v - 40,
                               t, t, random.choice(cores), random.randint(*tam), grav])

    def confete(self, cam, n=90):
        cores = [C_AMARELO, C_LARANJA, C_VERDE, C_AZUL, C_BRANCO]
        for _ in range(n):
            t = random.uniform(1.6, 3.2)
            self.lista.append([cam.x + random.uniform(0, LARGURA), cam.y + random.uniform(-80, -10),
                               random.uniform(-40, 40), random.uniform(60, 220),
                               t, t, random.choice(cores), random.randint(3, 6), 90.0])

    def atualizar(self, dt):
        vivas = []
        for p in self.lista:
            p[4] -= dt
            if p[4] <= 0:
                continue
            p[3] += p[8] * dt
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            vivas.append(p)
        self.lista = vivas[-400:]

    def desenhar(self, surf, cam):
        for x, y, _vx, _vy, t, t0, cor, tam, _g in self.lista:
            a = max(0.0, min(1.0, t / t0))
            c = tuple(int(v * (0.35 + 0.65 * a)) for v in cor)
            pygame.draw.rect(surf, c, (int(x - cam.x), int(y - cam.y), tam, tam))


class Fundo:
    """Ceu, nuvens e skyline em parallax (pre-renderizados)."""
    _cache = {}

    def __init__(self, seed=1, tema=None):
        rnd = random.Random(seed)
        tm = TEMAS.get(tema, TEMAS[None])
        if tm["ceu"] not in Fundo._cache:
            s = pygame.Surface((LARGURA, ALTURA))
            gradiente_vertical(s, s.get_rect(), tm["ceu"][0], tm["ceu"][1])
            Fundo._cache[tm["ceu"]] = s
        self.ceu = Fundo._cache[tm["ceu"]]
        self.noite = tm["noite"]
        if self.noite:
            self.ceu = self.ceu.copy()
            for _ in range(130):
                sx, sy = rnd.randint(0, LARGURA - 1), rnd.randint(0, int(ALTURA * 0.7))
                c = rnd.randint(120, 255)
                self.ceu.set_at((sx, sy), (c, c, min(255, c + 12)))
                if rnd.random() < 0.18:
                    pygame.draw.circle(self.ceu, (c, c, 255), (sx, sy), 1)
            t0, t1 = tm["ceu"]
            f = 110 / float(ALTURA)
            ceu_lua = tuple(int(t0[k] + (t1[k] - t0[k]) * f) for k in range(3))
            pygame.draw.circle(self.ceu, (238, 238, 214), (LARGURA - 200, 110), 28)
            pygame.draw.circle(self.ceu, ceu_lua, (LARGURA - 190, 104), 25)
        self.predios = []
        if tm["predios"]:
            for _ in range(26):
                bx, bh = rnd.randint(-200, LARGURA + 200), rnd.randint(120, 380)
                bw, par = rnd.randint(60, 150), rnd.uniform(0.15, 0.35)
                tom = int(40 + par * 90)
                s = pygame.Surface((bw, bh + 400))
                s.fill((tom, tom + 8, tom + 22))
                luz = (240, 210, 120) if self.noite else (tom + 34, tom + 38, tom + 24)
                for jx in range(8, bw - 6, 16):
                    for jy in range(12, bh - 10, 22):
                        if (jx + jy + int(bx)) % 3 == 0:
                            pygame.draw.rect(s, luz, (jx, jy, 6, 9))
                self.predios.append((s, bx, bh, par))
        self.nuvens = []
        for _ in range(9):
            w = rnd.randint(60, 150)
            s = pygame.Surface((w * 2, 44), pygame.SRCALPHA)
            for i in range(4):
                pygame.draw.ellipse(s, (255, 255, 255, 40), (i * w // 3, 6 + (i % 2) * 6, w, 32))
            self.nuvens.append([float(rnd.randint(0, LARGURA)), rnd.randint(40, 320), rnd.uniform(0.05, 0.16), s])

    def desenhar(self, surf, cam, vento=0.0):
        surf.blit(self.ceu, (0, 0))
        for n in self.nuvens:
            n[0] -= (6 + vento * 2) * 0.016
            if n[0] < -400:
                n[0] = LARGURA + 200
            surf.blit(n[3], ((n[0] - cam.x * n[2]) % (LARGURA + 400) - 200, n[1] - cam.y * n[2] * 0.5))
        for (s, bx, bh, par) in self.predios:
            x, y = bx - cam.x * par, ALTURA - bh - cam.y * par * 0.35
            if -260 < x < LARGURA + 60 and y < ALTURA:
                surf.blit(s, (x, y))


# ------------------------------------------------------------------ MENU ----
class CenaMenu(Cena):
    def __init__(self, app):
        super().__init__(app)
        self.fundo = Fundo(7)
        self.cam = Vector2(0, 0)
        self.opcoes = ["MODO CARREIRA", "DESAFIO VR - SPRINT DE ANCORAGEM",
                       "COMO JOGAR / NORMAS", "ZERAR PROGRESSO", "SAIR"]
        self.sel = 0
        self.confirma_t = 0.0
        self.botoes = [Botao((LARGURA // 2 - 170, 300 + i * 58, 460, 46), o) for i, o in enumerate(self.opcoes)]

    def evento(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_DOWN, pygame.K_s):
                self.sel = (self.sel + 1) % len(self.opcoes)
                self.app.audio.tocar("ui")
            elif ev.key in (pygame.K_UP, pygame.K_w):
                self.sel = (self.sel - 1) % len(self.opcoes)
                self.app.audio.tocar("ui")
            elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.executar(self.sel)
        for i, b in enumerate(self.botoes):
            if b.clicado(ev):
                self.sel = i
                self.executar(i)

    def executar(self, i):
        if i == 0:
            if len(NIVEIS) == 1:
                self.app.trocar(CenaBriefing(self.app, 0))
            else:
                self.app.trocar(CenaSelecaoObra(self.app))
        elif i == 1:
            self.app.trocar(CenaBriefing(self.app, 0, vr=True))
        elif i == 2:
            self.app.trocar(CenaAjuda(self.app))
        elif i == 3:
            if self.confirma_t <= 0:
                self.confirma_t = 4.0
                self.botoes[3].rotulo = "CONFIRMAR? APAGA O SAVE (CLIQUE DE NOVO)"
                self.app.audio.tocar("erro")
            else:
                self.app.progresso = {"desbloqueado": 1, "melhores": {}, "estrelas": {}, "recorde_vr": 0, "recorde_vr_pts": 0}
                self.app.salvar()
                self.confirma_t = 0.0
                self.botoes[3].rotulo = "ZERAR PROGRESSO"
                self.app.audio.tocar("ok")
        elif i == 4:
            self.app.rodando = False

    def atualizar(self, dt):
        if self.confirma_t > 0:
            self.confirma_t -= dt
            if self.confirma_t <= 0:
                self.botoes[3].rotulo = "ZERAR PROGRESSO"
        self.cam.x += dt * 12
        mpos = pygame.mouse.get_pos()
        for i, b in enumerate(self.botoes):
            b.atualizar(mpos)
            if b.hover:
                self.sel = i

    def desenhar(self, surf):
        self.fundo.desenhar(surf, self.cam, 3)
        pygame.draw.line(surf, C_ACO, (130, 60), (130, 660), 8)
        pygame.draw.line(surf, C_ACO, (290, 60), (290, 660), 8)
        for i in range(9):
            pygame.draw.line(surf, C_ACO_ESC, (120, 80 + i * 66), (300, 80 + i * 66), 6)
        desenhar_rafa(surf, 210, 250, 1.1)
        texto(surf, "SKYLINE SAFE", (LARGURA // 2 + 60, 120), "titulo", C_AMARELO, centro=True, sombra=True)
        texto(surf, "M E S T R E   D A   A L T U R A", (LARGURA // 2 + 60, 172), "sub", C_TEXTO, centro=True, sombra=True)
        texto(surf, "Simulador de inspecao e manutencao em altura", (LARGURA // 2 + 60, 212),
              "ui_p", C_TEXTO_FRACO, centro=True)
        for i, b in enumerate(self.botoes):
            b.cor = C_AMARELO if i == self.sel else C_AZUL
            b.desenhar(surf)
        p = self.app.progresso
        texto(surf, "Cargo: {}   |   Recorde VR: {} ancoragens / {} pts".format(
            cargo_do_jogador(p), p.get("recorde_vr", 0), p.get("recorde_vr_pts", 0)),
            (LARGURA // 2, ALTURA - 56), "mono_p", C_TEXTO_FRACO, centro=True)
        texto(surf, "Setas/WASD navegam - ENTER confirma - M som ({})".format(
            "desligado" if self.app.audio.mudo else ("ligado" if self.app.audio.ativo else "indisponivel")),
            (LARGURA // 2, ALTURA - 32), "mono_p", C_TEXTO_FRACO, centro=True)


# ----------------------------------------------------------------- AJUDA ----
class CenaAjuda(Cena):
    COL_A = [
        ("MOVIMENTACAO", [
            "A / D ou SETAS - deslocar na horizontal sobre as vigas",
            "W / S - subir e descer nos montantes",
            "CTRL - agachar e firmar o corpo (reduz o efeito do vento)"]),
        ("TALABARTE DUPLO (regra de ouro)", [
            "1 - ancorar / liberar o GANCHO 1 (verde)",
            "2 - ancorar / liberar o GANCHO 2 (azul)",
            "Mire com WASD: o anel branco mostra onde o gancho prende.",
            "Para avancar: ancore o gancho livre no proximo ponto e",
            "so depois libere o de tras. NUNCA os dois soltos.",
            "Sem nenhum gancho em altura = queda e falha da missao."]),
        ("PONTOS DE ANCORAGEM", [
            "Pontos enferrujados (marrons com X) estao corroidos.",
            "Ancorar neles gera infracao e o gancho cede em 3 s.",
            "Por isso o segundo gancho precisa estar em ponto bom."]),
    ]
    COL_B = [
        ("TRABALHO E RESGATE", [
            "E - iniciar tarefa na estacao (exige os 2 ganchos)",
            "R - resgatar o colega suspenso (exige os 2 ganchos)",
            "   Resgate: procedimento (1 a 5) e depois descida controlada",
            "TAB - abrir a ordem de servico"]),
        ("CLIMA", [
            "Acima de {:.0f} m/s o servico deve parar.".format(LIMITE_VENTO),
            "Va a um ABRIGO (azul) ou agache com os 2 ganchos.",
            "Se insistir, o equilibrio zera e voce cai (queda contida)."]),
        ("PRE-CHECK DE EPI", [
            "Clique nos 4 pontos da lupa (ou teclas 1-4) para inspecionar.",
            "Aprovar EPI danificado causa falha do equipamento na obra.",
            "Descartar EPI bom custa tempo. Demorar demais tambem."]),
        ("GERAL", [
            "Cada infracao custa pontos e 3 segundos.",
            "M som - -/+ volume - F1 tela cheia - ESC pausa"]),
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
        painel(surf, (50, 40, LARGURA - 100, ALTURA - 110))
        texto(surf, "MANUAL DO INSPETOR", (LARGURA // 2, 72), "sub", C_AMARELO, centro=True)
        for x, col in ((80, self.COL_A), (670, self.COL_B)):
            y = 112
            for titulo, linhas in col:
                texto(surf, titulo, (x, y), "ui_g", C_LARANJA)
                y += 30
                for l in linhas:
                    texto(surf, l, (x + 10, y), "ui_p", C_TEXTO)
                    y += 21
                y += 14
        self.voltar.desenhar(surf)


# --------------------------------------------------------- SELECAO OBRA ----
class CenaSelecaoObra(Cena):
    """Aparece quando houver mais de uma obra em NIVEIS."""

    def __init__(self, app):
        super().__init__(app)
        self.fundo = Fundo(11)
        self.sel = 0
        self.cards = [pygame.Rect(80, 150 + i * 96, 520, 82) for i in range(len(NIVEIS))]
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
            self.app.trocar(CenaBriefing(self.app, self.sel))

    def atualizar(self, dt):
        self.voltar.atualizar(pygame.mouse.get_pos())

    def desenhar(self, surf):
        self.fundo.desenhar(surf, Vector2(0, 0))
        texto(surf, "MODO CARREIRA - ORDENS DE SERVICO", (LARGURA // 2, 70), "sub", C_AMARELO, centro=True, sombra=True)
        for i, c in enumerate(self.cards):
            lib = i < self.app.progresso["desbloqueado"]
            painel(surf, c, borda=C_AMARELO if i == self.sel else C_PAINEL_BORDA,
                   cor=(24, 32, 46) if lib else (16, 18, 22))
            texto(surf, NIVEIS[i]["nome"], (c.x + 18, c.y + 14), "ui", C_TEXTO if lib else (86, 92, 104))
            texto(surf, NIVEIS[i]["local"], (c.x + 18, c.y + 40), "ui_p", C_TEXTO_FRACO if lib else (70, 74, 84))
            best = self.app.progresso["melhores"].get(str(i))
            if not lib:
                texto(surf, "BLOQUEADA", (c.right - 18, c.centery), "mono", (120, 90, 90), direita=True)
            elif best:
                texto(surf, "{} pts".format(best), (c.right - 18, c.centery - 16), "mono", C_VERDE, direita=True)
                desenhar_estrelas(surf, c.right - 62, c.centery + 18, self.app.progresso.get("estrelas", {}).get(str(i), 1), 10)
        nv = NIVEIS[self.sel]
        det = pygame.Rect(640, 150, LARGURA - 720, 360)
        painel(surf, det)
        texto(surf, "BRIEFING", (det.x + 24, det.y + 20), "ui_g", C_LARANJA)
        texto_bloco(surf, nv["briefing"], (det.x + 24, det.y + 56), det.w - 48, "ui_p")
        texto(surf, "ENTER para iniciar", (det.centerx, det.bottom - 34), "ui_p", C_AMARELO, centro=True)
        self.voltar.desenhar(surf)


# -------------------------------------------------------------- BRIEFING ----
class CenaBriefing(Cena):
    def __init__(self, app, nivel_idx, vr=False):
        super().__init__(app)
        self.nivel_idx, self.vr = nivel_idx, vr
        self.nv = NIVEIS[nivel_idx]
        self.fundo = Fundo(nivel_idx + 40, self.nv.get("tema"))
        self.dica = random.choice(DICAS_NR35)
        self.b_ok = Botao((LARGURA // 2 + 20, ALTURA - 66, 300, 46), "COMECAR  [ENTER]", pygame.K_RETURN, C_AMARELO)
        self.b_voltar = Botao((LARGURA // 2 - 320, ALTURA - 66, 300, 46), "VOLTAR  [ESC]", pygame.K_ESCAPE)

    def evento(self, ev):
        if self.b_voltar.clicado(ev):
            self.app.trocar(CenaMenu(self.app) if (self.vr or len(NIVEIS) == 1) else CenaSelecaoObra(self.app))
        elif self.b_ok.clicado(ev):
            if self.vr:
                self.app.trocar(CenaJogo(self.app, self.nivel_idx, kit_aprovado(), vr=True))
            else:
                self.app.trocar(CenaPreCheck(self.app, self.nivel_idx))

    def atualizar(self, dt):
        mp = pygame.mouse.get_pos()
        self.b_ok.atualizar(mp)
        self.b_voltar.atualizar(mp)

    def desenhar(self, surf):
        self.fundo.desenhar(surf, Vector2(0, 0))
        veu = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        veu.fill((0, 0, 0, 120))
        surf.blit(veu, (0, 0))
        esq = pygame.Rect(60, 50, 360, 560)
        painel(surf, esq)
        desenhar_rafa(surf, esq.centerx, esq.y + 150, 1.4)
        texto(surf, 'RAFAEL "RAFA" LIMA', (esq.centerx, esq.y + 290), "ui_g", C_AMARELO, centro=True)
        texto(surf, cargo_do_jogador(self.app.progresso), (esq.centerx, esq.y + 320), "ui_p", C_TEXTO_FRACO, centro=True)
        texto(surf, "Inspetor e tecnico de seguranca", (esq.centerx, esq.y + 342), "ui_p", C_TEXTO_FRACO, centro=True)
        pygame.draw.line(surf, C_PAINEL_BORDA, (esq.x + 30, esq.y + 372), (esq.right - 30, esq.y + 372), 1)
        texto_bloco(surf, '"' + (FALA_VR if self.vr else self.nv["fala"]) + '"',
                    (esq.x + 28, esq.y + 392), esq.w - 56, "ui", C_TEXTO)
        dir_ = pygame.Rect(450, 50, LARGURA - 510, 440)
        painel(surf, dir_)
        if self.vr:
            texto(surf, "DESAFIO VR - SPRINT DE ANCORAGEM", (dir_.x + 24, dir_.y + 22), "ui_g", C_AMARELO)
            y = texto_bloco(surf, "Sem pre-check, sem tarefas: so agilidade. Suba a estrutura e ancore nos "
                            "alvos laranja ALTERNANDO os ganchos. Cada acerto soma pontos e +4 s (combo "
                            "ate x5). Cada alvo tem prazo que diminui: se expirar, voce perde 5 s e o combo.",
                            (dir_.x + 24, dir_.y + 64), dir_.w - 48, "ui_p")
            y += 12
            for l in ["Tempo inicial: 90 s", "Alterne SEMPRE o gancho usado no alvo",
                      "Vento e equilibrio continuam valendo"]:
                texto(surf, "- " + l, (dir_.x + 30, y), "mono_p", C_TEXTO)
                y += 24
        else:
            texto(surf, self.nv["nome"], (dir_.x + 24, dir_.y + 22), "ui_g", C_AMARELO)
            texto(surf, self.nv["local"], (dir_.x + 24, dir_.y + 54), "ui_p", C_TEXTO_FRACO)
            y = texto_bloco(surf, self.nv["briefing"], (dir_.x + 24, dir_.y + 90), dir_.w - 48, "ui_p")
            y += 12
            linhas = [
                "Vento previsto  : {:.0f} a {:.0f} m/s".format(self.nv["vento_base"], self.nv["vento_pico"]),
                "Tarefas         : {}".format(len(self.nv["tarefas"])),
                "Resgate         : {}".format("SIM" if self.nv["resgate"] else "nao"),
                "Ancoragens ruins: {}".format(self.nv.get("ruins", 0)),
                "Altura maxima   : {:.0f} m".format((self.nv["linhas"] - 1) * self.nv["sy"] / ESCALA_METRO),
                "Tempo limite    : {:02d}:{:02d}".format(self.nv["tempo"] // 60, self.nv["tempo"] % 60),
            ]
            for l in linhas:
                texto(surf, l, (dir_.x + 30, y), "mono_p", C_TEXTO)
                y += 24
        dica = pygame.Rect(450, 510, LARGURA - 510, 100)
        painel(surf, dica, borda=C_LARANJA)
        texto(surf, "DICA DE SEGURANCA (NR-35)", (dica.x + 20, dica.y + 14), "ui_p", C_LARANJA)
        texto_bloco(surf, self.dica, (dica.x + 20, dica.y + 40), dica.w - 40, "ui", C_TEXTO)
        self.b_voltar.desenhar(surf)
        self.b_ok.desenhar(surf)


# ------------------------------------------------------------- PRE-CHECK ----
class CenaPreCheck(Cena):
    HOT = [(0.2, 0.26), (0.8, 0.26), (0.22, 0.78), (0.78, 0.78)]

    def __init__(self, app, nivel_idx):
        super().__init__(app)
        self.nivel_idx = nivel_idx
        self.kit = gerar_kit(NIVEIS[nivel_idx]["defeitos"])
        self.sel = 0
        self.fundo = Fundo(21, NIVEIS[nivel_idx].get("tema"))
        self.msg, self.msg_t = "", 0.0
        self.t_gasto = 0.0
        self.dica = random.choice(DICAS_NR35)
        self.cards = [pygame.Rect(60 + (i % 2) * 300, 150 + (i // 2) * 116, 275, 96) for i in range(len(self.kit))]
        self.det = pygame.Rect(680, 120, LARGURA - 740, 430)
        self.icone = pygame.Rect(self.det.x + 20, self.det.y + 100, 200, 200)
        self.b_aprovar = Botao((700, 566, 200, 46), "APROVAR  [A]", pygame.K_a, C_VERDE)
        self.b_descartar = Botao((920, 566, 200, 46), "DESCARTAR  [D]", pygame.K_d, C_VERMELHO)
        self.b_subir = Botao((LARGURA // 2 - 170, ALTURA - 56, 340, 44), "CONCLUIR PRE-CHECK  [ENTER]", pygame.K_RETURN)
        self.b_voltar = Botao((60, ALTURA - 56, 150, 40), "ESC", pygame.K_ESCAPE)

    @property
    def item(self):
        return self.kit[self.sel]

    def centros(self):
        return [(self.icone.x + int(fx * self.icone.w), self.icone.y + int(fy * self.icone.h)) for fx, fy in self.HOT]

    def revelar(self, i):
        if i not in self.item.revelados:
            self.item.revelados.add(i)
            self.app.audio.tocar("ui")

    def evento(self, ev):
        if self.b_voltar.clicado(ev):
            self.app.trocar(CenaBriefing(self.app, self.nivel_idx))
            return
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for i, c in enumerate(self.cards):
                if c.collidepoint(ev.pos):
                    self.sel = i
            for i, (hx, hy) in enumerate(self.centros()):
                if (ev.pos[0] - hx) ** 2 + (ev.pos[1] - hy) ** 2 <= 20 ** 2:
                    self.revelar(i)
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_DOWN, pygame.K_s):
                self.sel = (self.sel + 1) % len(self.kit)
            elif ev.key in (pygame.K_UP, pygame.K_w):
                self.sel = (self.sel - 1) % len(self.kit)
            elif ev.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                self.revelar(ev.key - pygame.K_1)
        if self.b_aprovar.clicado(ev):
            self.decidir("aprovado")
        if self.b_descartar.clicado(ev):
            self.decidir("descartado")
        if self.b_subir.clicado(ev):
            self.concluir()

    def decidir(self, d):
        if len(self.item.revelados) < 4:
            self.msg, self.msg_t = "Inspecione os 4 pontos antes de decidir.", 2.0
            self.app.audio.tocar("erro")
            return
        self.item.decisao = d
        self.msg, self.msg_t = "{} -> {}".format(self.item.sigla, d.upper()), 1.4
        self.app.audio.tocar("ok" if d == "aprovado" else "solta")
        for k in range(1, len(self.kit) + 1):
            j = (self.sel + k) % len(self.kit)
            if self.kit[j].decisao is None:
                self.sel = j
                break

    def concluir(self):
        pend = [e for e in self.kit if e.decisao is None]
        if pend:
            self.msg, self.msg_t = "Ha {} item(ns) sem decisao no pre-check.".format(len(pend)), 2.2
            self.app.audio.tocar("erro")
            return
        penal = min(60, max(0, int((self.t_gasto - TEMPO_PRECHECK_LIVRE) * 0.5)))
        self.app.trocar(CenaJogo(self.app, self.nivel_idx, self.kit, penal_tempo=penal))

    def atualizar(self, dt):
        self.t_gasto += dt
        self.msg_t = max(0.0, self.msg_t - dt)
        mp = pygame.mouse.get_pos()
        for b in (self.b_aprovar, self.b_descartar, self.b_subir, self.b_voltar):
            b.atualizar(mp)

    def desenhar(self, surf):
        self.fundo.desenhar(surf, Vector2(0, 0))
        veu = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        veu.fill((0, 0, 0, 120))
        surf.blit(veu, (0, 0))
        texto(surf, "INSPECAO PRE-USO DE EPI", (LARGURA // 2, 44), "sub", C_AMARELO, centro=True, sombra=True)
        texto(surf, NIVEIS[self.nivel_idx]["nome"], (LARGURA // 2, 80), "ui_p", C_TEXTO_FRACO, centro=True)
        mm, ss = int(self.t_gasto) // 60, int(self.t_gasto) % 60
        cor_t = C_VERMELHO if self.t_gasto > TEMPO_PRECHECK_LIVRE else C_TEXTO_FRACO
        texto(surf, "Inspecao: {:02d}:{:02d}  (apos 01:30 desconta tempo da obra)".format(mm, ss),
              (LARGURA - 40, 44), "mono_p", cor_t, direita=True)
        for i, c in enumerate(self.cards):
            it = self.kit[i]
            borda = C_AMARELO if i == self.sel else C_PAINEL_BORDA
            if it.decisao == "aprovado":
                borda = C_VERDE
            elif it.decisao == "descartado":
                borda = C_VERMELHO
            painel(surf, c, borda=borda)
            texto(surf, it.sigla, (c.x + 14, c.y + 12), "ui_g", C_LARANJA)
            texto_bloco(surf, it.nome, (c.x + 14, c.y + 42), c.w - 28, "ui_p")
            marca = {"aprovado": "APROVADO", "descartado": "DESCARTADO", None: "{}/4 pontos".format(len(it.revelados))}[it.decisao]
            cor_m = {"aprovado": C_VERDE, "descartado": C_VERMELHO, None: C_TEXTO_FRACO}[it.decisao]
            texto(surf, marca, (c.right - 12, c.y + 20), "mono_p", cor_m, direita=True)
        texto_bloco(surf, "DICA NR-35: " + self.dica, (60, 510), 560, "ui_p", C_TEXTO_FRACO)
        det, it = self.det, self.item
        painel(surf, det)
        texto(surf, "LUPA DE INSPECAO", (det.x + 22, det.y + 16), "ui_g", C_AMARELO)
        texto(surf, it.nome, (det.x + 22, det.y + 50), "ui", C_TEXTO)
        icone_epi(surf, it.sigla, self.icone)
        for i, (hx, hy) in enumerate(self.centros()):
            ok = i in it.revelados
            pygame.draw.circle(surf, (20, 60, 36) if ok else (60, 48, 12), (hx, hy), 16)
            pygame.draw.circle(surf, C_VERDE if ok else C_AMARELO, (hx, hy), 16, 2)
            texto(surf, str(i + 1), (hx, hy), "mono_p", C_VERDE if ok else C_AMARELO, centro=True)
        texto(surf, "Clique nos pontos ou tecle 1-4", (self.icone.centerx, self.icone.bottom + 18),
              "mono_p", C_TEXTO_FRACO, centro=True)
        x, y = det.x + 240, det.y + 100
        for i, linha in enumerate(it.linhas_inspecao()):
            ok = i in it.revelados
            texto(surf, "PONTO {}".format(i + 1), (x, y), "mono_p", C_LARANJA if ok else C_TEXTO_FRACO)
            if ok:
                texto_bloco(surf, linha, (x, y + 18), det.w - 262, "ui_p", C_TEXTO)
            else:
                texto(surf, "-- inspecionar --", (x, y + 18), "ui_p", C_TEXTO_FRACO)
            y += 78
        self.b_aprovar.desenhar(surf)
        self.b_descartar.desenhar(surf)
        self.b_subir.desenhar(surf)
        self.b_voltar.desenhar(surf)
        if self.msg_t > 0:
            texto(surf, self.msg, (LARGURA // 2, ALTURA - 90), "ui", C_AMARELO, centro=True)


# ------------------------------------------------------------------ JOGO ----
def criar_vinheta():
    s = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
    for i in range(36):
        a = int(160 * (1 - i / 36.0) ** 2)
        pygame.draw.rect(s, (0, 0, 24, a), (i * 6, i * 4, LARGURA - i * 12, ALTURA - i * 8), 6, border_radius=50)
    return s


class CenaJogo(Cena):
    def __init__(self, app, nivel_idx, kit, vr=False, penal_tempo=0):
        super().__init__(app)
        self.nivel_idx, self.nv, self.kit, self.vr = nivel_idx, NIVEIS[nivel_idx], kit, vr
        nv = self.nv
        self.fundo = Fundo(nivel_idx + 4, nv.get("tema"))
        self.est = Estrutura(nv["cols"], nv["linhas"], nv["sx"], nv["sy"], (240, 560))
        self.jog = Jogador(self.est, self.est.n(0, 0))
        self.cam = Vector2(0, 0)
        self.atualizar_camera(instantaneo=True)

        self.tarefas = [] if vr else [dict(no=self.est.n(*cr), tipo=t, feito=False) for (cr, t) in nv["tarefas"]]
        self.abrigos = [self.est.n(*cr) for cr in nv["abrigos"]]
        self.no_resgate = self.est.n(*nv["resgate"]) if (nv["resgate"] and not vr) else None
        self.resgate_feito = False
        self.trauma_max = float(nv.get("trauma", TEMPO_TRAUMA))
        self.trauma = self.trauma_max

        # pontos de ancoragem corroidos
        self.ruins, self.ancora_t = set(), [None, None]
        if not vr and nv.get("ruins", 0):
            proib = {t["no"] for t in self.tarefas} | set(self.abrigos) | self.est.solo
            if self.no_resgate is not None:
                proib.add(self.no_resgate)
            cand = [i for i in range(len(self.est.nodes)) if i not in proib]
            self.ruins = set(random.sample(cand, min(nv["ruins"], len(cand))))

        self.tempo = float(nv["tempo"]) if not vr else 90.0
        self.tempo -= 0 if vr else penal_tempo
        self.tempo_total = self.tempo
        self.pontos = 100.0
        self.infracoes = []
        self.mini = self.mini_ref = None
        self._mini_erros = 0
        self.msg, self.msg_t, self.msg_cor = "", 0.0, C_TEXTO
        self.terminou, self.motivo = None, ""
        self.mostrar_os = self.pausado = False
        self.flash = self.queda_anim = self.altura_max = 0.0
        self.part = Particulas()
        self.shake = 0.0
        self.tut = set()
        self.estrelas = 0
        self.novo_recorde = False
        self.t_jogo = 0.0                 # tempo real de jogo (sem pausas/tarefas)
        self.conf_pausa, self.conf_t = "", 0.0
        self.raio_t, self.raio_prox = 0.0, random.uniform(6, 14)
        self.veu_raio = None
        if nv.get("tema") == "arranha":
            self.veu_raio = pygame.Surface((LARGURA, ALTURA))
            self.veu_raio.fill((205, 215, 255))
        self.alt_total = max(1.0, max(self.est.altura_metros(p) for p in self.est.nodes))
        self.bip_t = 0.0
        self.musica_nome, self.musica_t = "jogo", 0.0
        app.audio.musica("jogo")

        self.vento = nv["vento_base"]
        self.vento_alvo = nv["vento_base"]
        self.rajada_t = random.uniform(*nv["rajada_intervalo"]) * 0.5
        self.em_rajada = False
        self.vento_prox = random.uniform(nv["vento_base"] + 2, nv["vento_pico"])
        self.mini_vento = 0.0

        self.epi_ruins = [e for e in kit if e.danificado and e.decisao == "aprovado"]
        bons_descartados = [e for e in kit if (not e.danificado) and e.decisao == "descartado"]
        self.falha_epi_t = random.uniform(25, 55) if self.epi_ruins else 1e9
        self.ganchos_ok = [True, True]
        if not vr:
            for _ in bons_descartados:
                self.pontos -= 3
                self.tempo -= 15
            if penal_tempo:
                self.avisar("Pre-check demorado: -{} s de obra".format(penal_tempo), C_LARANJA, 3.5)
        if self.epi_ruins:
            self.registrar("Pre-check falho: EPI danificado liberado para uso ({})".format(
                ", ".join(e.sigla for e in self.epi_ruins)), 12)

        # modo VR
        self.vinheta = criar_vinheta() if vr else None
        self.vr_alvo, self.vr_score, self.vr_pts, self.vr_combo = None, 0, 0, 0
        self.vr_ultimo, self.vr_t, self.vr_prazo = None, 0.0, 9.0
        if vr:
            self.jog.ganchos[0] = self.est.n(0, 0)
            self.novo_alvo_vr()
        if not self.epi_ruins and not penal_tempo:
            self.avisar("Pre-check concluido. Ancore o gancho 1 (tecla 1) e comece a subir.", C_AMARELO, 4.5)

    # ---------------------------------------------------------------- util
    def avisar(self, txt, cor=C_TEXTO, t=2.4):
        self.msg, self.msg_cor, self.msg_t = txt, cor, t

    def registrar(self, texto_inf, pontos):
        agora = max(0, int(self.tempo_total - self.tempo))
        for (t, tx, _p) in self.infracoes[-3:]:
            if tx == texto_inf and agora - t < 4:
                return
        self.infracoes.append((agora, texto_inf, pontos))
        self.pontos = max(0.0, self.pontos - pontos)
        if not self.vr:
            self.tempo -= 3.0
        self.flash = 0.35
        self.shake = max(self.shake, 0.3)
        self.part.explodir(self.jog.pos, 14, [C_VERMELHO, C_LARANJA], vel=(60, 220))
        self.avisar("INFRACAO: " + texto_inf, C_VERMELHO, 3.0)
        self.app.audio.tocar("alarme", intervalo=0.8)

    def tarefas_pendentes(self):
        return [t for t in self.tarefas if not t["feito"]]

    def direcao_atual(self):
        t = pygame.key.get_pressed()
        d = Vector2(0, 0)
        if t[pygame.K_a] or t[pygame.K_LEFT]:
            d.x -= 1
        if t[pygame.K_d] or t[pygame.K_RIGHT]:
            d.x += 1
        if t[pygame.K_w] or t[pygame.K_UP]:
            d.y -= 1
        if t[pygame.K_s] or t[pygame.K_DOWN]:
            d.y += 1
        return d

    def novo_alvo_vr(self):
        at = self.est.pos(self.jog.a)
        cand = [i for i in range(len(self.est.nodes))
                if 1.5 * self.nv["sx"] < self.est.pos(i).distance_to(at) < 3.5 * self.nv["sx"]]
        self.vr_alvo = random.choice(cand) if cand else random.randrange(len(self.est.nodes))
        self.vr_prazo = max(4.0, 9.0 - 0.35 * self.vr_score)
        self.vr_t = self.vr_prazo

    # ------------------------------------------------------------- eventos
    def evento(self, ev):
        if self.terminou:
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.app.trocar(CenaRelatorio(self.app, self))
            return
        if ev.type == getattr(pygame, "WINDOWFOCUSLOST", -1) and not self.pausado and not self.mini:
            self.pausado = True      # janela perdeu o foco: pausa sozinho
            return
        if self.pausado:
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    self.pausado = False
                    self.conf_pausa = ""
                elif ev.key in (pygame.K_r, pygame.K_q):
                    acao = "reiniciar" if ev.key == pygame.K_r else "abandonar"
                    if self.conf_pausa == acao and self.conf_t > 0:
                        if acao == "reiniciar":
                            self.app.trocar(CenaJogo(self.app, self.nivel_idx, self.kit, self.vr))
                        else:
                            self.pausado = False
                            self.finalizar(False, "Missao abandonada pelo inspetor")
                    else:
                        self.conf_pausa, self.conf_t = acao, 3.0
                        self.app.audio.tocar("erro")
                else:
                    self.conf_pausa = ""
            return
        if self.mini:
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE and self.mini_ref != "resgate":
                self.cancelar_tarefa("Tarefa interrompida. Retome quando for seguro.")
                return
            self.mini.evento(ev)
            return
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                self.pausado = True
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

    def acionar_gancho(self, i, direcao=None):
        a = self.app.audio
        if not self.ganchos_ok[i]:
            self.avisar("Gancho {} inoperante (EPI danificado)!".format(i + 1), C_VERMELHO)
            a.tocar("erro")
            return
        if direcao is None:
            direcao = self.direcao_atual()
        ok, msg = self.jog.alternar_gancho(i, direcao)
        if not ok:
            self.avisar(msg, C_VERMELHO)
            a.tocar("erro")
            return
        no = self.jog.ganchos[i]
        if no is None:
            a.tocar("solta")
            self.ancora_t[i] = None
            if msg.startswith("PERIGO"):
                self.avisar(msg, C_VERMELHO, 3.0)
                self.registrar("Permanencia em altura sem nenhum ponto de ancoragem", 10)
            else:
                self.avisar(msg, C_TEXTO, 1.2)
            return
        a.tocar("clique")
        self.part.explodir(self.est.pos(no), 10, [C_AMARELO, C_BRANCO, C_VERDE], vel=(40, 150), vida=(0.2, 0.5))
        self.avisar(msg, C_VERDE, 1.2)
        if no in self.ruins:
            self.ancora_t[i] = 3.0
            self.registrar("Ancoragem em ponto corroido, sem certificacao", 8)
            self.avisar("PONTO CORROIDO! Vai ceder: garanta o outro gancho em ponto bom!", C_VERMELHO, 3.0)
        if self.vr and no == self.vr_alvo:
            if self.vr_ultimo == i:
                self.avisar("Alterne os ganchos! Use o outro talabarte.", C_LARANJA)
                a.tocar("erro")
            else:
                self.vr_score += 1
                self.vr_combo += 1
                self.vr_pts += 10 * min(self.vr_combo, 5) + int(self.vr_t * 2)
                self.vr_ultimo = i
                self.tempo = min(90.0, self.tempo + 4.0)
                self.avisar("ANCORAGEM CORRETA  x{}  +4s".format(min(self.vr_combo, 5)), C_VERDE, 1.2)
                a.tocar("ok")
                self.novo_alvo_vr()

    def tentar_tarefa(self):
        if self.vr:
            return
        for t in self.tarefas:
            if t["feito"] or self.jog.pos.distance_to(self.est.pos(t["no"])) >= 46:
                continue
            if self.jog.ancorado < 2:
                self.registrar("Trabalho iniciado sem os dois ganchos ancorados", 8)
                self.avisar("Ancore os DOIS ganchos antes de trabalhar!", C_VERMELHO)
                return
            if self.vento > LIMITE_VENTO:
                self.registrar("Tarefa iniciada com vento acima do limite", 10)
                self.avisar("Vento acima do limite! Aguarde no abrigo.", C_VERMELHO)
                return
            self.mini, self.mini_ref, self._mini_erros = MINIJOGOS[t["tipo"]](), t, 0
            return
        self.avisar("Nenhuma estacao de manutencao ao alcance.", C_TEXTO_FRACO, 1.5)

    def cancelar_tarefa(self, msg=None):
        self.mini = self.mini_ref = None
        self.mini_vento = 0.0
        if msg:
            self.avisar(msg, C_AMARELO, 2.5)

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
        self.mini = MiniResgate(self.est.altura_metros(self.est.pos(self.no_resgate)))
        self.mini_ref, self._mini_erros = "resgate", 0

    # ----------------------------------------------------------- atualizar
    def atualizar(self, dt):
        a = self.app.audio
        self.part.atualizar(dt)
        self.shake = max(0.0, self.shake - dt)
        if self.terminou:
            self.queda_anim += dt
            a.nivel_vento = 0.0
            return
        if self.pausado:
            a.nivel_vento = 0.0
            self.conf_t = max(0.0, self.conf_t - dt)
            return
        a.nivel_vento = min(1.0, self.vento / 20.0) * 0.9
        self.atualizar_raio(dt)
        if self.mini:
            self.msg_t = max(0.0, self.msg_t - dt)
            self.flash = max(0.0, self.flash - dt)
            self.mini.atualizar(dt)
            self.atualizar_clima(dt)
            if self.mini_ref != "resgate":
                if self.vento > LIMITE_VENTO:
                    if self.mini_vento == 0.0:
                        self.avisar("VENTO ACIMA DO LIMITE! Aperte ESC e interrompa a tarefa.", C_VERMELHO, 3.0)
                        a.tocar("bip")
                    self.mini_vento += dt
                    if self.mini_vento > 3.5:
                        self.cancelar_tarefa()
                        self.registrar("Tarefa mantida com vento acima do limite", 6)
                        return
                else:
                    self.mini_vento = 0.0
            if self.mini_ref == "resgate":
                self.trauma -= dt
                if self.trauma <= 0:
                    self.finalizar(False, "Trauma por suspensao: o colega nao resistiu a espera")
                    return
            if self.mini.erros > self._mini_erros:
                self._mini_erros = self.mini.erros
                a.tocar("erro", intervalo=0.2)
            if self.mini.concluido:
                a.tocar("ok")
                self.concluir_mini()
            self.atualizar_musica(dt)
            return

        self.tempo -= dt
        self.t_jogo += dt
        self.msg_t = max(0.0, self.msg_t - dt)
        self.flash = max(0.0, self.flash - dt)
        if self.tempo <= 0:
            if self.vr:
                self.finalizar(True, "Tempo esgotado - sessao VR encerrada")
            else:
                self.finalizar(False, "Tempo da ordem de servico esgotado")
            return

        self.atualizar_clima(dt)
        self.atualizar_epi(dt)
        self.atualizar_ancoras(dt)
        if self.terminou:
            return

        t = pygame.key.get_pressed()
        self.jog.agachado = bool(t[pygame.K_LCTRL] or t[pygame.K_RCTRL])
        d = self.direcao_atual()
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
                a.tocar("estalo", intervalo=0.7)
            elif res == "BLOQUEADO_SOLO":
                self.avisar("Ancore um gancho (tecla 1 ou 2) antes de subir.", C_LARANJA, 1.2)
                self.registrar("Tentativa de subir sem ancoragem", 3)
        self.altura_max = max(self.altura_max, self.jog.altura())

        excesso = max(0.0, self.vento - 5.0)
        self.jog.sway = (math.sin(pygame.time.get_ticks() * 0.006) * min(9.0, excesso * 0.9)
                         * (0.35 if self.jog.agachado else 1.0))
        self.atualizar_equilibrio(dt, d)
        if self.terminou:
            return
        self.atualizar_objetivos(dt)
        if self.vr and not self.terminou:
            self.vr_t -= dt
            if self.vr_t <= 0:
                self.vr_combo = 0
                self.tempo -= 5.0
                self.avisar("ALVO EXPIROU  -5s", C_VERMELHO, 1.6)
                a.tocar("erro")
                self.novo_alvo_vr()
        if self.vento > LIMITE_VENTO:
            self.bip_t -= dt
            if self.bip_t <= 0:
                a.tocar("bip")
                self.bip_t = 0.9
        self.atualizar_tutorial()
        self.atualizar_musica(dt)
        self.atualizar_camera()

    def atualizar_raio(self, dt):
        """Tempestade na Obra 05: relampagos ocasionais (so visual)."""
        if self.veu_raio is None:
            return
        self.raio_t = max(0.0, self.raio_t - dt)
        self.raio_prox -= dt
        if self.raio_prox <= 0:
            self.raio_t = 0.22
            self.raio_prox = random.uniform(9, 22)

    def atualizar_tutorial(self):
        """Dicas contextuais na Obra 01 (aparecem uma vez, quando fazem sentido)."""
        if self.nivel_idx != 0 or self.vr or self.msg_t > 0:
            return
        j = self.jog

        def dica(chave, txt):
            if chave in self.tut:
                return False
            self.tut.add(chave)
            self.avisar("DICA: " + txt, C_AZUL, 5.0)
            return True
        if j.ancorado == 1 and j.altura() > 1.5 and dica("troca", "ancore o outro gancho (tecla 2) mais a frente e so depois solte o de tras."):
            return
        if any((not t["feito"]) and j.pos.distance_to(self.est.pos(t["no"])) < 70 for t in self.tarefas) \
                and dica("tarefa", "estacao de manutencao: ancore os DOIS ganchos e aperte E."):
            return
        if self.vento > LIMITE_VENTO and dica("vento", "vento acima do limite! Va a um ABRIGO (azul) ou agache (CTRL) com os 2 ganchos."):
            return
        if self.ruins and any(i in self.ruins and j.pos.distance_to(self.est.pos(i)) < 150 for i in self.ruins):
            dica("ruim", "pontos marrons com X estao corroidos: nao ancore neles.")

    def atualizar_musica(self, dt):
        self.musica_t += dt
        if self.terminou:
            alvo = None
        elif self.no_resgate is not None and not self.resgate_feito and (
                self.mini_ref == "resgate" or self.trauma < self.trauma_max * 0.85):
            alvo = "resgate"
        elif self.vento > LIMITE_VENTO or self.tempo < 45:
            alvo = "tensao"
        else:
            alvo = "jogo"
        if alvo != self.musica_nome and (self.musica_t > 8.0 or self.musica_nome is None):
            self.musica_nome, self.musica_t = alvo, 0.0
            self.app.audio.musica(alvo)

    def atualizar_clima(self, dt):
        self.rajada_t -= dt
        if self.rajada_t <= 0:
            self.em_rajada = not self.em_rajada
            if self.em_rajada:
                self.vento_alvo = self.vento_prox
                self.rajada_t = random.uniform(5, 11)
                if self.vento_alvo > LIMITE_VENTO:
                    self.avisar("ALERTA: rajada acima do limite! Procure abrigo.", C_LARANJA, 3.0)
            else:
                self.vento_alvo = random.uniform(self.nv["vento_base"] * 0.6, self.nv["vento_base"] + 1.5)
                self.vento_prox = random.uniform(self.nv["vento_base"] + 2, self.nv["vento_pico"])
                self.rajada_t = random.uniform(*self.nv["rajada_intervalo"])
        self.vento += (self.vento_alvo - self.vento) * min(1.0, dt * 0.9)
        self.vento += math.sin(pygame.time.get_ticks() * 0.004) * 0.05

    def checar_sem_ancoragem(self, motivo):
        if self.jog.ancorado == 0 and not self.jog.no_solo() and not self.terminou:
            self.finalizar(False, motivo)

    def atualizar_epi(self, dt):
        self.falha_epi_t -= dt
        if self.falha_epi_t > 0 or not self.epi_ruins:
            return
        e = self.epi_ruins.pop(0)
        self.falha_epi_t = random.uniform(35, 70) if self.epi_ruins else 1e9
        self.app.audio.tocar("estalo")
        if e.sigla in ("TAL", "MSQ") and all(self.ganchos_ok):
            idx = random.choice([0, 1])
            self.ganchos_ok[idx] = False
            self.jog.ganchos[idx] = None
            self.ancora_t[idx] = None
            self.registrar("Falha do {}: gancho {} inutilizado em servico".format(e.sigla, idx + 1), 15)
            self.checar_sem_ancoragem("Falha de EPI sem segunda ancoragem: queda fatal")
        elif e.sigla == "FTA":
            presos = [i for i, g in enumerate(self.jog.ganchos) if g is not None]
            if presos:
                i = random.choice(presos)
                self.jog.ganchos[i] = None
                self.ancora_t[i] = None
            self.registrar("Falha da FTA: fita de ancoragem rompeu em servico", 15)
            self.checar_sem_ancoragem("Fita de ancoragem rompeu sem segunda ancoragem: queda fatal")
        elif e.sigla == "CAP":
            self.jog.suspenso = 2.0
            self.registrar("Falha do CAP: impacto atordoou o inspetor (capacete defeituoso)", 12)
        elif e.sigla == "TRQ":
            self.registrar("Falha do TRQ: trava-quedas nao bloqueou em teste de campo", 15)
            self.jog.equilibrio = min(self.jog.equilibrio, 40)
        else:
            self.registrar("Falha em servico do EPI {} aprovado no pre-check".format(e.sigla), 12)
            self.jog.equilibrio = max(10, self.jog.equilibrio - 25)

    def atualizar_ancoras(self, dt):
        for i in (0, 1):
            if self.ancora_t[i] is None:
                continue
            g = self.jog.ganchos[i]
            if g is None or g not in self.ruins:
                self.ancora_t[i] = None
                continue
            self.ancora_t[i] -= dt
            if self.ancora_t[i] <= 0:
                self.jog.ganchos[i] = None
                self.ancora_t[i] = None
                self.avisar("O PONTO DE ANCORAGEM CEDEU!", C_VERMELHO, 2.5)
                self.app.audio.tocar("estalo")
                self.registrar("Ponto de ancoragem cedeu", 5)
                self.checar_sem_ancoragem("Ponto de ancoragem cedeu sem segunda ancoragem: queda fatal")

    def em_abrigo(self):
        return self.jog.no_solo() or any(self.jog.pos.distance_to(self.est.pos(n)) < 60 for n in self.abrigos)

    def atualizar_equilibrio(self, dt, direcao):
        excesso = self.vento - LIMITE_VENTO
        protegido = self.em_abrigo() or (self.jog.agachado and self.jog.ancorado >= 2)
        if excesso > 0 and not protegido:
            dreno = (6 + excesso * 5) * dt * (1.9 if direcao.length_squared() > 0 else 1.0)
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
                self.jog.equilibrio, self.jog.suspenso = 55.0, 2.6
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
                self.avisar("Tudo concluido. Desca ate o solo com seguranca.", C_VERDE, 2.0)

    def concluir_mini(self):
        m = self.mini
        if self.mini_ref == "resgate":
            self.resgate_feito = True
            if m.erros:
                self.registrar("Erros na manobra de resgate ({} eventos de procedimento/velocidade)".format(m.erros),
                               min(25, m.erros * 5))
            self.avisar("RESGATE CONCLUIDO. Vitima entregue ao socorro.", C_VERDE, 3.5)
        else:
            self.mini_ref["feito"] = True
            if m.erros:
                self.registrar("Erros de execucao em {}".format(NOME_TAREFA[self.mini_ref["tipo"]]),
                               min(12, m.erros * 2))
            else:
                self.pontos = min(100.0, self.pontos + 2)
                self.avisar("Tarefa concluida sem erros. +2 pts", C_VERDE, 2.5)
        self.mini = self.mini_ref = None

    def finalizar(self, sucesso, motivo):
        if self.terminou:
            return
        self.terminou = "sucesso" if sucesso else "falha"
        self.motivo = motivo
        a = self.app.audio
        a.musica(None)
        a.nivel_vento = 0.0
        a.tocar("sucesso" if sucesso else "falha")
        if sucesso:
            self.part.confete(self.cam)
        else:
            self.shake = 0.6
        p = self.app.progresso
        if self.vr:
            p["recorde_vr"] = max(p.get("recorde_vr", 0), self.vr_score)
            p["recorde_vr_pts"] = max(p.get("recorde_vr_pts", 0), self.vr_pts)
        elif sucesso:
            self.estrelas = estrelas_de(self.pontos, self.infracoes)
            est_d = p.setdefault("estrelas", {})
            est_d[str(self.nivel_idx)] = max(est_d.get(str(self.nivel_idx), 0), self.estrelas)
            anterior = p["melhores"].get(str(self.nivel_idx), 0)
            self.novo_recorde = int(self.pontos) > anterior and anterior > 0
            p["melhores"][str(self.nivel_idx)] = max(anterior, int(self.pontos))
            if self.nivel_idx + 1 >= p["desbloqueado"]:
                p["desbloqueado"] = min(len(NIVEIS), self.nivel_idx + 2)
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
        cam_real = self.cam
        if self.shake > 0 and not self.pausado:
            amp = 12.0 * min(1.0, self.shake / 0.3)
            self.cam = cam_real + Vector2(random.uniform(-amp, amp), random.uniform(-amp, amp))
        elif self.vento > LIMITE_VENTO and not self.pausado and not self.terminou:
            amp = min(5.0, (self.vento - LIMITE_VENTO) * 0.8)
            self.cam = cam_real + Vector2(random.uniform(-amp, amp), random.uniform(-amp, amp))
        self.fundo.desenhar(surf, self.cam, self.vento)
        self.desenhar_tema(surf)
        self.desenhar_estrutura(surf)
        self.desenhar_estacoes(surf)
        self.jog.desenhar(surf, self.cam)
        self.desenhar_previa(surf)
        self.desenhar_particulas_vento(surf)
        self.desenhar_chuva(surf)
        self.part.desenhar(surf, self.cam)
        self.cam = cam_real
        if self.vinheta is not None:
            surf.blit(self.vinheta, (0, 0))
        if self.raio_t > 0 and self.veu_raio is not None:
            self.veu_raio.set_alpha(int(95 * self.raio_t / 0.22))
            surf.blit(self.veu_raio, (0, 0))
        self.desenhar_guias(surf)
        self.desenhar_hud(surf)
        self.desenhar_regua(surf)
        self.desenhar_dica_controles(surf)
        if self.mostrar_os:
            self.desenhar_os(surf)
        if self.mini:
            self.mini.desenhar(surf)
            if self.mini_ref != "resgate":
                r = self.mini.rect
                if self.vento > LIMITE_VENTO:
                    texto(surf, "VENTO ACIMA DO LIMITE - ESC interrompe ({:.0f}s)".format(max(0.0, 3.5 - self.mini_vento)),
                          (r.centerx, r.bottom + 24), "ui", C_VERMELHO, centro=True, sombra=True)
                else:
                    texto(surf, "ESC interrompe a tarefa", (r.centerx, r.bottom + 24), "ui_p", C_TEXTO_FRACO, centro=True)
        if self.flash > 0:
            v = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
            v.fill((220, 40, 40, int(90 * self.flash / 0.35)))
            surf.blit(v, (0, 0))
        if self.pausado:
            self.desenhar_pausa(surf)
        if self.terminou:
            self.desenhar_fim(surf)

    def desenhar_tema(self, surf):
        """Cenario de fundo da obra. Adicione um ramo por novo tema."""
        tema = self.nv.get("tema")
        est, cam, r = self.est, self.cam, self.est.rect
        x0, x1 = r.left - cam.x, r.right - cam.x
        xc = (x0 + x1) / 2
        topo, chao = r.top - cam.y, est.chao_y - cam.y
        if chao < -50:
            return
        yb = min(chao, ALTURA + 10)
        if tema == "predio":
            ya = max(topo + 100, -10)
            if yb > ya:
                pygame.draw.rect(surf, (96, 100, 108), (x0 + 70, ya, x1 - x0 - 140, yb - ya))
                pygame.draw.rect(surf, (70, 74, 82), (x0 + 70, ya, 18, yb - ya))
                pygame.draw.rect(surf, (70, 74, 82), (x1 - 88, ya, 18, yb - ya))
            for rr in range(est.linhas):
                y = est.pos(est.n(0, rr)).y - cam.y
                if -80 < y < ALTURA + 20:
                    pygame.draw.line(surf, (60, 64, 72), (x0 + 70, y + 8), (x1 - 70, y + 8), 10)
                    pygame.draw.rect(surf, (128, 132, 140), (xc - 30, y - 70, 60, 70), border_radius=3)
                    pygame.draw.line(surf, (80, 84, 92), (xc, y - 70), (xc, y), 2)
            gx = x1 + 40  # guindaste ao fundo
            pygame.draw.line(surf, (214, 168, 40), (gx, chao), (gx, topo - 30), 8)
            pygame.draw.line(surf, (214, 168, 40), (gx - 220, topo - 30), (gx + 80, topo - 30), 6)
            pygame.draw.line(surf, (40, 40, 40), (gx - 190, topo - 24), (gx - 190, topo + 60), 2)
        elif tema == "torre":
            # colinas ao fundo
            if chao < ALTURA + 200:
                for cor, alt, desl in (((86, 56, 72), 150, 0), ((64, 48, 52), 90, 220)):
                    pts = [(0, chao)]
                    for hx in range(0, LARGURA + 80, 80):
                        pts.append((hx, chao - alt - math.sin(hx * 0.006 + desl) * 40))
                    pts.append((LARGURA, chao))
                    pygame.draw.polygon(surf, cor, pts)
            # torre de treliça: duas pernas inclinadas + contraventamento
            base_w, topo_w = (x1 - x0) - 120, 70.0
            ytor = topo + 60

            def perna(t, lado):
                return (xc + lado * (topo_w + (base_w - topo_w) * t) / 2.0, ytor + (chao - ytor) * t)
            for lado in (-1, 1):
                pygame.draw.line(surf, (58, 52, 60), perna(0, lado), perna(1, lado), 7)
            n_seg = 10
            for k in range(n_seg):
                t0, t1 = k / n_seg, (k + 1) / n_seg
                pygame.draw.line(surf, (74, 68, 78), perna(t0, -1), perna(t1, 1), 3)
                pygame.draw.line(surf, (74, 68, 78), perna(t0, 1), perna(t1, -1), 3)
                pygame.draw.line(surf, (74, 68, 78), perna(t1, -1), perna(t1, 1), 4)
            # cruzetas, isoladores e cabos
            for t in (0.0, 0.14, 0.28):
                cx_, cy_ = xc, ytor + (chao - ytor) * t
                pygame.draw.line(surf, (58, 52, 60), (cx_ - 240, cy_), (cx_ + 240, cy_), 6)
                for lado in (-1, 1):
                    ix = cx_ + lado * 230
                    pygame.draw.line(surf, (214, 206, 190), (ix, cy_), (ix, cy_ + 26), 5)
                    pts = [(ix + lado * k * 40, cy_ + 26 + math.sin(k * 0.5) * 6 + k * 3.5) for k in range(0, 40)]
                    pygame.draw.lines(surf, (40, 36, 44), False, pts, 2)
        elif tema == "turbina":
            # campo verde ao fundo
            if chao < ALTURA + 200:
                for cor, alt, desl in (((92, 140, 88), 120, 0), ((70, 118, 70), 70, 300)):
                    pts = [(0, chao)]
                    for hx in range(0, LARGURA + 80, 80):
                        pts.append((hx, chao - alt - math.sin(hx * 0.005 + desl) * 34))
                    pts.append((LARGURA, chao))
                    pygame.draw.polygon(surf, cor, pts)
            hub = (xc, topo + 70)
            larg_t, larg_b = 34.0, 96.0
            pygame.draw.polygon(surf, (226, 230, 236), [(xc - larg_t / 2, hub[1]), (xc + larg_t / 2, hub[1]),
                                                        (xc + larg_b / 2, chao), (xc - larg_b / 2, chao)])
            pygame.draw.polygon(surf, (190, 196, 206), [(xc + larg_t / 6, hub[1]), (xc + larg_t / 2, hub[1]),
                                                        (xc + larg_b / 2, chao), (xc + larg_b / 6, chao)])
            for k in range(1, 6):
                yy = hub[1] + (chao - hub[1]) * k / 6.0
                pygame.draw.line(surf, (170, 176, 188), (xc - larg_b / 2 * k / 6 - 12, yy),
                                 (xc + larg_b / 2 * k / 6 + 12, yy), 2)
            ang0 = pygame.time.get_ticks() * 0.00035 * (0.6 + self.vento * 0.12)
            for k in range(3):
                a = ang0 + k * 2.0944
                ux, uy = math.cos(a), math.sin(a)
                nx, ny = -uy, ux
                ponta = (hub[0] + ux * 250, hub[1] + uy * 250)
                pygame.draw.polygon(surf, (238, 240, 244), [(hub[0] + nx * 9, hub[1] + ny * 9),
                                                            (hub[0] - nx * 9, hub[1] - ny * 9), ponta])
                pygame.draw.line(surf, C_VERMELHO, (hub[0] + ux * 215, hub[1] + uy * 215), ponta, 3)
            pygame.draw.circle(surf, (210, 214, 222), (int(hub[0]), int(hub[1])), 16)
            pygame.draw.rect(surf, (210, 214, 222), (hub[0] - 20, hub[1] - 12, 70, 26), border_radius=8)
        elif tema == "arranha":
            fx0, fx1 = x0 + 60, x1 - 60
            ya = max(topo + 60, -10)
            if yb > ya:
                pygame.draw.rect(surf, (18, 26, 48), (fx0, ya, fx1 - fx0, yb - ya))
                pygame.draw.rect(surf, (34, 46, 78), (fx0, ya, 16, yb - ya))
                pygame.draw.rect(surf, (10, 14, 28), (fx1 - 16, ya, 16, yb - ya))
                for jx in range(int(fx0) + 30, int(fx1) - 20, 36):
                    for jy in range(int(ya) + 14, int(yb) - 10, 40):
                        if (jx // 36 * 7 + (jy - int(cam.y * 0)) // 40 * 13) % 5 in (0, 1):
                            pygame.draw.rect(surf, (236, 212, 128), (jx, jy, 18, 24))
                        else:
                            pygame.draw.rect(surf, (28, 40, 70), (jx, jy, 18, 24))
            ax, ay = xc, topo + 60
            pygame.draw.line(surf, (110, 118, 134), (ax, ay), (ax, ay - 90), 5)
            if (pygame.time.get_ticks() // 600) % 2 == 0:
                pygame.draw.circle(surf, C_VERMELHO, (int(ax), int(ay - 92)), 6)
                pygame.draw.circle(surf, (255, 150, 150), (int(ax), int(ay - 92)), 11, 2)
        elif tema == "ponte":
            ytop = max(topo + 40, -10)
            deck_y = chao - 30
            # pilone de concreto atras da estrutura
            if yb > ytop:
                pygame.draw.rect(surf, (150, 154, 160), (xc - 34, ytop, 68, yb - ytop))
                pygame.draw.rect(surf, (118, 122, 130), (xc - 34, ytop, 14, yb - ytop))
            # cabos estaiados em leque do topo do pilone ate o tabuleiro
            pt = (xc, topo + 50)
            for k in range(1, 9):
                dx = k * 150
                pygame.draw.line(surf, (214, 214, 220), pt, (xc - dx, deck_y), 2)
                pygame.draw.line(surf, (214, 214, 220), pt, (xc + dx, deck_y), 2)
            # tabuleiro
            if -40 < deck_y < ALTURA:
                pygame.draw.rect(surf, (96, 100, 108), (0, deck_y, LARGURA, 30))
                pygame.draw.line(surf, (60, 64, 72), (0, deck_y), (LARGURA, deck_y), 4)
                for fx in range(-int(cam.x) % 60 - 60, LARGURA, 60):
                    pygame.draw.line(surf, C_AMARELO, (fx, deck_y + 14), (fx + 30, deck_y + 14), 3)

    def desenhar_estrutura(self, surf):
        cam = self.cam
        tm = TEMAS.get(self.nv.get("tema"), TEMAS[None])
        chao_y = self.est.chao_y - cam.y
        if chao_y < ALTURA:
            pygame.draw.rect(surf, tm["chao"], (0, chao_y, LARGURA, ALTURA - chao_y))
            pygame.draw.line(surf, (70, 78, 70), (0, chao_y), (LARGURA, chao_y), 3)
            if self.nv.get("tema") == "ponte":
                t = pygame.time.get_ticks() * 0.002
                for wy in range(int(chao_y) + 14, ALTURA, 22):
                    pts = [(x, wy + math.sin(x * 0.03 + t + wy) * 3) for x in range(0, LARGURA + 20, 20)]
                    pygame.draw.lines(surf, (70, 130, 176), False, pts, 2)
        for c in range(self.est.cols - 1):
            for r in range(self.est.linhas - 1):
                p1 = self.est.pos(self.est.n(c, r)) - cam
                p2 = self.est.pos(self.est.n(c + 1, r + 1)) - cam
                if -100 < p1.y < ALTURA + 100:
                    pygame.draw.line(surf, C_ACO_ESC, p1, p2, 3)
        for (a, b) in self.est.edges:
            p1, p2 = self.est.pos(a) - cam, self.est.pos(b) - cam
            if max(p1.y, p2.y) < -60 or min(p1.y, p2.y) > ALTURA + 60:
                continue
            pygame.draw.line(surf, C_ACO_ESC, p1, p2, 9)
            pygame.draw.line(surf, C_ACO, p1, p2, 6)
            pygame.draw.line(surf, C_ACO_LUZ, (p1.x, p1.y - 2), (p2.x, p2.y - 2), 1)
        for i, p0 in enumerate(self.est.nodes):
            p = p0 - cam
            x, y = int(p.x), int(p.y)
            if not (-40 < y < ALTURA + 40):
                continue
            if i in self.abrigos:
                pygame.draw.circle(surf, C_AZUL, (x, y), 15, 2)
                texto(surf, "ABRIGO", (x, y - 26), "mono_p", C_AZUL, centro=True)
            if i in self.ruins:
                pygame.draw.circle(surf, (24, 20, 18), (x, y), 10)
                pygame.draw.circle(surf, (150, 78, 36), (x, y), 9, 3)
                pygame.draw.line(surf, (210, 110, 50), (x - 5, y - 5), (x + 5, y + 5), 2)
                pygame.draw.line(surf, (210, 110, 50), (x - 5, y + 5), (x + 5, y - 5), 2)
                if i in self.jog.ganchos:
                    texto(surf, "CEDENDO!", (x, y - 24), "mono_p", C_VERMELHO, centro=True)
                continue
            ancorado = i in self.jog.ganchos
            perto = self.jog.pos.distance_to(p0) <= min(RAIO_ANCORAGEM, CABO_MAX)
            cor = C_VERDE if ancorado else (C_AMARELO if perto else (110, 108, 86))
            pygame.draw.circle(surf, (25, 28, 34), (x, y), 9)
            pygame.draw.circle(surf, cor, (x, y), 8, 2)
            pygame.draw.circle(surf, cor, (x, y), 3)
        if self.vr and self.vr_alvo is not None:
            p = self.est.pos(self.vr_alvo) - cam
            raio = 18 + math.sin(pygame.time.get_ticks() * 0.008) * 5
            pygame.draw.circle(surf, C_LARANJA, (int(p.x), int(p.y)), int(raio), 3)
            texto(surf, "ANCORAR AQUI", (int(p.x), int(p.y) - 34), "mono_p", C_LARANJA, centro=True)

    def desenhar_previa(self, surf):
        """Anel que mostra onde o proximo gancho vai prender."""
        if self.terminou or self.mini or self.pausado:
            return
        if all(g is not None or not ok for g, ok in zip(self.jog.ganchos, self.ganchos_ok)):
            return
        alvo = self.jog.alvo_gancho(self.direcao_atual())
        if alvo is None:
            return
        p = self.est.pos(alvo) - self.cam
        raio = 16 + int(math.sin(pygame.time.get_ticks() * 0.01) * 2)
        pygame.draw.circle(surf, C_VERMELHO if alvo in self.ruins else C_BRANCO, (int(p.x), int(p.y)), raio, 2)

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
            texto(surf, {"solda": "SLD", "aperto": "TRQ", "lampada": "LMP", "sequencia": "END"}[t["tipo"]], r.center,
                  "mono_p", C_AMARELO, centro=True)
            if self.jog.pos.distance_to(self.est.pos(t["no"])) < 46:
                texto(surf, "[E] " + NOME_TAREFA[t["tipo"]], (int(p.x), int(p.y - 58)), "ui_p", C_BRANCO, centro=True)
        if self.no_resgate is not None and not self.resgate_feito:
            p = self.est.pos(self.no_resgate) - self.cam
            bal = math.sin(pygame.time.get_ticks() * 0.002) * 6
            cx, cy = int(p.x + bal), int(p.y + 44)
            desenhar_cabo(surf, p, (cx, cy - 14), C_VERMELHO, 6, 2)
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
        t = pygame.time.get_ticks() * 0.35
        for i in range(int(self.vento * 3)):
            x = (i * 137 + t * (1 + self.vento * 0.16)) % (LARGURA + 200) - 100
            y = (i * 271 + self.cam.y * 0.4) % ALTURA
            surf.blit(risco_vento(int(8 + self.vento * 2), 60 if self.vento < LIMITE_VENTO else 120), (x, y))

    def desenhar_chuva(self, surf):
        if self.veu_raio is None:
            return
        t = pygame.time.get_ticks()
        inc = 3 + self.vento * 1.1
        for i in range(70 + int(self.vento * 5)):
            x = (i * 193 + t * 0.12 * (1 + self.vento * 0.05)) % (LARGURA + 120) - 60
            y = (i * 71 + t * (0.9 + (i % 5) * 0.08)) % (ALTURA + 40) - 20
            pygame.draw.line(surf, (128, 146, 196), (x, y), (x - inc, y + 12), 1)

    def desenhar_regua(self, surf):
        """Regua vertical de altura: onde voce esta, tarefas, resgate e abrigos."""
        if self.mini or self.pausado:
            return
        x, y0, y1 = LARGURA - 24, 200, ALTURA - 112
        pygame.draw.rect(surf, (20, 26, 36), (x - 5, y0 - 8, 10, y1 - y0 + 16), border_radius=5)
        pygame.draw.rect(surf, C_PAINEL_BORDA, (x - 5, y0 - 8, 10, y1 - y0 + 16), 1, border_radius=5)

        def yy(no_pos):
            f = max(0.0, min(1.0, self.est.altura_metros(no_pos) / self.alt_total))
            return int(y1 - f * (y1 - y0))
        for n in self.abrigos:
            pygame.draw.rect(surf, C_AZUL, (x - 8, yy(self.est.pos(n)) - 1, 16, 3))
        for t in self.tarefas_pendentes():
            pygame.draw.circle(surf, C_AMARELO, (x, yy(self.est.pos(t["no"]))), 4)
        if self.no_resgate is not None and not self.resgate_feito:
            pygame.draw.circle(surf, C_VERMELHO, (x, yy(self.est.pos(self.no_resgate))), 5)
        if self.vr and self.vr_alvo is not None:
            pygame.draw.circle(surf, C_LARANJA, (x, yy(self.est.pos(self.vr_alvo))), 5, 2)
        py = yy(self.jog.pos)
        pygame.draw.polygon(surf, C_BRANCO, [(x - 9, py), (x - 17, py - 5), (x - 17, py + 5)])
        pygame.draw.circle(surf, C_BRANCO, (x, py), 3)
        texto(surf, "{:.0f}m".format(self.alt_total), (x, y0 - 18), "mono_p", C_TEXTO_FRACO, centro=True)

    def desenhar_dica_controles(self, surf):
        if self.t_jogo > 16 or self.mini or self.pausado or self.terminou:
            return
        txt = "1/2 ganchos  |  WASD mover  |  CTRL agachar  |  E tarefa  |  R resgate  |  TAB ordem  |  ESC pausa"
        if self.vr:
            txt = "1/2 ancoram os ganchos  |  WASD mover  |  alterne o gancho a cada alvo  |  ESC pausa"
        cor = C_TEXTO_FRACO if self.t_jogo < 12 else (96, 106, 120)
        texto(surf, txt, (LARGURA // 2, ALTURA - 172), "mono_p", cor, centro=True, sombra=True)

    def desenhar_guias(self, surf):
        """Setas na borda da tela apontando o proximo objetivo (ou o abrigo, com vento forte)."""
        if self.vr or self.terminou or self.mini or self.pausado:
            return
        alvo = None
        if self.vento > LIMITE_VENTO and self.abrigos and not self.em_abrigo():
            alvo = (min(self.abrigos, key=lambda i: self.jog.pos.distance_to(self.est.pos(i))), "ABRIGO", C_AZUL)
        else:
            cand = [(t["no"], {"solda": "SLD", "aperto": "TRQ", "lampada": "LMP", "sequencia": "END"}[t["tipo"]], C_AMARELO)
                    for t in self.tarefas_pendentes()]
            if self.no_resgate is not None and not self.resgate_feito:
                cand.append((self.no_resgate, "RESGATE", C_VERMELHO))
            if cand:
                alvo = min(cand, key=lambda c: self.jog.pos.distance_to(self.est.pos(c[0])))
            elif not self.jog.no_solo() and self.est.solo:
                alvo = (min(self.est.solo, key=lambda i: self.jog.pos.distance_to(self.est.pos(i))), "SOLO", C_VERDE)
        if alvo is None:
            return
        no, rot, cor = alvo
        p = self.est.pos(no) - self.cam
        if -30 <= p.x <= LARGURA + 30 and -30 <= p.y <= ALTURA + 30:
            return
        c = Vector2(LARGURA / 2, ALTURA / 2)
        d = p - c
        if d.length_squared() == 0:
            return
        k = min((LARGURA / 2 - 70) / abs(d.x) if d.x else 1e9, (ALTURA / 2 - 190) / abs(d.y) if d.y else 1e9)
        pos = c + d * k
        dn = d.normalize()
        perp = Vector2(-dn.y, dn.x)
        pts = [pos + dn * 16, pos - dn * 8 + perp * 11, pos - dn * 8 - perp * 11]
        pygame.draw.polygon(surf, cor, pts)
        pygame.draw.polygon(surf, C_BRANCO, pts, 2)
        dy = self.est.altura_metros(self.est.pos(no)) - self.jog.altura()
        lp = pos - dn * 38
        texto(surf, "{} {:+.0f} m".format(rot, dy), (int(max(70, min(LARGURA - 70, lp.x))), int(lp.y)),
              "mono_p", cor, centro=True, sombra=True)

    def desenhar_hud(self, surf):
        painel(surf, (16, 12, 420, 96), alpha=210)
        cor_p = C_VERDE if self.pontos >= 85 else (C_AMARELO if self.pontos >= 60 else C_VERMELHO)
        texto(surf, "SEGURANCA", (32, 24), "mono_p", C_TEXTO_FRACO)
        texto(surf, "{:.0f}".format(self.pontos), (150, 18), "sub", cor_p)
        barra(surf, (32, 50, 180, 10), self.pontos / 100.0, cor_p)
        texto(surf, "ALTURA", (250, 24), "mono_p", C_TEXTO_FRACO)
        texto(surf, "{:.1f} m".format(self.jog.altura()), (250, 40), "hud", C_TEXTO)
        mm, ss = int(max(0, self.tempo)) // 60, int(max(0, self.tempo)) % 60
        texto(surf, "TEMPO", (340, 24), "mono_p", C_TEXTO_FRACO)
        texto(surf, "{:02d}:{:02d}".format(mm, ss), (340, 40), "hud", C_VERMELHO if self.tempo < 45 else C_TEXTO)
        texto(surf, "EQUILIBRIO", (32, 70), "mono_p", C_TEXTO_FRACO)
        eq = self.jog.equilibrio
        barra(surf, (120, 70, 290, 12), eq / 100.0, C_VERDE if eq > 50 else (C_AMARELO if eq > 25 else C_VERMELHO))
        self.desenhar_anemometro(surf, (LARGURA - 118, 96))

        painel(surf, (16, ALTURA - 96, 380, 80), alpha=210)
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
                tens = self.jog.pos.distance_to(self.est.pos(g)) / CABO_MAX
                estado = "ANCORADO  (tensao {:.0f}%)".format(tens * 100)
                if g in self.ruins:
                    cor = C_VERMELHO
                elif tens > 0.85:
                    cor = C_LARANJA
            pygame.draw.circle(surf, cor, (40, y + 7), 7)
            texto(surf, "[{}] GANCHO {} : {}".format(i + 1, i + 1, estado), (56, y), "mono_p", cor)
        if self.jog.ancorado == 0 and not self.jog.no_solo() and (pygame.time.get_ticks() // 300) % 2 == 0:
            texto(surf, "!! SEM ANCORAGEM - NAO SE MOVA !!", (LARGURA // 2, 140), "ui_g", C_VERMELHO,
                  centro=True, sombra=True)

        painel(surf, (LARGURA - 300, ALTURA - 96, 284, 80), alpha=210)
        if self.vr:
            texto(surf, "DESAFIO VR", (LARGURA - 286, ALTURA - 88), "mono_p", C_TEXTO_FRACO)
            texto(surf, "{} ancor.  {} pts  x{}".format(self.vr_score, self.vr_pts, min(self.vr_combo, 5)),
                  (LARGURA - 286, ALTURA - 66), "ui_p", C_AMARELO)
            texto(surf, "PRAZO DO ALVO", (LARGURA - 286, ALTURA - 44), "mono_p", C_TEXTO_FRACO)
            barra(surf, (LARGURA - 286, ALTURA - 28, 250, 8), self.vr_t / max(0.1, self.vr_prazo),
                  C_LARANJA if self.vr_t > 2 else C_VERMELHO)
        else:
            texto(surf, "ORDEM DE SERVICO  [TAB]", (LARGURA - 286, ALTURA - 88), "mono_p", C_TEXTO_FRACO)
            texto(surf, "Tarefas restantes: {}".format(len(self.tarefas_pendentes())),
                  (LARGURA - 286, ALTURA - 64), "ui_p", C_TEXTO)
            if self.no_resgate is not None and not self.resgate_feito:
                tr = max(0, int(self.trauma))
                texto(surf, "Resgate - trauma em {:02d}:{:02d}".format(tr // 60, tr % 60),
                      (LARGURA - 286, ALTURA - 40), "ui_p", C_VERMELHO if self.trauma < 45 else C_LARANJA)
            elif self.resgate_feito:
                texto(surf, "Resgate concluido", (LARGURA - 286, ALTURA - 40), "ui_p", C_VERDE)
        if self.msg_t > 0:
            r = pygame.Rect(0, 0, FONTES["ui"].size(self.msg)[0] + 40, 40)
            r.center = (LARGURA // 2, ALTURA - 130)
            painel(surf, r, alpha=225, borda=self.msg_cor)
            texto(surf, self.msg, r.center, "ui", self.msg_cor, centro=True)

    def desenhar_anemometro(self, surf, centro):
        cx, cy, raio = centro[0], centro[1], 52
        painel(surf, (cx - 100, cy - 84, 200, 168), alpha=215)
        texto(surf, "ANEMOMETRO", (cx, cy - 70), "mono_p", C_TEXTO_FRACO, centro=True)
        pygame.draw.circle(surf, (30, 36, 46), (cx, cy), raio)
        for i in range(0, 21, 2):
            ang = math.radians(210 - i * 10)
            r1 = raio - (10 if i % 4 == 0 else 5)
            pygame.draw.line(surf, C_VERMELHO if i > LIMITE_VENTO else C_TEXTO_FRACO,
                             (cx + math.cos(ang) * r1, cy - math.sin(ang) * r1),
                             (cx + math.cos(ang) * raio, cy - math.sin(ang) * raio), 2)
        v = max(0.0, min(20.0, self.vento))
        ang = math.radians(210 - v * 10)
        cor = C_VERMELHO if self.vento > LIMITE_VENTO else C_VERDE
        pygame.draw.line(surf, cor, (cx, cy), (cx + math.cos(ang) * (raio - 8), cy - math.sin(ang) * (raio - 8)), 4)
        pygame.draw.circle(surf, C_ACO_LUZ, (cx, cy), 5)
        texto(surf, "{:.1f} m/s".format(self.vento), (cx, cy + 34), "hud", cor, centro=True)
        if self.vento > LIMITE_VENTO:
            texto(surf, "ACIMA DO LIMITE", (cx, cy + 58), "mono_p", C_VERMELHO, centro=True)
        else:
            texto(surf, "limite {:.0f} m/s".format(LIMITE_VENTO), (cx, cy + 58), "mono_p", C_TEXTO_FRACO, centro=True)
        if not self.terminou and not self.em_rajada and self.rajada_t < 8:
            forte = self.vento_prox > LIMITE_VENTO
            if not forte or (pygame.time.get_ticks() // 300) % 2 == 0:
                texto(surf, ("RAJADA FORTE EM {}s" if forte else "rajada leve em {}s").format(int(self.rajada_t) + 1),
                      (cx, cy + 98), "mono_p", C_LARANJA if forte else C_TEXTO_FRACO, centro=True, sombra=True)

    def desenhar_os(self, surf):
        r = pygame.Rect(0, 0, 640, 460)
        r.center = (LARGURA // 2, ALTURA // 2)
        veu = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        veu.fill((0, 0, 0, 130))
        surf.blit(veu, (0, 0))
        painel(surf, r)
        texto(surf, "ORDEM DE SERVICO", (r.centerx, r.y + 26), "sub", C_AMARELO, centro=True)
        texto(surf, self.nv["nome"], (r.centerx, r.y + 60), "ui_p", C_TEXTO_FRACO, centro=True)
        y = r.y + 96
        for t in self.tarefas:
            alt = self.est.altura_metros(self.est.pos(t["no"]))
            texto(surf, "{} {}  -  {:.0f} m".format("[X]" if t["feito"] else "[ ]", NOME_TAREFA[t["tipo"]], alt),
                  (r.x + 40, y), "ui_p", C_VERDE if t["feito"] else C_TEXTO)
            y += 28
        if self.no_resgate is not None:
            texto(surf, "{} Resgate do colega suspenso".format("[X]" if self.resgate_feito else "[ ]"),
                  (r.x + 40, y), "ui_p", C_VERDE if self.resgate_feito else C_VERMELHO)
            y += 28
        texto(surf, "Pontos de ancoragem corroidos na estrutura: {} (marrons com X)".format(len(self.ruins)),
              (r.x + 40, y + 6), "ui_p", C_LARANJA)
        y += 44
        texto(surf, "EPI EM USO", (r.x + 40, y), "ui_g", C_LARANJA)
        y += 28
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
        texto(surf, "ESC retoma  |  R reinicia a obra  |  Q abandona  |  M som  |  - / + volume",
              (LARGURA // 2, ALTURA // 2 + 20), "ui", C_TEXTO_FRACO, centro=True)
        if self.conf_t > 0 and self.conf_pausa:
            texto(surf, "Aperte {} de novo para confirmar ({:.0f}s)".format(
                "R" if self.conf_pausa == "reiniciar" else "Q", self.conf_t + 0.5), (LARGURA // 2, ALTURA // 2 + 64), "ui_g", C_AMARELO,
                centro=True, sombra=True)

    def desenhar_fim(self, surf):
        veu = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        veu.fill((0, 0, 0, min(200, int(self.queda_anim * 320))))
        surf.blit(veu, (0, 0))
        ok = self.terminou == "sucesso"
        texto(surf, "MISSAO CONCLUIDA" if ok else "MISSAO FALHOU", (LARGURA // 2, ALTURA // 2 - 50), "titulo",
              C_VERDE if ok else C_VERMELHO, centro=True, sombra=True)
        texto(surf, self.motivo, (LARGURA // 2, ALTURA // 2 + 10), "ui", C_TEXTO, centro=True)
        texto(surf, "ENTER para ver o relatorio", (LARGURA // 2, ALTURA // 2 + 60), "ui_p", C_TEXTO_FRACO, centro=True)


# ------------------------------------------------------------- RELATORIO ----
class CenaRelatorio(Cena):
    def __init__(self, app, jogo):
        super().__init__(app)
        self.j = jogo
        self.fundo = Fundo(31, jogo.nv.get("tema"))
        tem_prox = (not jogo.vr) and jogo.terminou == "sucesso" and jogo.nivel_idx + 1 < len(NIVEIS)
        if tem_prox:
            self.b_menu = Botao((200, ALTURA - 62, 240, 44), "MENU [ESC]", pygame.K_ESCAPE)
            self.b_rep = Botao((520, ALTURA - 62, 240, 44), "REPETIR [ENTER]", pygame.K_RETURN, C_AMARELO)
            self.b_prox = Botao((840, ALTURA - 62, 240, 44), "PROXIMA OBRA [N]", pygame.K_n, C_VERDE)
        else:
            self.b_menu = Botao((340, ALTURA - 62, 240, 44), "MENU [ESC]", pygame.K_ESCAPE)
            self.b_rep = Botao((700, ALTURA - 62, 240, 44), "REPETIR [ENTER]", pygame.K_RETURN, C_AMARELO)
            self.b_prox = None
        self.scroll = 0

    def evento(self, ev):
        if self.b_menu.clicado(ev):
            self.app.trocar(CenaMenu(self.app))
        elif self.b_rep.clicado(ev):
            if self.j.vr:
                self.app.trocar(CenaJogo(self.app, self.j.nivel_idx, kit_aprovado(), vr=True))
            else:
                self.app.trocar(CenaPreCheck(self.app, self.j.nivel_idx))
        elif self.b_prox and self.b_prox.clicado(ev):
            self.app.trocar(CenaBriefing(self.app, self.j.nivel_idx + 1))
        if ev.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, self.scroll - ev.y * 30)

    def atualizar(self, dt):
        mp = pygame.mouse.get_pos()
        for b in (self.b_menu, self.b_rep, self.b_prox):
            if b:
                b.atualizar(mp)

    def classificacao(self):
        p = self.j.pontos
        if self.j.vr:
            return "SESSAO VR ENCERRADA", C_AMARELO
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
        j = self.j
        self.fundo.desenhar(surf, Vector2(0, 0))
        veu = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        veu.fill((0, 0, 0, 150))
        surf.blit(veu, (0, 0))
        r = pygame.Rect(90, 24, LARGURA - 180, 606)
        painel(surf, r)
        texto(surf, "RELATORIO DE SEGURANCA - SESSAO VR" if j.vr else "RELATORIO DE SEGURANCA DO SERVICO",
              (r.centerx, r.y + 26), "sub", C_AMARELO, centro=True)
        texto(surf, "Desafio VR - Sprint de Ancoragem" if j.vr else j.nv["nome"], (r.centerx, r.y + 60),
              "ui_p", C_TEXTO_FRACO, centro=True)
        cls, cor_cls = self.classificacao()
        texto(surf, cls, (r.centerx, r.y + 94), "ui_g", cor_cls, centro=True)
        if not j.vr and j.terminou == "sucesso":
            desenhar_estrelas(surf, r.right - 110, r.y + 40, j.estrelas, 15)
            if j.novo_recorde:
                texto(surf, "NOVO RECORDE!", (r.right - 110, r.y + 74), "mono_p", C_VERDE, centro=True)
            if j.estrelas < 3:
                texto(surf, "3 estrelas: 95+ pts e zero infracoes", (r.right - 40, r.y + 100), "mono_p",
                      C_TEXTO_FRACO, direita=True)
        x, y = r.x + 40, r.y + 132
        if j.vr:
            texto(surf, "Ancoragens corretas : {}".format(j.vr_score), (x, y), "mono", C_TEXTO)
            y += 26
            texto(surf, "Pontos VR           : {}".format(j.vr_pts), (x, y), "mono", C_AMARELO)
            y += 26
            texto(surf, "Recorde             : {} ancor. / {} pts".format(
                self.app.progresso.get("recorde_vr", 0), self.app.progresso.get("recorde_vr_pts", 0)),
                (x, y), "mono", C_TEXTO)
            y += 26
        else:
            feitas = sum(1 for t in j.tarefas if t["feito"])
            texto(surf, "Pontuacao final     : {:.0f} / 100".format(j.pontos), (x, y), "mono", C_TEXTO)
            y += 26
            texto(surf, "Tarefas concluidas  : {}/{}".format(feitas, len(j.tarefas)), (x, y), "mono", C_TEXTO)
            y += 26
            if j.no_resgate is not None:
                texto(surf, "Resgate             : {}".format("CONCLUIDO" if j.resgate_feito else "NAO REALIZADO"),
                      (x, y), "mono", C_VERDE if j.resgate_feito else C_VERMELHO)
                y += 26
            tj = int(j.t_jogo)
            texto(surf, "Altura max. {:.1f} m  |  Tempo {:02d}:{:02d}".format(j.altura_max, tj // 60, tj % 60),
                  (x, y), "mono", C_TEXTO)
            y += 26
        texto(surf, "Total de infracoes  : {}".format(len(j.infracoes)), (x, y), "mono",
              C_VERDE if not j.infracoes else C_VERMELHO)
        y += 34
        if not j.vr:
            texto(surf, "AUDITORIA DO PRE-CHECK", (x, y), "ui_g", C_LARANJA)
            y += 30
            acertos = 0
            for e in j.kit:
                ok = (e.decisao == "descartado") == e.danificado
                acertos += 1 if ok else 0
                detalhe = e.defeito if e.danificado else "conforme"
                texto(surf, "[{}] {} - {}".format("OK  " if ok else "ERRO", e.sigla, detalhe[:50]), (x + 8, y),
                      "mono_p", C_VERDE if ok else C_VERMELHO)
                y += 21
            texto(surf, "Acertos no pre-check: {}/{}".format(acertos, len(j.kit)), (x + 8, y + 6), "mono",
                  C_VERDE if acertos == len(j.kit) else C_LARANJA)
        x2, y2 = r.centerx + 30, r.y + 132
        texto(surf, "REGISTRO DE INFRACOES", (x2, y2), "ui_g", C_LARANJA)
        y2 += 30
        if not j.infracoes:
            texto(surf, "Nenhuma infracao registrada. Excelente trabalho.", (x2 + 8, y2), "ui_p", C_VERDE)
        else:
            vis = int((r.bottom - 140 - y2) // 44)
            for (t, txt, p) in j.infracoes[self.scroll // 44:][:vis]:
                texto(surf, "{:02d}:{:02d}  -{} pts".format(t // 60, t % 60, p), (x2 + 8, y2), "mono_p", C_VERMELHO)
                y2 = texto_bloco(surf, txt, (x2 + 8, y2 + 18), r.right - x2 - 50, "ui_p") + 8
            if len(j.infracoes) > vis:
                texto(surf, "... role a roda do mouse para ver mais", (x2 + 8, r.bottom - 150), "mono_p", C_TEXTO_FRACO)
        caixa = pygame.Rect(r.x + 24, r.bottom - 124, r.w - 48, 108)
        painel(surf, caixa, borda=C_LARANJA)
        licoes = licoes_para(j.infracoes)
        if j.terminou == "sucesso" and not j.vr and j.nivel_idx == len(NIVEIS) - 1 and not j.infracoes:
            texto(surf, "RAFA", (caixa.x + 16, caixa.y + 10), "ui_p", C_LARANJA)
            texto_bloco(surf, "Obra sem nenhuma infracao. Hoje todo mundo volta pra casa - e e assim que se vira "
                        "referencia e mentor de equipes.", (caixa.x + 16, caixa.y + 34), caixa.w - 32, "ui", C_TEXTO)
        elif licoes:
            texto(surf, "LICOES DE SEGURANCA (NR-35)", (caixa.x + 16, caixa.y + 8), "ui_p", C_LARANJA)
            yy = caixa.y + 30
            for l in licoes:
                yy = texto_bloco(surf, "- " + l, (caixa.x + 16, yy), caixa.w - 32, "ui_p", C_TEXTO, 2)
        else:
            texto(surf, "DICA", (caixa.x + 16, caixa.y + 8), "ui_p", C_LARANJA)
            texto_bloco(surf, random.Random(len(j.kit) + int(j.pontos)).choice(DICAS_NR35),
                        (caixa.x + 16, caixa.y + 34), caixa.w - 32, "ui", C_TEXTO)
        for b in (self.b_menu, self.b_rep, self.b_prox):
            if b:
                b.desenhar(surf)


# =============================================================================
# 10. APLICACAO
# =============================================================================

class App:
    def __init__(self):
        try:
            pygame.mixer.pre_init(22050, -16, 1, 512)
        except Exception:
            pass
        pygame.init()
        pygame.display.set_caption(TITULO)
        try:
            # SCALED: a janela pode ser redimensionada e o mouse continua correto
            self.tela = pygame.display.set_mode((LARGURA, ALTURA), pygame.SCALED | pygame.RESIZABLE)
        except Exception:
            self.tela = pygame.display.set_mode((LARGURA, ALTURA))
        self.relogio = pygame.time.Clock()
        carregar_fontes()
        self.rodando = True
        self.vol_t = 0.0
        self.progresso = {"desbloqueado": 1, "melhores": {}, "estrelas": {}, "recorde_vr": 0, "recorde_vr_pts": 0}
        self.carregar()
        self.audio = Audio()
        try:
            self.audio.volume = max(0.0, min(1.0, float(self.progresso.get("volume", 1.0))))
            self.audio.mudo = bool(self.progresso.get("mudo", False))
        except Exception:
            pass
        self.cena = CenaMenu(self)
        self.audio.musica("menu")

    def carregar(self):
        try:
            with open(ARQUIVO_SAVE, "r", encoding="utf-8") as f:
                d = json.load(f)
            self.progresso["desbloqueado"] = int(d.get("desbloqueado", 1))
            self.progresso["melhores"] = dict(d.get("melhores", {}))
            self.progresso["estrelas"] = dict(d.get("estrelas", {}))
            self.progresso["recorde_vr"] = int(d.get("recorde_vr", 0))
            self.progresso["recorde_vr_pts"] = int(d.get("recorde_vr_pts", 0))
            self.progresso["volume"] = float(d.get("volume", 1.0))
            self.progresso["mudo"] = bool(d.get("mudo", False))
        except Exception:
            pass

    def salvar(self):
        try:
            a = getattr(self, "audio", None)
            if a is not None:
                self.progresso["volume"] = a.volume
                self.progresso["mudo"] = a.mudo
            tmp = ARQUIVO_SAVE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.progresso, f, ensure_ascii=False, indent=2)
            os.replace(tmp, ARQUIVO_SAVE)
        except Exception:
            pass

    def trocar(self, cena):
        self.cena = cena
        if not isinstance(cena, CenaJogo):
            self.audio.musica("menu")
            self.audio.nivel_vento = 0.0

    def rodar(self):
        while self.rodando:
            dt = min(0.05, self.relogio.tick(FPS) / 1000.0)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.rodando = False
                elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_F1:
                    pygame.display.toggle_fullscreen()
                elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_m:
                    self.audio.mudo = not self.audio.mudo
                    self.salvar()
                elif ev.type == pygame.KEYDOWN and ev.key in (pygame.K_MINUS, pygame.K_KP_MINUS,
                                                              pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    passo = -0.1 if ev.key in (pygame.K_MINUS, pygame.K_KP_MINUS) else 0.1
                    self.audio.volume = max(0.0, min(1.0, round(self.audio.volume + passo, 2)))
                    self.vol_t = 1.6
                    self.salvar()
                else:
                    self.cena.evento(ev)
            self.cena.atualizar(dt)
            self.cena.desenhar(self.tela)
            if self.vol_t > 0:
                self.vol_t -= dt
                texto(self.tela, "Volume: {:.0f}%".format(self.audio.volume * 100), (LARGURA // 2, 24), "ui",
                      C_AMARELO, centro=True, sombra=True)
            self.audio.atualizar()
            pygame.display.flip()
        self.salvar()
        pygame.quit()
        sys.exit(0)


def main():
    App().rodar()


if __name__ == "__main__":
    main()
