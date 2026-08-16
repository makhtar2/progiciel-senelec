"""Export PDF d'une facture simulée.

Reprend la structure d'une facture SENELEC réelle (bandeaux « Éléments de
facturation », tableau des tranches, récapitulatif des taxes, montant net
à payer encadré) plutôt qu'un relevé générique — ce document reste une
simulation académique : aucune donnée client réelle n'y figure.
"""

from datetime import datetime
from pathlib import Path

from fpdf import FPDF

from moteur.tarifs import TAUX_TCO

from . import formatage as fmt

_LOGO = Path(__file__).resolve().parent.parent / "static" / "img" / "senelec-logo.png"

_PRIMAIRE = (0, 77, 153)
_PRIMAIRE_FONCE = (0, 51, 102)
_ACCENT = (232, 122, 30)
_ACCENT_DOUX = (252, 232, 214)
_GRIS_CLAIR = (244, 246, 248)
_GRIS_BORDURE = (216, 220, 224)
_GRIS_TEXTE = (85, 85, 85)
_INK = (34, 34, 34)
_BLANC = (255, 255, 255)

_MARGE = 15
_LIGNES_TAXES = ("Taxe communale", "Redevance", "TVA")


def _safe(texte) -> str:
    """Rabat le texte sur le Windows-1252 des polices standard du PDF
    (remplace les caractères hors jeu, notamment φ, par leur équivalent
    lisible ; Windows-1252 couvre les accents français et le tiret cadratin)."""
    texte = str(texte or "").replace("φ", "phi")
    return texte.encode("cp1252", "replace").decode("cp1252")


def _bandeau_section(pdf: FPDF, largeur_utile: float, titre: str) -> None:
    pdf.set_fill_color(*_ACCENT)
    pdf.set_text_color(*_BLANC)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(largeur_utile, 8, "  " + _safe(titre), fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def _ligne_info(pdf: FPDF, largeur_utile: float, gauche: tuple, droite: tuple) -> None:
    """Une ligne à deux champs libellé/valeur, façon bloc d'informations."""
    moitie = largeur_utile / 2
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*_GRIS_TEXTE)
    y = pdf.get_y()
    pdf.cell(moitie, 4, _safe(gauche[0].upper()))
    pdf.cell(moitie, 4, _safe(droite[0].upper()) if droite else "")
    pdf.ln(4.5)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(*_INK)
    pdf.cell(moitie, 5, _safe(gauche[1]))
    pdf.cell(moitie, 5, _safe(droite[1]) if droite else "")
    pdf.ln(7)


def _ligne_recap(pdf: FPDF, largeur_utile: float, libelle: str, montant: float, gras: bool = False) -> None:
    pdf.set_font("Helvetica", "B" if gras else "", 9)
    pdf.set_text_color(*_INK)
    pdf.cell(largeur_utile * 0.7, 7, _safe(libelle))
    pdf.cell(largeur_utile * 0.3, 7, _safe(fmt.fcfa(montant)), align="R")
    pdf.ln(7)


