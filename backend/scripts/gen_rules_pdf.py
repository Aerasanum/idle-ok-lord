"""Genera il Regolamento completo di IDLE 1 (PDF, sola lettura, nessuna password di apertura).

Ogni numero è letto dal CANONICAL_SPEC (v1.2) o calcolato con le stesse formule del server (app/domain/formulas.py),
quindi il documento coincide sempre con ciò che il gioco applica davvero.

Uso: python scripts/gen_rules_pdf.py  ->  static/IDLE1_Regolamento_v1.2.pdf
"""
from __future__ import annotations

import hashlib
import os
import secrets
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pypdf import PdfReader, PdfWriter
from pypdf.constants import UserAccessPermissions
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, NextPageTemplate, PageBreak, PageTemplate, Paragraph, Spacer, Table,
                                TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

from app.core.canon import canon
from app.domain import formulas as F

C = canon()
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
OUT = os.path.join(OUT_DIR, "IDLE1_Regolamento.pdf")

# ---------------------------------------------------------------- fonts / styles
FONT_DIR = "/usr/share/fonts/truetype/liberation"
pdfmetrics.registerFont(TTFont("Body", f"{FONT_DIR}/LiberationSans-Regular.ttf"))
pdfmetrics.registerFont(TTFont("BodyB", f"{FONT_DIR}/LiberationSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("BodyI", f"{FONT_DIR}/LiberationSans-Italic.ttf"))
_title_font = "/app/frontend/assets/fonts/CormorantGaramond-Bold.ttf"
pdfmetrics.registerFont(TTFont("Title", _title_font if os.path.exists(_title_font) else f"{FONT_DIR}/LiberationSerif-Bold.ttf"))

GOLD = colors.HexColor("#8A6A1F")
INK = colors.HexColor("#1B1F27")
MUTED = colors.HexColor("#5B6270")
ZEBRA = colors.HexColor("#F4F0E6")
HEAD = colors.HexColor("#2B2F3A")
LINE = colors.HexColor("#C9BFA8")

S = {
    "cover": ParagraphStyle("cover", fontName="Title", fontSize=40, leading=46, textColor=INK, alignment=TA_CENTER),
    "cover2": ParagraphStyle("cover2", fontName="Title", fontSize=20, leading=26, textColor=GOLD, alignment=TA_CENTER),
    "cover3": ParagraphStyle("cover3", fontName="Body", fontSize=10.5, leading=15, textColor=MUTED, alignment=TA_CENTER),
    "h1": ParagraphStyle("h1", fontName="Title", fontSize=24, leading=28, textColor=INK, spaceBefore=6, spaceAfter=8),
    "h2": ParagraphStyle("h2", fontName="BodyB", fontSize=13, leading=17, textColor=GOLD, spaceBefore=12, spaceAfter=4),
    "h3": ParagraphStyle("h3", fontName="BodyB", fontSize=10.5, leading=14, textColor=INK, spaceBefore=8, spaceAfter=3),
    "p": ParagraphStyle("p", fontName="Body", fontSize=9.5, leading=13.5, textColor=INK, spaceAfter=5),
    "why": ParagraphStyle("why", fontName="BodyI", fontSize=9, leading=13, textColor=MUTED, leftIndent=8, spaceAfter=6,
                          borderPadding=(2, 4, 2, 4)),
    "li": ParagraphStyle("li", fontName="Body", fontSize=9.5, leading=13.5, textColor=INK, leftIndent=12, bulletIndent=2, spaceAfter=2),
    "cell": ParagraphStyle("cell", fontName="Body", fontSize=7.4, leading=9, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName="BodyB", fontSize=7.4, leading=9, textColor=colors.white),
    "small": ParagraphStyle("small", fontName="Body", fontSize=8, leading=11, textColor=MUTED, spaceAfter=4),
}
TOC_STYLES = [
    ParagraphStyle("toc1", fontName="BodyB", fontSize=10.5, leading=15, textColor=INK),
    ParagraphStyle("toc2", fontName="Body", fontSize=9, leading=12.5, textColor=INK, leftIndent=14),
]

RES = {"grain": "Grano", "wood": "Legno", "clay": "Argilla", "iron": "Ferro", "gold": "Oro", "rubies": "Rubini", "forge_dust": "Polvere di Forgia",
       "reforge_stone": "Pietra di Riforgiatura", "mythic_essence": "Essenza Mitica", "war_coins": "Monete di Guerra", "event_tokens": "Gettoni Evento"}
RES_ORDER = ["grain", "wood", "clay", "iron", "gold"]
RARITY_IT = {"common": "Comune", "uncommon": "Non comune", "rare": "Raro", "epic": "Epico", "legendary": "Leggendario", "mythic": "Mitico", "ancient": "Antico"}
SLOT_IT = {"weapon": "Arma", "offhand": "Mano secondaria", "helmet": "Elmo", "chest": "Corazza", "gloves": "Guanti", "boots": "Stivali", "cloak": "Mantello",
           "ring": "Anello", "amulet": "Amuleto"}
AFFIX_IT = {"crit_chance_pct": "Probabilità critico %", "crit_damage_pct": "Danno critico %", "attack_speed_pct": "Velocità d'attacco %", "dodge_pct": "Schivata %",
            "lifesteal_pct": "Rubavita %", "boss_damage_pct": "Danno ai boss %", "army_power_pct": "Potenza esercito %", "gold_find_pct": "Oro trovato %",
            "gear_find_pct": "Equipaggiamento trovato %"}
CAT_IT = {"regular": "Regolare", "siege": "Assedio", "beast": "Bestia", "mythic": "Mitica"}
ROLE_IT = {"frontline": "Prima linea", "ranged": "A distanza", "mobile": "Mobile", "siege": "Assedio", "domain": "Sfondamento", "assault": "Assalto",
           "scout": "Esploratore", "heavy": "Pesante", "legendary": "Leggendaria"}
CLASS_IT = C["units"]["counters"]["class_labels"]
SKILL_IT = {"power_strike": "Colpo Potente", "war_cry": "Grido di Guerra", "shield_wall": "Muro di Scudi", "rain_of_steel": "Pioggia d'Acciaio",
            "royal_strike": "Colpo Reale", "dragon_banner": "Stendardo del Drago"}
TALENT_IT = {"warrior": ("Guerriero", "+2% attacco dell'eroe per rango"), "guardian": ("Guardiano", "+2% PV e difesa dell'eroe per rango"),
             "commander": ("Comandante", "+1,5% potenza dell'esercito per rango"), "fortune": ("Fortuna", "+1,5% oro e drop di equipaggiamento per rango")}
EFFECT_IT = {
    "grain_production_pct": "Produzione grano", "wood_production_pct": "Produzione legno", "clay_production_pct": "Produzione argilla",
    "iron_production_pct": "Produzione ferro", "gold_production_pct": "Produzione oro", "warehouse_capacity_pct": "Capacità magazzino",
    "construction_speed_pct": "Velocità costruzione", "construction_cost_reduction_pct": "Riduzione costi costruzione", "wall_defense_pct": "Difesa mura",
    "castle_upgrade_speed_pct": "Velocità potenziamento castello", "infantry_power_pct": "Potenza Fanteria", "archer_power_pct": "Potenza Arcieri",
    "cavalry_power_pct": "Potenza Cavalleria", "all_regular_units_power_pct": "Potenza unità regolari", "army_hp_pct": "PV esercito",
    "army_power_pct": "Potenza esercito", "catapult_power_pct": "Potenza Catapulte", "siege_damage_pct": "Danno unità d'assedio",
    "fortress_attack_pct": "Attacco alle fortezze (guerra)", "conquest_wagon_power_pct": "Potenza Ariete d'Assedio", "siege_units_power_pct": "Potenza unità d'assedio",
    "beast_power_pct": "Potenza bestie", "beast_recruit_speed_pct": "Velocità reclutamento bestie", "wolf_falcon_power_pct": "Potenza Lupo e Falco",
    "bear_lion_power_pct": "Potenza Orso e Leone", "elephant_power_pct": "Potenza Elefante", "mythic_power_pct": "Potenza unità mitiche",
    "dragon_power_pct": "Potenza Drago", "angel_power_pct": "Potenza Angelo", "demon_power_pct": "Potenza Demone", "mythic_hp_pct": "PV unità mitiche",
    "offline_loot_pct": "Bottino offline", "event_deploy_speed_pct": "Velocità spedizioni evento", "domain_reward_pct": "Ricompense del dominio",
    "all_resource_production_pct": "Produzione di tutte le risorse", "alliance_donation_reward_pct": "Ricompense donazioni alleanza",
    "war_roster_power_pct": "Potenza roster di guerra", "war_defense_pct": "Difesa in guerra", "territory_bonus_cap_pct": "Tetto bonus territoriali",
    "alliance_reward_pct": "Ricompense alleanza",
}
BRANCH_IT = {"economy": "Economia", "construction": "Costruzione", "military": "Militare", "siege": "Assedio", "beasts": "Bestie", "mythic": "Mitico",
             "domain": "Dominio", "alliance": "Alleanza"}


def n(x) -> str:
    """Formato italiano: 1.234.567 · decimali con virgola."""
    if isinstance(x, float) and not x.is_integer():
        return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{int(round(x)):,}".replace(",", ".")


def t(minutes: float) -> str:
    m = int(round(minutes))
    if m <= 0:
        return "istantaneo"
    d, r = divmod(m, 1440)
    h, mi = divmod(r, 60)
    parts = ([f"{d}g"] if d else []) + ([f"{h}h"] if h else []) + ([f"{mi}m"] if mi or not (d or h) else [])
    return " ".join(parts)


def P(text, style="p"):
    return Paragraph(text, S[style])


def WHY(text):
    return Paragraph(f"<b>Perché:</b> {text}", S["why"])


def LI(items):
    return [Paragraph(f"• {i}", S["li"]) for i in items]


def cell(v, bold=False):
    return Paragraph(str(v), S["cellb" if bold else "cell"])


def tbl(header, rows, widths=None, align_right_from=1):
    data = [[cell(h, True) for h in header]] + [[cell(v) for v in r] for r in rows]
    tb = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    st = [("BACKGROUND", (0, 0), (-1, 0), HEAD), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEBELOW", (0, 0), (-1, -1), 0.25, LINE),
          ("TOPPADDING", (0, 0), (-1, -1), 2.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2), ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]
    for i in range(1, len(data)):
        if i % 2 == 0:
            st.append(("BACKGROUND", (0, i), (-1, i), ZEBRA))
    tb.setStyle(TableStyle(st))
    return tb


# ---------------------------------------------------------------- document template with TOC + bookmarks
class Doc(BaseDocTemplate):
    def __init__(self, path):
        super().__init__(path, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=18 * mm, bottomMargin=16 * mm,
                         title="IDLE 1 · Regolamento completo v1.2", author="IDLE 1", subject="Regole, unità, costi, ricerche, formule")
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="f")
        self.addPageTemplates([PageTemplate(id="cover", frames=[frame]), PageTemplate(id="body", frames=[frame], onPage=self._decorate)])
        self._n = 0

    def _decorate(self, canv, doc):
        canv.saveState()
        canv.setFont("Body", 7.5)
        canv.setFillColor(MUTED)
        canv.drawString(self.leftMargin, A4[1] - 11 * mm, f"IDLE 1 · Regolamento completo · spec v{C['document']['version']}")
        canv.drawRightString(A4[0] - self.rightMargin, A4[1] - 11 * mm, f"Pagina {doc.page}")
        canv.setStrokeColor(LINE)
        canv.line(self.leftMargin, A4[1] - 12.5 * mm, A4[0] - self.rightMargin, A4[1] - 12.5 * mm)
        canv.drawCentredString(A4[0] / 2, 9 * mm, "Ogni valore proviene dal CANONICAL_SPEC v1.2 e dalle formule del server: nessun numero è inventato.")
        canv.restoreState()

    def afterFlowable(self, fl):
        if isinstance(fl, Paragraph) and fl.style.name in ("h1", "h2"):
            level = 0 if fl.style.name == "h1" else 1
            text = fl.getPlainText()
            key = "k" + hashlib.sha1(text.encode()).hexdigest()[:12]  # stable across multiBuild passes
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=level, closed=False)
            self.notify("TOCEntry", (level, text, self.page, key))


