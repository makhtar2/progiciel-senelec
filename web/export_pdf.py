"""Export PDF d'une facture simulée.

Reprend l'identité visuelle SENELEC de l'application web : logo, bandeau
marine, montant total mis en avant, tableau à en-tête colorée.
"""

from datetime import datetime
from pathlib import Path

from fpdf import FPDF

from . import formatage as fmt

_LOGO = Path(__file__).resolve().parent.parent / "static" / "img" / "senelec-logo.png"

_PRIMAIRE = (0, 77, 153)
_PRIMAIRE_FONCE = (0, 51, 102)
_ACCENT = (232, 122, 30)
_GRIS_CLAIR = (244, 246, 248)
_GRIS_TEXTE = (85, 85, 85)
_INK = (34, 34, 34)
_BLANC = (255, 255, 255)

_LARGEURS = (78, 32, 30, 40)
_ENTETES = ("Désignation", "Valeur", "Tarif (F/unité)", "Montant")


def _safe(texte) -> str:
    """Rabat le texte sur le Windows-1252 des polices standard du PDF
    (remplace les caractères hors jeu, notamment φ, par leur équivalent
    lisible ; Windows-1252 couvre les accents français et le tiret cadratin)."""
    texte = str(texte or "").replace("φ", "phi")
    return texte.encode("cp1252", "replace").decode("cp1252")


def facture_pdf_bytes(facture) -> bytes:
    """Construit le PDF d'une facture simulée et retourne son contenu binaire."""
    pdf = FPDF(format="A4")
    pdf.core_fonts_encoding = "cp1252"
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    marge = 15
    largeur_page = pdf.w
    largeur_utile = largeur_page - 2 * marge

    if _LOGO.exists():
        pdf.image(str(_LOGO), x=marge, y=13, h=11)

    # Bandeau marine : titre + option tarifaire, en pleine largeur (fond
    # perdu, comme le bandeau de titre de l'écran de simulation).
    y_bandeau = 30
    h_bandeau = 24
    pdf.set_fill_color(*_PRIMAIRE_FONCE)
    pdf.rect(0, y_bandeau, largeur_page, h_bandeau, style="F")

    pdf.set_xy(marge, y_bandeau + 4)
    pdf.set_text_color(*_BLANC)
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(largeur_utile, 8, _safe("Simulation de facture"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(marge)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(largeur_utile, 6, _safe(f"{facture.libelle} — période : {facture.periode}"))

    pdf.set_xy(marge, y_bandeau + h_bandeau + 5)
    pdf.set_text_color(*_GRIS_TEXTE)
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(largeur_utile, 5, _safe(f"Édité le {datetime.now():%d/%m/%Y à %H:%M}"))

    # Montant total mis en avant (comme les indicateurs de l'écran web).
    y_hero = y_bandeau + h_bandeau + 14
    h_hero = 22
    pdf.set_fill_color(*_GRIS_CLAIR)
    pdf.rect(marge, y_hero, largeur_utile, h_hero, style="F")
    pdf.set_xy(marge, y_hero + 4)
    pdf.set_text_color(*_GRIS_TEXTE)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(largeur_utile - 8, 5, _safe("MONTANT TOTAL TOUTES TAXES"), align="R")
    pdf.set_xy(marge, y_hero + 9)
    pdf.set_text_color(*_PRIMAIRE)
    pdf.set_font("Helvetica", "B", 17)
    pdf.cell(largeur_utile - 8, 9, _safe(fmt.fcfa(facture.total_ttc)), align="R")

    pdf.set_y(y_hero + h_hero + 10)

    # Tableau détaillé : en-tête marine, lignes alternées.
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(*_PRIMAIRE_FONCE)
    pdf.set_text_color(*_BLANC)
    for largeur, entete in zip(_LARGEURS, _ENTETES):
        align = "R" if entete in ("Tarif (F/unité)", "Montant") else ""
        pdf.cell(largeur, 9, _safe(entete), fill=True, align=align)
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    paire = False
    for designation, valeur, tarif_unitaire, montant in facture.lignes:
        pdf.set_text_color(*_INK)
        pdf.set_fill_color(*(_GRIS_CLAIR if paire else _BLANC))
        pdf.cell(_LARGEURS[0], 8, _safe(designation), fill=True)
        pdf.cell(_LARGEURS[1], 8, _safe(valeur), fill=True)
        tarif_txt = f"{tarif_unitaire:,.2f}".replace(",", " ") if tarif_unitaire else ""
        pdf.cell(_LARGEURS[2], 8, _safe(tarif_txt), align="R", fill=True)
        pdf.cell(_LARGEURS[3], 8, _safe(fmt.fcfa(montant)), align="R", fill=True)
        pdf.ln()
        paire = not paire

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(*_ACCENT)
    pdf.set_text_color(*_BLANC)
    pdf.cell(sum(_LARGEURS[:3]), 10, _safe("  Montant total toutes taxes"), fill=True)
    pdf.cell(_LARGEURS[3], 10, _safe(fmt.fcfa(facture.total_ttc) + "  "), align="R", fill=True)
    pdf.ln(18)

    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*_GRIS_TEXTE)
    pdf.multi_cell(0, 5, _safe("Progiciel d'optimisation de la facture électrique"))

    return bytes(pdf.output())
