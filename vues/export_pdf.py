"""Export PDF d'une facture simulée."""

from datetime import datetime

from fpdf import FPDF

from . import theme

_LARGEURS = (85, 35, 35, 30)
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
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _safe("Simulation de facture — SENELEC"), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, _safe(f"{facture.libelle} — période : {facture.periode}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, _safe(f"Édité le {datetime.now():%d/%m/%Y à %H:%M}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(235, 235, 235)
    for largeur, entete in zip(_LARGEURS, _ENTETES):
        pdf.cell(largeur, 8, _safe(entete), border=1, fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 10)
    for designation, valeur, tarif_unitaire, montant in facture.lignes:
        pdf.cell(_LARGEURS[0], 8, _safe(designation), border=1)
        pdf.cell(_LARGEURS[1], 8, _safe(valeur), border=1)
        tarif_txt = f"{tarif_unitaire:,.2f}".replace(",", " ") if tarif_unitaire else ""
        pdf.cell(_LARGEURS[2], 8, _safe(tarif_txt), border=1, align="R")
        pdf.cell(_LARGEURS[3], 8, _safe(theme.fcfa(montant)), border=1, align="R")
        pdf.ln()

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(sum(_LARGEURS[:3]), 8, _safe("Montant total toutes taxes"), border=1)
    pdf.cell(_LARGEURS[3], 8, _safe(theme.fcfa(facture.total_ttc)), border=1, align="R")
    pdf.ln(12)

    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(
        0, 5,
        _safe(
            "Simulation issue du progiciel d'optimisation de la facture "
            "électrique au Sénégal — mémoire de Master II, École "
            "Polytechnique de Thiès. Grille tarifaire hors taxes reproduite "
            "dans le mémoire ; montants indicatifs, sans valeur contractuelle."
        ),
    )

    return bytes(pdf.output())