def H1(text):
    return Paragraph(text, S["h1"])


def H2(text):
    return Paragraph(text, S["h2"])


def H3(text):
    return Paragraph(text, S["h3"])


# ---------------------------------------------------------------- content
def cover():
    return [Spacer(1, 60 * mm), Paragraph("IDLE 1", S["cover"]), Spacer(1, 6 * mm), Paragraph("Regolamento completo", S["cover2"]),
            Spacer(1, 4 * mm), Paragraph("Regole, unità e contro-unità, costi e tempi di costruzione, esperienza dell'eroe, ricerche, equipaggiamento, "
                                          "campagna, dominio, alleanze e guerre. Tutto ciò che il server applica, spiegato.", S["cover3"]),
            Spacer(1, 10 * mm), Paragraph(f"Specifica canonica v{C['document']['version']} · stato {C['document']['status']}", S["cover3"]),
            Paragraph("Documento di sola lettura, consultabile da tutti.", S["cover3"]), NextPageTemplate("body"), PageBreak()]


def toc():
    toc_ = TableOfContents()
    toc_.levelStyles = TOC_STYLES
    toc_.dotsMinLevel = 0
    return [Paragraph("Indice", S["h1"].clone("h1toc")), toc_, PageBreak()]


def sec_intro():
    b, o = C["battle"], C["offline"]
    return [
        H1("1. Come funziona IDLE 1"),
        P(C["product"]["combat_fantasy"].replace("The player begins as one warrior and ends leading a visually enormous medieval-fantasy army against monster hordes, giant bosses, beasts and mythic enemies.",
                                                 "Inizi come un unico guerriero, il <b>Lord</b>, e finisci alla guida di un esercito medievale-fantasy enorme contro orde di mostri, boss giganti, bestie e nemici mitici.")),
        H2("1.1 Il ciclo di gioco"),
        *LI([
            "<b>Battaglia automatica</b>: il Lord (e il suo esercito) affronta uno stage della Campagna. Il risultato è deciso dal server confrontando la tua potenza con quella richiesta.",
            "<b>Bottino</b>: XP per l'eroe, Oro, risorse e equipaggiamento. Gli stage già superati vengono <i>farmati</i> in automatico (anche offline).",
            "<b>Regno</b>: le risorse pagano edifici, ricerche e reclutamento. Il Castello sblocca tutto il resto.",
            "<b>Esercito</b>: dallo stage 10 schieri unità che si sommano alla potenza del Lord; ogni unità è forte o debole contro certe classi di nemici.",
            "<b>Dominio</b>: ogni 2 stage superati conquisti una casella della tua mappa 10x10 e aumenti la produzione.",
            "<b>Alleanze</b>: chat, Titan Hunt e guerre 10 contro 10 asincrone per il controllo della mappa stagionale.",
        ]),
        H2("1.2 Regole di fondo (valgono ovunque)"),
        *LI([
            "<b>Server-autoritativo</b>: ogni calcolo (potenza, ricompense, timer, acquisti) è eseguito dal server. L'app anima soltanto il risultato. L'orologio del telefono non è mai usato.",
            f"<b>Nessuna casualità nell'esito</b> della Campagna: vinci se <i>potenza totale ≥ potenza richiesta</i>. Il caso esiste solo in drop e animazioni.",
            f"<b>Nessuna perdita permanente</b>: le unità reclutate non muoiono mai, né in PvE né in Guerra d'Alleanza ({C['units']['casualties']}).",
            f"<b>Offline</b>: il gioco progredisce fino a <b>{o['max_hours']} ore</b> senza di te, con efficienza {int(o['resource_efficiency']*100)}% sulle risorse, "
            f"{int(o['battle_loot_efficiency']*100)}% sul bottino di battaglia e {int(o['gear_roll_efficiency']*100)}% sui tiri equipaggiamento. Costruzioni, ricerche e reclutamenti proseguono al 100%.",
            "<b>Niente pay-to-win diretto</b>: nessun acquisto casuale di equipaggiamento (gacha); i Rubini accelerano tempi e comprano cosmetici o risorse limitate al giorno.",
        ]),
        WHY("il gioco deve essere equo e verificabile: due giocatori con la stessa potenza ottengono lo stesso risultato, e nessuno può barare modificando l'orologio o il client."),
    ]


def sec_resources():
    r = C["resources"]
    init = r["initial"]
    rows = [[RES[k], n(v)] for k, v in init.items() if v]
    prod_b = {"grain": "Fattoria", "wood": "Boscaiolo", "clay": "Cava d'Argilla", "iron": "Miniera di Ferro", "gold": "Miniera d'Oro + bottino di battaglia"}
    use = {"grain": "cibo per reclutare unità (voce di costo più alta per bestie)", "wood": "edifici, ricerche, macchine d'assedio", "clay": "edifici e ricerche",
           "iron": "armi: unità, edifici militari, ricerche", "gold": "tutto: Forgia, Riforgiatura, alleanze (creazione 5.000), espansioni inventario"}
    return [
        H1("2. Risorse"),
        P("Cinque risorse <b>morbide</b> alimentano il Regno; tre <b>materiali</b> servono alla Forgia; i <b>Rubini</b> sono la valuta premium; "
          "<b>Monete di Guerra</b> e <b>Gettoni Evento</b> si guadagnano solo in alleanza ed eventi."),
        tbl(["Risorsa", "Da dove arriva", "A cosa serve"],
            [[RES[k], prod_b[k], use[k]] for k in RES_ORDER] + [
                [RES["forge_dust"], "Smantellamento oggetti, dungeon Forge Depths, missioni", "Potenziare la Forgia di ogni slot (permanente)"],
                [RES["reforge_stone"], "Smantellamento di leggendari+, dungeon, missioni settimanali", "Ritirare un affisso di un oggetto (Riforgiatura)"],
                [RES["mythic_essence"], "Smantellamento mitici/antichi, Ancient Ruins tier 7+", "Materiale di fascia alta (pass e missioni)"],
                [RES["rubies"], "Missioni, calendario accessi, traguardi, Codex, negozio", "Accelerare timer, ingressi extra, casse risorse, cosmetici"],
                [RES["war_coins"], "Guerre d'Alleanza e Titan Hunt", "Ricompense di alleanza"],
                [RES["event_tokens"], "Spedizioni evento, Monster Hunt", "Avanzare nel tracciato evento (1 punto ciascuno)"]],
            widths=[38 * mm, 70 * mm, 70 * mm]),
        H3("Dotazione iniziale di un nuovo Lord"),
        tbl(["Risorsa", "Quantità"], rows, widths=[50 * mm, 30 * mm]),
        WHY("le risorse iniziali bastano per i primi potenziamenti e le prime reclute; il resto va guadagnato producendo e combattendo. "
            f"Il Magazzino limita la scorta di ogni risorsa (livello 1: {n(C['buildings'][4]['levels'][0]['capacity_each_resource'])}, livello 20: {n(C['buildings'][4]['levels'][-1]['capacity_each_resource'])}). "
            "<b>Regola v1.3</b>: il Magazzino di livello L contiene sempre almeno il 110% del costo singolo più alto raggiungibile al Castello L (castello, edifici, ricerche): ogni potenziamento è pagabile con un magazzino pieno, senza eccezioni."),
        H3("Il tuo dominio aumenta la produzione"),
        P(f"Ogni {C['battle']['domain_tile_every_stages']} stage superati conquisti una casella adiacente della tua mappa {C['personal_domain']['map']}. "
          f"Ogni {10} caselle possedute danno <b>+{C['personal_domain']['production_bonus_per_10_owned_tiles_pct']}%</b> di produzione, fino a un massimo di "
          f"<b>+{C['personal_domain']['production_bonus_cap_pct']}%</b> (100 caselle allo stage {C['personal_domain']['full_domain_at_stage']})."),
    ]