def facture_pdf_bytes(facture) -> bytes:
    """Construit le PDF d'une facture simulée et retourne son contenu binaire."""
    pdf = FPDF(format="A4")
    pdf.core_fonts_encoding = "cp1252"
    pdf.set_margins(_MARGE, _MARGE, _MARGE)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    largeur_page = pdf.w
    largeur_utile = largeur_page - 2 * _MARGE

    # --- En-tête : logo, référence de la simulation --------------------
    if _LOGO.exists():
        pdf.image(str(_LOGO), x=_MARGE, y=13, h=10)
    pdf.set_xy(_MARGE, 25)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*_GRIS_TEXTE)
    pdf.cell(largeur_utile, 4, _safe(f"Simulation éditée le {datetime.now():%d/%m/%Y à %H:%M}"),
             align="R")
    pdf.set_y(34)

    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*_PRIMAIRE_FONCE)
    pdf.cell(largeur_utile, 7, _safe("SIMULATION DE FACTURE"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # --- Bloc identification de l'option tarifaire ----------------------
    pdf.set_draw_color(*_GRIS_BORDURE)
    y_bloc = pdf.get_y()
    pdf.rect(_MARGE, y_bloc, largeur_utile, 18)
    pdf.set_xy(_MARGE + 4, y_bloc + 2)
    _ligne_info(
        pdf, largeur_utile - 8,
        ("Catégorie tarifaire", f"{facture.code_tarif} — {facture.libelle}"),
        ("Période de facturation", facture.periode.capitalize()),
    )
    pdf.ln(4)

    # --- Éléments de facturation : détail de la consommation -----------
    _bandeau_section(pdf, largeur_utile, "Éléments de facturation")

    lignes_conso = [l for l in facture.lignes if not l[0].startswith(_LIGNES_TAXES)]

    pdf.set_fill_color(*_ACCENT_DOUX)
    pdf.set_text_color(*_PRIMAIRE_FONCE)
    pdf.set_font("Helvetica", "B", 8.5)
    largeurs = (68, 34, 38, 40)
    entetes = ("Désignation", "Quantité", "Prix (FCFA/unité)", "Montant (FCFA)")
    for l, entete in zip(largeurs, entetes):
        align = "R" if entete != "Désignation" else ""
        pdf.cell(l, 7, _safe(entete), fill=True, align=align)
    pdf.ln()

    pdf.set_font("Helvetica", "", 8.5)
    paire = False
    for designation, valeur, tarif_unitaire, montant in lignes_conso:
        pdf.set_text_color(*_INK)
        pdf.set_fill_color(*(_GRIS_CLAIR if paire else _BLANC))
        pdf.cell(largeurs[0], 7, _safe(designation), fill=True)
        pdf.cell(largeurs[1], 7, _safe(valeur), align="R", fill=True)
        tarif_txt = fmt.nombre(tarif_unitaire) if tarif_unitaire else ""
        pdf.cell(largeurs[2], 7, _safe(tarif_txt), align="R", fill=True)
        pdf.cell(largeurs[3], 7, _safe(fmt.nombre(montant, 0)), align="R", fill=True)
        pdf.ln()
        paire = not paire

    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_fill_color(*_GRIS_CLAIR)
    pdf.set_text_color(*_PRIMAIRE_FONCE)
    pdf.cell(sum(largeurs[:3]), 8, _safe("  TOTAL CONSOMMATION"), fill=True)
    pdf.cell(largeurs[3], 8, _safe(fmt.nombre(facture.montant_ht, 0)), align="R", fill=True)
    pdf.ln(12)

    # --- Récapitulatif des taxes et redevances --------------------------
    _bandeau_section(pdf, largeur_utile, "Récapitulatif de la facturation")

    _ligne_recap(pdf, largeur_utile, "Montant consommation (hors taxes)", facture.montant_ht)
    if facture.tco:
        _ligne_recap(pdf, largeur_utile, f"Taxe communale — TCO ({fmt.pourcentage(TAUX_TCO, 1)})", facture.tco)
    _ligne_recap(pdf, largeur_utile, "Redevance", facture.redevance)
    _ligne_recap(pdf, largeur_utile, "Base de calcul TVA", facture.base_tva)
    _ligne_recap(pdf, largeur_utile, "TVA (18 %)", facture.tva)
    pdf.ln(4)

    # --- Montant net à payer, encadré -----------------------------------
    y_total = pdf.get_y()
    h_total = 20
    pdf.set_fill_color(*_PRIMAIRE_FONCE)
    pdf.rect(_MARGE, y_total, largeur_utile, h_total, style="F")
    pdf.set_xy(_MARGE + 8, y_total + 5)
    pdf.set_text_color(*_BLANC)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(largeur_utile * 0.55, 10, _safe("MONTANT NET À PAYER"))
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(largeur_utile * 0.45 - 16, 10, _safe(fmt.fcfa(facture.total_ttc)), align="R")
    pdf.set_y(y_total + h_total + 10)

    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*_GRIS_TEXTE)
    pdf.multi_cell(0, 5, _safe("Progiciel d'optimisation de la facture électrique"))

    return bytes(pdf.output())