def sec_hero():
    h = C["hero"]
    bs, g = h["base_stats"], h["stat_growth_per_level"]
    rows = []
    cum = 0
    for lv in range(1, h["max_level"] + 1):
        st = F.hero_base_stats(lv)
        xp = F.xp_to_next(lv) if lv < h["max_level"] else 0
        rows.append([lv, n(xp) if xp else "—", n(cum), st["attack"], st["defense"], n(st["hp"]), n(round(st["attack"] * 2 + st["defense"] * 1.5 + st["hp"] * 0.15)),
                     F.talent_points_for_level(lv)])
        cum += xp
    skills = [[SKILL_IT.get(s["key"], s["key"]), s["unlock_level"], f"{s['cooldown_seconds']} s", _skill_effect(s)] for s in h["auto_skills"]]
    return [
        H1("3. L'Eroe (il Lord)"),
        P(f"Il Lord è sempre in campo. Parte con <b>{bs['attack']} attacco</b>, <b>{bs['defense']} difesa</b>, <b>{bs['hp']} PV</b> e colpisce ogni {bs['attack_interval_seconds']} s. "
          f"Ogni livello aggiunge <b>+{g['attack']} attacco, +{g['defense']} difesa, +{g['hp']} PV</b>. Livello massimo: <b>{h['max_level']}</b>."),
        H2("3.1 Potenza dell'eroe"),
        P("<b>Potenza eroe = round(attacco × 2 + difesa × 1,5 + PV × 0,15)</b>, calcolata sulle statistiche finali: base + livello + statistiche primarie "
          "dell'equipaggiamento (moltiplicate dalla Forgia), poi le percentuali di talenti e affissi."),
        WHY("l'attacco pesa più di tutto perché accorcia gli scontri; la difesa e i PV contano ma non permettono di 'tankare' all'infinito. La formula è unica e pubblica: puoi prevedere la tua potenza."),
        H2("3.2 Esperienza: costo di ogni livello"),
        P(f"<b>XP per passare al livello successivo = round(80 × livello^1,55 + 40 × livello)</b>. Il livello si paga <b>solo in XP</b> ({h['level_up_cost']}); "
          "l'XP arriva dalle battaglie (75% distribuito sulle uccisioni, 25% bonus di fine stage), dai dungeon Monster Hunt e dal farm offline."),
        P(f"Totale XP dal livello 1 al 100: <b>{n(C['balance_audit']['hero_xp_total_1_to_100'])}</b>. Superando tutti i 200 stage una sola volta si arriva circa al livello "
          f"{C['balance_audit']['approx_hero_level_after_all_200_first_clears_without_repeat_xp']} senza contare il farm ripetuto."),
        tbl(["Lv", "XP per il prossimo", "XP cumulati", "ATT", "DIF", "PV", "Potenza base", "Punti talento"], rows,
            widths=[10 * mm, 28 * mm, 28 * mm, 14 * mm, 14 * mm, 18 * mm, 24 * mm, 22 * mm]),
        H2("3.3 Talenti"),
        P(f"Ottieni <b>1 punto talento ogni 5 livelli</b> (massimo 20 al livello 100). Quattro rami, ognuno con {h['talents']['branches']['warrior']['max_ranks']} ranghi. "
          f"Il reset costa <b>{h['talents']['respec_rubies']} Rubini</b>."),
        tbl(["Ramo", "Effetto per rango", "Ranghi max", "Effetto al massimo"],
            [[TALENT_IT[k][0], TALENT_IT[k][1], v["max_ranks"], v["effect_per_rank"].split("+")[-1].replace(".", ",") + "% × " + str(v["max_ranks"])]
             for k, v in h["talents"]["branches"].items()], widths=[30 * mm, 70 * mm, 22 * mm, 40 * mm]),
        WHY("Guerriero e Guardiano rendono il Lord più forte da solo (inizio partita); Comandante conviene appena l'esercito pesa più dell'eroe; Fortuna accelera oro e drop per chi farma molto."),
        H2("3.4 Abilità automatiche"),
        P(f"Le abilità si attivano da sole in battaglia. Hai <b>{h['active_skill_slots']} slot</b>, sbloccati ai livelli {', '.join(map(str, h['skill_slot_unlock_levels']))}. "
          "Le abilità si imparano salendo di livello e le equipaggi negli slot nella scheda Eroe."),
        tbl(["Abilità", "Livello", "Ricarica", "Effetto"], skills, widths=[34 * mm, 16 * mm, 18 * mm, 110 * mm]),
        WHY("l'esito della battaglia è deciso dalla potenza; le abilità cambiano il ritmo e la scena (burst, area, buff), non il verdetto: così il combattimento resta prevedibile ma spettacolare."),
    ]


def _skill_effect(s):
    v = s["canonical_effect_values"]
    parts = []
    if "hero_attack_multiplier" in v:
        parts.append(f"colpo singolo ×{n(v['hero_attack_multiplier'])} attacco")
    if "boss_only_bonus_pct" in v:
        parts.append(f"+{v['boss_only_bonus_pct']}% contro i boss")
    if "hero_attack_multiplier_per_enemy" in v:
        parts.append(f"area: ×{n(v['hero_attack_multiplier_per_enemy'])} attacco su fino a {v['max_targets']} nemici")
    if "hero_attack_pct" in v:
        parts.append(f"+{v['hero_attack_pct']}% attacco eroe")
    if "army_power_pct" in v:
        parts.append(f"+{v['army_power_pct']}% potenza esercito")
    if "mythic_unit_power_pct" in v:
        parts.append(f"+{v['mythic_unit_power_pct']}% unità mitiche")
    if "hero_defense_pct" in v:
        parts.append(f"+{v['hero_defense_pct']}% difesa")
    if "incoming_damage_reduction_pct" in v:
        parts.append(f"-{v['incoming_damage_reduction_pct']}% danni subiti")
    if v.get("duration_seconds"):
        parts.append(f"per {v['duration_seconds']} s")
    return "; ".join(parts)


def sec_campaign():
    b = C["battle"]
    reg_rows = []
    for r in b["regions"]:
        fams = ", ".join(f"{f} ({CLASS_IT[F.enemy_class(f)]})" for f in r["enemy_families"])
        reg_rows.append([r["region"], r["name"], f"{r['stage_start']}–{r['stage_end']}", fams, f"{r['region_boss']} ({CLASS_IT[F.enemy_class(r['region_boss'])]})"])
    stage_rows = []
    for s in range(1, b["campaign_stages"] + 1):
        k = F.stage_kind(s)
        fc = F.first_clear_rewards(s)
        kind = {"normal": "Normale", "elite": "Elite", "boss": "BOSS"}[k]
        reg = F.region_info(s)
        stage_rows.append([s, kind, reg["name"], n(F.enemy_required_power(s)), n(fc["xp"]), n(fc["gold"]), n(fc["soft"]),
                           F.monsters_per_wave(s) if k != "boss" else f"boss + {F.boss_minions(s)}", F.item_level_for_stage(s)])
    gd = b["gear_drop"]
    return [
        H1("4. Campagna"),
        P(f"<b>{b['campaign_stages']} stage</b> in 10 regioni, ciascuno con <b>{b['waves_per_stage']} ondate</b> e un limite di <b>{b['stage_time_limit_seconds']} secondi</b>. "
          f"Ogni <b>{b['elite_every_stages']}</b> stage c'è un'<b>Elite</b> (potenza ×{n(b['elite_power_multiplier'])}), ogni <b>{b['boss_every_stages']}</b> un <b>Boss</b> "
          f"(potenza ×{n(b['boss_power_multiplier'])}; l'ultima ondata è il boss regionale con min(10, ⌊stage/20⌋) servitori)."),
        H2("4.1 Come si vince"),
        *LI([
            "<b>Potenza totale = potenza eroe + potenza esercito</b>.",
            "<b>Potenza nemica = round(75 × 1,043^(stage−1) × rampa)</b>, dove la rampa vale <b>1 + 0,0015 × max(0, stage−50)</b> (+7,5% allo stage 100, +15% al 150, +22,5% al 200). Curva v1.4: ogni boss (50/100/150/180/200) è battibile con potenza e unità ottenibili prima di affrontarlo.",
            "Potenza richiesta = potenza nemica × 1,35 (Elite) o × 1,85 (Boss).",
            "<b>Vinci se potenza totale ≥ potenza richiesta.</b> Nessun dado.",
            "Durata della vittoria = clamp(round(18 + 55 × richiesta/totale), 18, 90) secondi: più sei forte, più in fretta finisce.",
            f"Se perdi, tieni il <b>20%</b> di XP e Oro già 'guadagnati sulle uccisioni' ma niente bonus di fine stage, casella di dominio o cassa boss.",
        ]),
        WHY("la crescita del 4,7% a stage crea un muro morbido: quando ti blocchi devi potenziare Regno, esercito, Forgia o ricerca. La rampa dal 50 in poi evita che il late-game diventi troppo facile con eserciti mitici."),
        H2("4.2 Ricompense"),
        *LI([
            "<b>Prima vittoria</b>: XP = round(25 × stage^1,35) · Oro = round(18 × stage^1,22) · Risorse = round(12 × stage^1,18) divise in "
            + ", ".join(f"{RES[k]} {int(v*100)}%" for k, v in b["soft_resource_split"].items()) + ".",
            f"<b>Farm ripetuto</b> (stage più alto superato, ogni {b['repeat_farm_cycle_seconds']} s anche offline): {int(b['repeat_xp_fraction']*100)}% dell'XP, "
            f"{int(b['repeat_gold_fraction']*100)}% dell'Oro e {int(b['repeat_soft_resource_fraction']*100)}% delle risorse della prima vittoria.",
            f"<b>Casella di dominio</b> ogni {b['domain_tile_every_stages']} stage superati.",
            f"<b>Equipaggiamento</b>: probabilità di drop a fine stage {gd['normal_stage_clear_roll_pct']}% (normale), {gd['elite_stage_clear_roll_pct']}% (elite); il boss garantisce "
            f"{gd['boss_guaranteed_items']} oggetto + {gd['boss_extra_item_roll_pct']}% di un secondo. In farm ripetuto il drop è dimezzato (×{gd['repeat_drop_rate_multiplier']}).",
            "Boss traguardo con rarità minima garantita: " + ", ".join(f"stage {k} → {RARITY_IT[v]}" for k, v in sorted(gd["milestone_boss_minimum_rarity"].items(), key=lambda kv: int(kv[0]))) + ".",
            f"Totali di tutta la campagna (prime vittorie): {n(C['balance_audit']['campaign_first_clear_xp_total'])} XP, {n(C['balance_audit']['campaign_first_clear_gold_total'])} Oro, "
            f"{n(C['balance_audit']['campaign_first_clear_soft_bundle_total'])} risorse.",
        ]),
        H2("4.3 Le 10 regioni e i loro nemici"),
        P("Ogni regione ha 4 famiglie di mostri e un boss. Tra parentesi la <b>classe</b> del nemico: è ciò che conta per i contro-attacchi delle tue unità (capitolo 5)."),
        tbl(["#", "Regione", "Stage", "Famiglie di mostri (classe)", "Boss regionale (classe)"], reg_rows, widths=[8 * mm, 28 * mm, 16 * mm, 84 * mm, 42 * mm]),
        H2("4.4 Tabella completa degli stage"),
        P("Potenza richiesta e ricompense di prima vittoria per ogni stage. 'Mostri' = nemici per ondata normale; nell'ondata boss compaiono il boss e i suoi servitori. "
          "'Lv ogg.' = livello oggetto degli equipaggiamenti trovati in quello stage (= stage/2 arrotondato per eccesso, max 100)."),
        tbl(["Stage", "Tipo", "Regione", "Potenza richiesta", "XP", "Oro", "Risorse", "Mostri", "Lv ogg."], stage_rows,
            widths=[12 * mm, 15 * mm, 30 * mm, 28 * mm, 20 * mm, 20 * mm, 20 * mm, 20 * mm, 13 * mm]),
    ]


def sec_units():
    u = C["units"]
    cc = u["counters"]
    cat = u["catalog"]
    stat_rows, cost_rows, counter_rows = [], [], []
    for x in cat:
        stat_rows.append([x["name"], CAT_IT[x["category"]], ROLE_IT.get(x["role"], x["role"]), CLASS_IT[cc["unit_class"][x["key"]]], x["attack"], x["defense"], x["hp"],
                          x["base_power"], x["command_cost"], round(x["base_power"] / x["command_cost"], 1)])
        rc = x["recruit_cost"]
        req = x["required_research"]
        req_name = next((r["name"] for r in C["research"]["nodes"] if r["key"] == req), "—") if req else "—"
        cost_rows.append([x["name"], n(rc["grain"]), n(rc["wood"]), n(rc["clay"]), n(rc["iron"]), n(rc["gold"]), t(x["recruit_time_minutes_each"]),
                          f"Castello {x['unlock_castle_level']}", f"Stage {x['unlock_campaign_stage']}", req_name])
        row = cc["table"][x["key"]]
        counter_rows.append([x["name"], ", ".join(CLASS_IT[c] for c in row["strong_vs"]), ", ".join(CLASS_IT[c] for c in row["weak_vs"])])
    # enemies grouped by class
    by_class = defaultdict(list)
    for fam, cls in C["battle"]["enemy_classes"].items():
        by_class[cls].append(fam)
    class_rows = [[CLASS_IT[c], ", ".join(sorted(v))] for c, v in sorted(by_class.items())]
    # per-region recommendation
    rec_rows = []
    for r in C["battle"]["regions"]:
        mix = F.stage_enemy_mix(r["stage_start"])
        boss_mix = F.stage_enemy_mix(r["stage_end"])
        scored = sorted(((F.unit_counter_pct(x["key"], mix), x["name"]) for x in cat), reverse=True)
        bscored = sorted(((F.unit_counter_pct(x["key"], boss_mix), x["name"]) for x in cat), reverse=True)
        best = ", ".join(f"{nm} ({'+' if p >= 0 else ''}{n(round(p, 1))}%)" for p, nm in scored[:4])
        worst = ", ".join(f"{nm} ({n(round(p, 1))}%)" for p, nm in scored[-3:])
        bbest = ", ".join(f"{nm} ({'+' if p >= 0 else ''}{n(round(p, 1))}%)" for p, nm in bscored[:3])
        rec_rows.append([r["name"], best, worst, bbest])
    slots = C["kingdom"]["support_formation_slots_by_castle_level"]
    tiers = C["army_visual_progression"]["tiers"]
    return [
        H1("5. Unità ed esercito"),
        P(f"L'esercito si sblocca allo <b>stage {u['campaign_army_unlock_stage']}</b>. Ci sono <b>{u['unit_count']} unità</b> in 4 categorie: Regolari, Assedio, Bestie e Mitiche. "
          "Le recluti nel Regno (Caserma, Scuderia, Officina, Bestiario, Santuario Mitico), le possiedi per sempre e ne schieri una parte in <b>formazione</b>."),
        H2("5.1 Come l'esercito conta in battaglia"),
        *LI([
            "<b>Potenza esercito = Σ (quantità schierata × potenza base dell'unità × moltiplicatori)</b>. I moltiplicatori sommano ricerche applicabili, talento Comandante (+1,5%/rango), affissi 'Potenza esercito' e bonus territoriali dell'alleanza.",
            "<b>Capacità di comando = 50 + livello eroe × 10 + livello castello² × 20</b>. Ogni unità occupa 'comando': non puoi schierare oltre la capacità.",
            "<b>Slot di formazione</b>: il Lord è sempre presente; il numero di <i>tipi</i> di unità schierabili dipende dal Castello: "
            + ", ".join(f"Castello {s['castle_level']} → {s['slots']} slot" for s in slots) + ".",
            "<b>Contro-unità (v1.2)</b>: ogni unità è <b>forte (+30%)</b> o <b>debole (−20%)</b> contro alcune delle 7 classi di nemici. Il bonus si applica in proporzione alla quota di quella classe nello stage "
            "(famiglie della regione in parti uguali; negli stage boss il 50% è la classe del boss).",
            "Le unità sono schierate come icone/squadre: il server tiene le quantità reali, la scena mostra truppe rappresentative.",
        ]),
        WHY("la capacità di comando lega l'esercito alla crescita di eroe e castello, così non si può 'comprare' un esercito enorme al livello 1. I contro-attacchi premiano chi cambia formazione per regione invece di usare sempre le unità più costose."),
        H2("5.2 Catalogo delle unità: statistiche"),
        P("'Potenza/comando' indica quanto rende ogni punto di comando. <b>Regola v1.4</b>: potenza/comando = 36 + 1,4 × Castello di sblocco (+14 mitiche, +6 assedio, +3 bestie): "
          "le unità d'élite valgono il loro comando (un Drago 1.740 vs 925 di 25 Fanti), le unità iniziali restano le più economiche per punto di potenza."),
        tbl(["Unità", "Categoria", "Ruolo", "Classe", "ATT", "DIF", "PV", "Potenza", "Comando", "Potenza/comando"], stat_rows,
            widths=[30 * mm, 18 * mm, 22 * mm, 18 * mm, 11 * mm, 11 * mm, 11 * mm, 15 * mm, 16 * mm, 24 * mm]),
        H2("5.3 Catalogo delle unità: costi, tempi e sblocchi"),
        P("Costi e tempo per <b>una</b> unità; il reclutamento di N unità costa N volte e dura N volte (le bestie sono più veloci con la ricerca Addomesticamento). "
          f"Code di reclutamento: {C['kingdom']['recruit_queues']['start']} (2 dal Castello {C['kingdom']['recruit_queues']['second_unlock_castle_level']}). "
          "Per reclutare servono <b>tutti</b> i requisiti: Castello, stage di campagna e ricerca (livello 1 basta)."),
        tbl(["Unità", "Grano", "Legno", "Argilla", "Ferro", "Oro", "Tempo", "Castello", "Campagna", "Ricerca richiesta"], cost_rows,
            widths=[28 * mm, 13 * mm, 13 * mm, 13 * mm, 13 * mm, 12 * mm, 14 * mm, 18 * mm, 17 * mm, 37 * mm]),
        H2("5.4 Contro chi è forte e debole ogni unità"),
        P(f"Bonus <b>+{cc['bonus_pct']}%</b> contro le classi 'forte', malus <b>−{cc['malus_pct']}%</b> contro le classi 'debole', neutrale altrimenti. Esempio: Fanteria (forte contro Bestie e Giganti) in uno stage con 2 famiglie di bestie su 4 "
          f"guadagna +{cc['bonus_pct']}% × 0,5 = +{cc['bonus_pct']//2}%."),
        tbl(["Unità", f"FORTE contro (+{cc['bonus_pct']}%)", f"DEBOLE contro (−{cc['malus_pct']}%)"], counter_rows, widths=[34 * mm, 72 * mm, 72 * mm]),
        H3("Le 7 classi di nemici e chi ne fa parte"),
        tbl(["Classe", "Famiglie di mostri e boss"], class_rows, widths=[28 * mm, 150 * mm]),
        H2("5.5 Quali unità portare in ogni regione"),
        P("Calcolato con la regola v1.2 sulle famiglie della regione (stage normali) e sull'ondata boss (50% classe del boss). Il pulsante <b>Suggerisci</b> nella schermata Formazione applica lo stesso calcolo alle unità che possiedi."),
        tbl(["Regione", "Migliori unità (stage normali)", "Da evitare", "Migliori contro il boss"], rec_rows, widths=[26 * mm, 62 * mm, 44 * mm, 46 * mm]),
        WHY("cambiare formazione tra una regione e l'altra vale fino a un +30% gratis: spesso è più economico di un intero livello di castello."),
        H2("5.6 Come cresce visivamente l'esercito"),
        tbl(["Tier", "Quando", "Aspetto", "Truppe in primo piano", "Coorti di sfondo"],
            [[x["tier"], x["trigger"].replace("stage", "stage").replace(" and army deployed", " e esercito schierato").replace(">=", "≥").replace("<", "<"), x["look"], x["foreground_proxy_cap"], x["background_cohorts"]] for x in tiers],
            widths=[10 * mm, 34 * mm, 84 * mm, 26 * mm, 24 * mm]),
    ]


def sec_kingdom():
    k = C["kingdom"]
    out = [
        H1("6. Regno: Castello ed edifici"),
        P(f"Il <b>Castello</b> (max livello {k['castle_max_level']}) sblocca edifici, ricerche, unità, slot di formazione e alleanze. "
          f"Code di costruzione: {k['construction_queues']['start']} (2 dal Castello {k['construction_queues']['second_unlock_castle_level']}); coda di ricerca: {k['research_queues']}."),
        P("Le ricerche <i>Carpenteria</i>/<i>Gilda dei Costruttori</i> riducono i tempi, <i>Architettura in Pietra</i>/<i>Pianificazione Reale</i> riducono i costi, "
          "<i>Opere Imperiali</i> accelera solo il Castello. Puoi completare subito un timer con Rubini: <b>max(5, ⌈minuti rimanenti / 3⌉)</b>."),
        WHY("i tempi crescono con il livello perché il gioco è pensato per sessioni brevi: avvii i lavori, combatti, torni. Il Castello è il collo di bottiglia voluto: dà il ritmo a tutta la progressione."),
        H2("6.1 Aspetto del Regno"),
        tbl(["Tier", "Castello", "Nome", "Cosa vedi"], [[v["tier"], v["castle_levels"], v["name"], v["visual"]] for v in k["visual_tiers"]], widths=[10 * mm, 18 * mm, 40 * mm, 110 * mm]),
        H2("6.2 Cosa sblocca ogni livello di Castello"),
    ]
    unlock = defaultdict(list)
    for bd in C["buildings"]:
        if bd["key"] != "castle":
            unlock[bd["unlock_castle_level"]].append(f"Edificio: {bd['name']}")
    for r in C["research"]["nodes"]:
        unlock[r["unlock_castle_level"]].append(f"Ricerca: {r['name']}")
    for x in C["units"]["catalog"]:
        unlock[x["unlock_castle_level"]].append(f"Unità: {x['name']}")
    for s in k["support_formation_slots_by_castle_level"]:
        unlock[s["castle_level"]].append(f"{s['slots']} slot di formazione")
    unlock[C["alliances"]["unlock_castle_level"]].append("Alleanze")
    unlock[k["construction_queues"]["second_unlock_castle_level"]].append("2ª coda di costruzione")
    unlock[k["recruit_queues"]["second_unlock_castle_level"]].append("2ª coda di reclutamento")
    out.append(tbl(["Castello", "Sblocchi"], [[lv, " · ".join(unlock[lv])] for lv in sorted(unlock)], widths=[18 * mm, 160 * mm]))
    out.append(H2("6.3 Costi e tempi di ogni edificio (livello per livello)"))
    out.append(P("Costo per passare <b>al</b> livello indicato. 'Produzione' è per ora al livello raggiunto (prima dei bonus di dominio, ricerca e alleanza); 'Capacità' è il tetto per ogni risorsa."))
    for bd in C["buildings"]:
        rows = []
        for L in bd["levels"]:
            c = L["upgrade_cost"]
            extra = ""
            if "production_per_hour" in L:
                extra = " · ".join(f"{n(v)} {RES[k2]}/h" for k2, v in L["production_per_hour"].items())
            elif "capacity_each_resource" in L:
                extra = f"{n(L['capacity_each_resource'])} per risorsa"
            rows.append([L["level"], n(c["grain"]), n(c["wood"]), n(c["clay"]), n(c["iron"]), n(c["gold"]), t(L["upgrade_time_minutes"]), extra])
        purpose = _building_purpose(bd["key"])
        out.append(KeepTogether([H3(f"{bd['name']} — richiede Castello {bd['unlock_castle_level']}"), P(purpose, "small"),
                                 tbl(["Lv", "Grano", "Legno", "Argilla", "Ferro", "Oro", "Tempo", "Produzione / capacità"], rows,
                                     widths=[9 * mm, 20 * mm, 20 * mm, 20 * mm, 20 * mm, 18 * mm, 18 * mm, 53 * mm])]))
    return out


def _building_purpose(key):
    return {
        "castle": "Cuore del Regno: ogni livello sblocca edifici, ricerche, unità e slot; alza la capacità di comando (livello² × 20).",
        "farm": "Produce Grano, la risorsa più richiesta dal reclutamento (soprattutto bestie).",
        "lumberyard": "Produce Legno per edifici, ricerche e macchine d'assedio.",
        "clay_pit": "Produce Argilla per edifici e ricerche.",
        "warehouse": "Alza il tetto di ogni risorsa: senza magazzino la produzione oltre il limite va persa.",
        "barracks": "Addestra le unità regolari (Fanteria, Arcieri); richiesta per l'esercito.",
        "iron_mine": "Produce Ferro, base di armi e armature.",
        "university": "Sede della ricerca (8 rami, 48 nodi).",
        "gold_mine": "Produce Oro: Forgia, riforgiatura, alleanza e inventario ne consumano molto.",
        "walls": "Difesa del regno: base per la ricerca Fortificazione e la difesa in guerra.",
        "stable": "Addestra la Cavalleria.",
        "workshop": "Costruisce Catapulte e Arieti d'Assedio.",
        "alliance_hall": "Abilita alleanze, donazioni e guerre (Castello 8).",
        "bestiary": "Addestra le bestie da guerra (lupi, falchi, orsi, leoni, elefanti).",
        "temple": "Edificio di prestigio; prerequisito della via mitica.",
        "mythic_sanctuary": "Evoca le unità mitiche: Drago, Angelo, Demone.",
    }[key]


def sec_research():
    r = C["research"]
    out = [
        H1("7. Ricerca"),
        P(f"L'Università ospita <b>{r['node_count']} ricerche</b> in <b>{len(r['branches'])} rami</b>, ognuna con <b>{r['max_level_each']} livelli</b>. L'effetto è permanente e si somma "
          f"(es. 2% × 5 livelli = 10%). Una sola ricerca alla volta; sblocco per livello di Castello. Alcune unità richiedono una ricerca al livello 1."),
        WHY("la ricerca converte risorse in bonus percentuali che moltiplicano tutto ciò che hai: un +10% alla Fanteria vale di più quanto più Fanteria schieri, quindi conviene specializzarsi nelle unità che usi davvero."),
    ]
    for br in r["branches"]:
        rows = []
        for node in [x for x in r["nodes"] if x["branch"] == br]:
            for L in node["levels"]:
                c = L["cost"]
                rows.append([node["name"] if L["level"] == 1 else "", L["level"], f"{EFFECT_IT.get(node['effect_key'], node['effect_key'])} +{n(L['effect_total_pct'])}%",
                             n(c["grain"]), n(c["wood"]), n(c["clay"]), n(c["iron"]), n(c["gold"]), t(L["time_minutes"]), f"Castello {node['unlock_castle_level']}" if L["level"] == 1 else ""])
        out.append(KeepTogether([H2(f"7.{r['branches'].index(br)+1} Ramo {BRANCH_IT[br]}"),
                                 tbl(["Ricerca", "Lv", "Effetto totale", "Grano", "Legno", "Argilla", "Ferro", "Oro", "Tempo", "Sblocco"], rows,
                                     widths=[30 * mm, 8 * mm, 46 * mm, 15 * mm, 15 * mm, 15 * mm, 15 * mm, 13 * mm, 13 * mm, 16 * mm])]))
    return out


def sec_gear():
    g = C["gear"]
    rar_rows = [[RARITY_IT[k], n(g["rarity_rules"][k]["stat_multiplier"]), g["rarity_rules"][k]["affix_count"], n(g["affix_values"]["rarity_affix_multiplier"][k]),
                 g["rarity_unlock_stage"][k], g["reforge"]["reforge_stone_cost_by_rarity"][k], f"{g['salvage']['rarity_base'][k]} + {g['salvage']['rarity_level_factor'][k]}×⌊lv/10⌋"]
                for k in g["rarity_order"]]
    slot_rows = [[SLOT_IT[s], ", ".join(f"{k} {v}" for k, v in g["slot_base_coefficients"][s].items()).replace("attack", "ATT").replace("defense", "DIF").replace("hp", "PV"),
                  ", ".join(f"{k.replace('attack','ATT').replace('defense','DIF').replace('hp','PV')} {n(v)}" for k, v in F.item_base_stats(s, 50, "epic").items()),
                  "sì" if s in ("weapon", "helmet", "chest", "boots", "cloak") else "no"] for s in g["slots"]]
    af = g["affix_values"]
    affix_rows = [[AFFIX_IT[k], n(af["base_at_item100"][k]), n(af["caps"].get(k, 0)) if k in af["caps"] else "—"] for k in g["affix_pool"]]
    drop_rows = [[d["stages"]] + [f"{d['weights_pct'][r]}%" for r in g["rarity_order"]] for d in g["stage_drop_weights"]]
    forge_rows = []
    for f_lv in range(0, g["forge"]["max_level_per_slot"]):
        c10, c50, c100 = F.forge_next_cost(10, f_lv), F.forge_next_cost(50, f_lv), F.forge_next_cost(100, f_lv)
        forge_rows.append([f"{f_lv} → {f_lv+1}", f"×{n(F.forge_multiplier(f_lv+1))}", n(c10["gold"]), c10["forge_dust"], n(c50["gold"]), c50["forge_dust"], n(c100["gold"]), c100["forge_dust"]])
    samples = g["forge"]["samples"]
    inv = g["inventory"]
    return [
        H1("8. Equipaggiamento e Forgia"),
        P(f"Nove slot: {', '.join(SLOT_IT[s] for s in g['slots'])}. Sette rarità. Ogni oggetto ha un <b>livello oggetto</b> = ⌈stage di provenienza / 2⌉ (max 100), statistiche primarie, "
          "da 0 a 4 <b>affissi</b> secondari e beneficia della <b>Forgia</b> dello slot. L'equipaggiamento migliore viene indossato automaticamente."),
        H2("8.1 Statistiche primarie"),
        P("<b>Statistica = round(coefficiente slot × (1 + livello oggetto × 0,12) × moltiplicatore rarità)</b>, poi × moltiplicatore Forgia dello slot."),
        tbl(["Slot", "Coefficienti", "Esempio: Epico lv 50", "Cambia l'aspetto del Lord"], slot_rows, widths=[32 * mm, 44 * mm, 52 * mm, 40 * mm]),
        WHY("armi e anelli spingono l'attacco (pesa ×2 nella potenza), corazze ed elmi difesa e PV. I gioielli non si vedono ma contano quanto gli altri pezzi."),
        H2("8.2 Rarità"),
        tbl(["Rarità", "Molt. statistiche", "Affissi", "Molt. affissi", "Dallo stage", "Pietre per riforgiare", "Polvere allo smantellamento"], rar_rows,
            widths=[24 * mm, 24 * mm, 14 * mm, 20 * mm, 18 * mm, 28 * mm, 46 * mm]),
        H3("Probabilità di rarità per fascia di stage"),
        tbl(["Stage"] + [RARITY_IT[r] for r in g["rarity_order"]], drop_rows, widths=[20 * mm] + [21 * mm] * 7),
        WHY("le rarità alte compaiono solo dove la campagna è dura: così un Mitico è sempre un traguardo di gioco, mai un acquisto."),
        H2("8.3 Affissi"),
        P("<b>Valore = round(base@100 × (0,35 + 0,65 × livello oggetto / 100) × molt. rarità × tiro casuale [0,85–1,15], 2)</b>. Ogni affisso compare al massimo una volta per oggetto; "
          "i tetti valgono sulla somma di tutti i pezzi indossati."),
        tbl(["Affisso", "Base a livello 100", "Tetto complessivo"], affix_rows, widths=[60 * mm, 40 * mm, 40 * mm]),
        H2("8.4 Forgia (permanente per slot)"),
        P(f"Ogni slot ha un livello di Forgia da 0 a <b>{g['forge']['max_level_per_slot']}</b>, che <b>non si perde</b> cambiando oggetto. Nessuna probabilità di fallimento. "
          "<b>Moltiplicatore = 1 + 0,04 × F + 0,002 × F²</b> (livello 20: ×2,6). Costo del prossimo livello: <b>Oro = round((25 + lv ogg. × 8) × 1,35^F)</b>, "
          "<b>Polvere = ⌈(2 + lv ogg. × 0,08) × 1,22^F⌉</b>, dove lv ogg. è il livello dell'oggetto indossato in quello slot."),
        tbl(["Forgia", "Molt.", "Oro (ogg. lv 10)", "Polvere", "Oro (ogg. lv 50)", "Polvere", "Oro (ogg. lv 100)", "Polvere"], forge_rows,
            widths=[18 * mm, 16 * mm, 26 * mm, 16 * mm, 26 * mm, 16 * mm, 28 * mm, 16 * mm]),
        P("Totale da 0 a 20: " + " · ".join(f"oggetto lv {k}: {n(v['gold_0_to_20'])} Oro e {n(v['forge_dust_0_to_20'])} Polvere" for k, v in sorted(samples.items(), key=lambda kv: int(kv[0]))) + ".", "small"),
        WHY("la Forgia è l'investimento sicuro del gioco: resta anche quando trovi un pezzo migliore, quindi conviene forgiare con oggetti di livello basso (costano meno) e poi indossare il meglio."),
        H2("8.5 Riforgiatura e smantellamento"),
        *LI([
            "<b>Riforgiatura</b>: ritira <b>un</b> affisso a scelta. Costo <b>Oro = round(50 × lv oggetto × molt. rarità)</b> + Pietre di Riforgiatura secondo la rarità (tabella 8.2). Statistiche e rarità non peggiorano mai.",
            f"<b>Smantellamento</b>: Polvere = base rarità + ⌊lv/10⌋ × fattore rarità; i Leggendari o superiori danno una Pietra extra nel {g['salvage']['legendary_or_higher_extra_reforge_stone_chance_pct']}% dei casi, "
            f"Mitici e Antichi un'Essenza Mitica nell'{g['salvage']['mythic_or_ancient_mythic_essence_chance_pct']}%.",
            f"<b>Smantellamento automatico</b> dallo stage {inv['auto_salvage_unlock_stage']} con filtri per rarità, slot e 'sotto il livello indossato'.",
            f"<b>Inventario</b>: {inv['base_slots']} posti, espandibile fino a {inv['hard_cap_slots']}: " + ", ".join(f"→{e['to_slots']} per {n(list(e['cost'].values())[0])} {RES[list(e['cost'].keys())[0]]}" for e in inv["expansions"]) + ".",
        ]),
    ]


def sec_domain_offline():
    pd, o = C["personal_domain"], C["offline"]
    return [
        H1("9. Dominio personale e progresso offline"),
        H2("9.1 Dominio"),
        P(f"Mappa {pd['map']} tutta tua ({pd['tiles_total']} caselle, parti con {pd['start_owned_tiles']}). <b>{pd['conquest_rule'].replace('one new canonical adjacent tile every 2 cleared campaign stages', 'Una nuova casella adiacente ogni 2 stage di campagna superati')}</b>; "
          f"dominio completo allo stage {pd['full_domain_at_stage']}. Bonus produzione <b>+{pd['production_bonus_per_10_owned_tiles_pct']}% ogni 10 caselle</b>, massimo +{pd['production_bonus_cap_pct']}%. "
          f"Tipi di terreno: {', '.join(pd['tile_visuals'])}. Strade, fattorie, torri e città compaiono man mano che cresci, nel tuo colore araldico."),
        WHY("il dominio rende visibile il progresso della campagna e premia chi avanza con più produzione, senza toccare la potenza in battaglia."),
        H2("9.2 Offline"),
        *LI([
            f"Massimo <b>{o['max_hours']} ore</b> accumulabili; il calcolo usa il tempo del server.",
            f"Risorse degli edifici al <b>{int(o['resource_efficiency']*100)}%</b>; farm dello stage più alto (XP/Oro/risorse in modalità ripetuta) al <b>{int(o['battle_loot_efficiency']*100)}%</b>; "
            f"tiri equipaggiamento al {int(o['gear_roll_efficiency']*100)}%, con <b>min(1,2; 0,35 + stage/250)</b> tiri l'ora.",
            "Costruzioni, ricerche e reclutamenti proseguono al 100% e si completano mentre sei via.",
            "Il riepilogo offline mostra uccisioni, XP, Oro, risorse, oggetti trovati/smantellati, materiali e timer completati; si riscatta una sola volta (idempotente).",
        ]),
    ]


def sec_dungeons_events_quests():
    d, e, q = C["dungeons"], C["events"], C["quests"]
    ab = e["alliance_boss"]
    dun_rows = [[x["name"], x["reward"], x["formula"]] for x in d["catalog"]]
    dep_rows = [[f"{dp['duration_minutes']} min", dp["energy"], f"×{n(dp['reward_multiplier'])}"] + list(_dep_example(dp["reward_multiplier"])) for dp in e["deployments"]]
    return [
        H1("10. Dungeon, Eventi e Missioni"),
        H2("10.1 Dungeon"),
        P(f"Dallo stage {d['unlock_stage']}. <b>{d['free_entries_per_dungeon_per_day']} ingressi gratuiti</b> al giorno per dungeon (reset 00:00 UTC), fino a {d['paid_extra_entry_cap_per_dungeon_per_day']} extra a "
          f"{d['paid_extra_entry_rubies']} Rubini. Ogni corsa dura <b>{d['run_duration_minutes']} minuti</b> (accelerabile). {d['tiers']} tier, sbloccati agli stage {', '.join(map(str, d['tier_unlock_stages']))}."),
        tbl(["Dungeon", "Ricompensa", "Formula (tier = livello del dungeon)"], dun_rows, widths=[30 * mm, 50 * mm, 98 * mm]),
        WHY("i dungeon sono la fonte programmata di materiali per la Forgia e di XP extra: due al giorno gratis tengono il ritmo anche a chi non spende."),
        H2("10.2 Eventi settimanali"),
        P(f"C'è sempre un evento attivo (archetipi: {', '.join(e['archetypes'])}), cicli di {e['cycle_days']} giorni. Spendi <b>Energia</b> (max {e['energy']['max']}, 1 punto ogni {e['energy']['regen_minutes_per_point']} min) "
          f"per <b>spedizioni</b> più o meno lunghe. Ricompense base: Gettoni = round((20 + stage × 0,35) × molt.), Oro = round((150 + stage × 8) × molt.), risorse = 0,25 h di produzione × molt., "
          "probabilità oggetto = min(35%, 5% + stage × 0,10)."),
        tbl(["Durata", "Energia", "Moltiplicatore", "Gettoni (stage 50)", "Oro (stage 50)", "Ore di produzione"], dep_rows, widths=[20 * mm, 18 * mm, 26 * mm, 32 * mm, 30 * mm, 32 * mm]),
        P(f"Tracciato evento: {e['event_track']['tiers']} tier da {e['event_track']['points_per_tier']} punti (1 Gettone = 1 punto); tracciato gratuito {e['event_track']['free_rubies_total_if_completed']} Rubini totali, "
          f"Pass Evento settimanale con materiali extra e oggetti garantiti (" + ", ".join(f"tier {k}: {RARITY_IT[v]}" for k, v in sorted(e['event_track']['premium_guaranteed_gear_milestones'].items(), key=lambda kv: int(kv[0]))) + ").", "small"),
        H2("10.3 Titan Hunt (boss di alleanza)"),
        *LI([
            f"Dura {ab['duration_hours']} ore; <b>{ab['free_attacks_per_day']} attacchi gratuiti</b> al giorno (+{ab['paid_extra_attacks_cap_per_day']} a {ab['extra_attack_rubies']} Rubini).",
            "<b>PV del boss = round(500.000 × tier^1,8)</b>; <b>danno di un attacco = round(potenza di campagna × 4)</b>.",
            f"Per attacco: {ab['personal_attack_reward']['forge_dust']} Polvere + {ab['personal_attack_reward']['war_coins']} Monete di Guerra. Casse di alleanza al {', '.join(map(str, ab['alliance_kill_chest_thresholds_pct']))}% dei PV. "
            f"Alla sconfitta del boss ogni partecipante riceve {ab['kill_reward_per_participant']['forge_dust']} Polvere, {ab['kill_reward_per_participant']['reforge_stone']} Pietre e {ab['kill_reward_per_participant']['war_coins']} Monete.",
            "Non influisce sul territorio né sulle guerre.",
        ]),
        H2("10.4 Missioni e calendario"),
        P(f"<b>Giornaliere</b>: {q['daily']['task_count']} compiti, casse a {', '.join(str(c['points']) for c in q['daily']['point_chests'])} punti, {q['daily']['total_rubies_per_day']} Rubini al giorno. "
          f"<b>Settimanali</b>: {q['weekly']['task_count']} compiti, {q['weekly']['total_rubies_per_week']} Rubini più Polvere, Pietre ed Essenza. "
          f"<b>Calendario accessi</b>: ciclo di {q['login_calendar']['cycle_days']} giorni, {q['login_calendar']['rubies_total_per_cycle']} Rubini a ciclo; il 7° giorno un tiro equipaggiamento potenziato + 10 Rubini."),
        tbl(["Compito giornaliero", "Obiettivo", "Punti"], [[x["key"].replace("_", " "), x["target"], x["points"]] for x in q["daily"]["templates"]], widths=[60 * mm, 25 * mm, 20 * mm]),
        tbl(["Compito settimanale", "Obiettivo", "Punti"], [[x["key"].replace("_", " "), x["target"], x["points"]] for x in q["weekly"]["templates"]], widths=[60 * mm, 25 * mm, 20 * mm]),
        P(f"Rubini gratuiti attesi in 28 giorni da giornaliere, settimanali e calendario: <b>{n(C['economy_controls']['free_rubies_expected_28d_from_daily_weekly_login'])}</b> (esclusi traguardi, Codex ed eventi).", "small"),
    ]


def _dep_example(mult):
    r = F.event_deploy_rewards(50, mult)
    return n(r["event_tokens"]), n(r["gold"]), n(r["soft_hours"])


def sec_alliance():
    a, w = C["alliances"], C["alliance_war"]
    node_rows = []
    for k, v in w["node_types"].items():
        bonus = "—" if not v.get("bonus") else ", ".join(f"{EFFECT_IT.get(bk, bk.replace('_', ' '))} +{bv}%" for bk, bv in v["bonus"].items())
        node_rows.append([k.replace("_", " "), v["count"], bonus, f"{v['stack_cap_pct']}%" if v.get("stack_cap_pct") else "—", v.get("special", "")])
    return [
        H1("11. Alleanze e Guerra d'Alleanza"),
        H2("11.1 Alleanze"),
        *LI([
            f"Sbloccate al <b>Castello {a['unlock_castle_level']}</b>; creare un'alleanza costa <b>{n(a['create_cost_gold'])} Oro</b>. Fino a <b>{a['member_cap']} membri</b>: 1 leader, max {a['roles']['officers_max']} ufficiali.",
            f"Ingresso: {', '.join(a['join_modes'])}. Se il leader è inattivo per {a['leader_inactivity_days_before_transfer']} giorni, il comando passa automaticamente.",
            f"Canali chat: {', '.join(a['chat_channels'])}; max {C['chat']['max_message_chars']} caratteri per messaggio.",
            f"Servono almeno <b>{a['minimum_members_to_attack']} membri</b> per dichiarare guerra.",
        ]),
        H2("11.2 Guerra 10 contro 10 (asincrona)"),
        *LI([
            f"Mappa stagionale di <b>{w['nodes_total']} nodi</b> ({w['map']}), fino a {w['alliances_per_shard_max']} alleanze per server; stagione di <b>{w['season_days']} giorni</b>, poi si azzerano territorio, bonus e punti.",
            f"Si attacca solo un nodo <b>adiacente</b> al proprio territorio, al massimo una dichiarazione ogni {w['attack_limit_per_alliance_hours']} ore per alleanza.",
            f"<b>Preparazione {w['prep_hours']} ore</b>: entrambe schierano <b>{w['attack_roster_size']} attaccanti</b> e <b>{w['defense_roster_size']} difensori</b>. Il roster si blocca {w['roster_lock_minutes_before_resolution']} minuti prima della risoluzione: "
            "da quel momento nulla (acquisti, potenziamenti) cambia quella guerra.",
            f"<b>Risoluzione</b>: {w['lane_resolution'].replace('10 deterministic lane battles; 1 point per lane', '10 duelli di corsia deterministici, 1 punto ciascuno')}; varianza seminata {w['seeded_variance_range'][0]}–{w['seeded_variance_range'][1]}. "
            "In ogni corsia si applicano i contro-attacchi v1.2 contro il mix di classi dell'avversario. Pareggio 5-5: vince chi ha la somma dei margini di vittoria più alta.",
            f"<b>Prenotazioni</b>: quando il leader o un ufficiale dichiara guerra (e si prenota per primo), i membri si prenotano e i <b>primi 10</b> schierano le loro truppe; ci si può ritirare fino al blocco. "
            f"Difesa incompleta: il server aggiunge NPC al {w['underfilled_defense_npc_fill']['npc_power_pct_of_alliance_median']}% della potenza mediana dell'alleanza. Attacco incompleto: consentito ma svantaggiato, ogni corsia senza attaccante è persa.",
            f"Ricompense: vincitori {w['rewards']['winner_season_points']} punti stagione + {w['rewards']['participant_war_coins'] + w['rewards']['winner_bonus_war_coins']} Monete; sconfitti {w['rewards']['loser_season_points']} punti + {w['rewards']['participant_war_coins']} Monete.",
            "Il castello base cade solo se un nemico è adiacente; l'alleanza sfollata riceve una nuova base neutrale dopo 12 ore.",
        ]),
        tbl(["Tipo di nodo", "Quanti", "Bonus per nodo", "Tetto cumulato", "Note"], node_rows, widths=[26 * mm, 14 * mm, 70 * mm, 22 * mm, 46 * mm]),
        WHY("la guerra è asincrona e a snapshot congelato perché tutti possano partecipare a orari diversi e nessuno possa comprare la vittoria all'ultimo minuto."),
    ]


def sec_achievements_shop():
    ach, cod, m = C["achievements"], C["codex"], C["monetization"]
    cat_it = {"campaign": "Campagna (stage)", "hero": "Eroe (livello)", "gear": "Equipaggiamento (leggendari+ trovati)", "kingdom": "Regno (Castello)", "army": "Esercito (unità reclutate)",
              "domain": "Dominio (caselle)", "events": "Eventi (spedizioni)", "alliance": "Alleanza (corsie di guerra o attacchi al boss)"}
    by_cat = defaultdict(list)
    for x in ach["catalog"]:
        by_cat[x["category"]].append(f"{n(x['threshold'])} → {x['rubies']} Rubini")
    ach_rows = [[cat_it[c], " · ".join(v)] for c, v in by_cat.items()]
    return [
        H1("12. Traguardi, Codex e negozio"),
        H2("12.1 Traguardi"),
        P(f"{ach['count']} traguardi in 8 categorie, {ach['total_rubies_across_all']} Rubini totali una tantum."),
        tbl(["Categoria", "Soglie e Rubini"], ach_rows, widths=[55 * mm, 123 * mm]),
        H2("12.2 Codex"),
        P(f"Tracce: {', '.join(cod['tracks'])}. Completamento: " + ", ".join(f"{x['pct']}% → {x['rubies']} Rubini" for x in cod["completion_milestones_pct"]) + ". Cornici profilo e lore, nessun paywall."),
        H2("12.3 Cosa si può comprare con i Rubini (e cosa no)"),
        *LI([
            "<b>Accelerazione timer</b>: max(5, ⌈minuti rimanenti / 3⌉) Rubini.",
            f"<b>Casse risorse</b> (ore di produzione): " + ", ".join(f"{c['key']} {c['production_hours_equivalent']}h = {c['rubies']} Rubini (max {c['daily_limit']}/giorno)" for c in m["resource_crates"]) + ".",
            f"Ingressi dungeon extra ({m['dungeon_extra_entry_rubies']}), attacchi Titan Hunt extra ({m['alliance_boss_extra_attack_rubies']}), ricariche energia evento, reset talenti ({C['hero']['talents']['respec_rubies']}).",
            f"Cosmetici: {', '.join(m['cosmetics'])}. Season Pass di {m['season_pass']['duration_days']} giorni ({m['season_pass']['levels']} livelli).",
            "<b>Mai</b>: equipaggiamento casuale a pagamento, aumento di rarità a pagamento, boost che alterino una guerra già bloccata.",
        ]),
        WHY(C["economy_controls"]["gear_power_purchase_rule"].replace("no direct random gear purchase; power progression comes from gameplay drops, Forge/materials and time/acceleration",
                                                                     "la potenza arriva solo dal gioco (drop, Forgia, materiali) e dal tempo; i Rubini possono accelerare, non sostituire.")),
    ]


def sec_formulas():
    rows = [
        ["Potenza nemica", "round(75 × 1,043^(stage−1) × (1 + 0,0015 × max(0, stage−50)))"],
        ["Potenza richiesta", "potenza nemica × 1,35 (Elite, ogni 5) · × 1,85 (Boss, ogni 10)"],
        ["Vittoria", "potenza eroe + potenza esercito ≥ potenza richiesta"],
        ["Durata vittoria", "clamp(round(18 + 55 × richiesta / totale), 18, 90) s"],
        ["Mostri per ondata", "min(12, 4 + ⌊(stage−1)/25⌋) · ondata boss: boss + min(10, ⌊stage/20⌋)"],
        ["Prima vittoria", "XP round(25 × stage^1,35) · Oro round(18 × stage^1,22) · Risorse round(12 × stage^1,18)"],
        ["Farm ripetuto", "5% XP · 12% Oro · 8% risorse della prima vittoria, ogni 120 s"],
        ["Potenza eroe", "round(ATT × 2 + DIF × 1,5 + PV × 0,15)"],
        ["Statistiche eroe", "ATT 20 + 5/lv · DIF 15 + 3/lv · PV 250 + 25/lv"],
        ["XP livello", "round(80 × lv^1,55 + 40 × lv)"],
        ["Punti talento", "min(20, ⌊lv/5⌋)"],
        ["Capacità di comando", "50 + lv eroe × 10 + lv castello² × 20"],
        ["Potenza esercito", "Σ quantità × potenza base × (1 + Σ% ricerche + 1,5% × Comandante + affissi + territorio) × (1 + contro-unità)"],
        ["Contro-unità", "+30% × quota classi 'forte' − 20% × quota classi 'debole'"],
        ["Livello oggetto", "min(100, ⌈stage/2⌉)"],
        ["Statistica oggetto", "round(coeff. slot × (1 + lv × 0,12) × molt. rarità) × (1 + 0,04F + 0,002F²)"],
        ["Affisso", "round(base@100 × (0,35 + 0,65 × lv/100) × molt. rarità × [0,85–1,15], 2)"],
        ["Forgia prossimo lv", "Oro round((25 + lv × 8) × 1,35^F) · Polvere ⌈(2 + lv × 0,08) × 1,22^F⌉"],
        ["Riforgiatura", "Oro round(50 × lv × molt. rarità) + Pietre per rarità"],
        ["Smantellamento", "Polvere = base rarità + ⌊lv/10⌋ × fattore rarità"],
        ["Accelerazione", "Rubini = max(5, ⌈minuti rimanenti / 3⌉)"],
        ["Dominio", "caselle = 1 + ⌊stage superato / 2⌋ · bonus = min(50%, ⌊caselle/10⌋ × 5%)"],
        ["Offline", "max 12 h · risorse 85% · bottino 70% · tiri oggetto min(1,2; 0,35 + stage/250)/h"],
        ["Titan Hunt", "PV boss round(500.000 × tier^1,8) · danno round(potenza × 4)"],
        ["Spedizione evento", "Gettoni round((20 + stage × 0,35) × m) · Oro round((150 + stage × 8) × m) · oggetto min(35%, 5% + stage × 0,1)"],
    ]
    return [H1("13. Tutte le formule in una pagina"), tbl(["Cosa", "Formula"], rows, widths=[38 * mm, 140 * mm]),
            Spacer(1, 6 * mm), P(f"Hash della specifica: {C['document']['spec_hash'][:16]}… · Ultime modifiche v1.2: " + " · ".join(C["document"]["changelog_v1_2"]), "small")]


def build():
    os.makedirs(OUT_DIR, exist_ok=True)
    tmp = OUT + ".tmp.pdf"
    doc = Doc(tmp)
    story = cover() + toc() + sec_intro() + [PageBreak()] + sec_resources() + [PageBreak()] + sec_hero() + [PageBreak()] + sec_campaign() + [PageBreak()] + \
        sec_units() + [PageBreak()] + sec_kingdom() + [PageBreak()] + sec_research() + [PageBreak()] + sec_gear() + [PageBreak()] + sec_domain_offline() + \
        [PageBreak()] + sec_dungeons_events_quests() + [PageBreak()] + sec_alliance() + [PageBreak()] + sec_achievements_shop() + [PageBreak()] + sec_formulas()
    doc.multiBuild(story)
    # read-only: nobody needs a password to open it; editing/annotating is locked with a random owner password.
    reader = PdfReader(tmp)
    writer = PdfWriter(clone_from=reader)
    writer.encrypt(user_password="", owner_password=secrets.token_urlsafe(24), algorithm="AES-256",
                   permissions_flag=UserAccessPermissions.PRINT | UserAccessPermissions.PRINT_TO_REPRESENTATION | UserAccessPermissions.EXTRACT | UserAccessPermissions.EXTRACT_TEXT_AND_GRAPHICS)
    with open(OUT, "wb") as f:
        writer.write(f)
    os.remove(tmp)
    print(f"OK {OUT} · {len(reader.pages)} pagine · {os.path.getsize(OUT)//1024} KB")


if __name__ == "__main__":
    build()
