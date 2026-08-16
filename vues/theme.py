"""Charte graphique commune : palette, gabarit Plotly et formats de nombres.

Palette catégorielle validée (déficiences chromatiques et contraste) ; les
couleurs sont attribuées dans un ordre fixe, jamais recyclées.
"""

import plotly.graph_objects as go

# Palette catégorielle, ordre fixe
BLEU = "#2a78d6"
VERT = "#008300"
MAGENTA = "#e87ba4"
JAUNE = "#eda100"
SERIES = [BLEU, VERT, MAGENTA, JAUNE]

# Rampe séquentielle bleue (clair → foncé) pour les tranches ordonnées
RAMPE_BLEUE = ["#86b6ef", "#2a78d6", "#104281"]

# Encres et surfaces
SURFACE = "#fcfcfb"
ENCRE = "#0b0b0b"
ENCRE_SECONDAIRE = "#52514e"
ENCRE_ATTENUEE = "#898781"
GRILLE = "#e1e0d9"
AXE = "#c3c2b7"


def gabarit() -> go.layout.Template:
    """Gabarit Plotly appliqué à toutes les figures."""
    return go.layout.Template(layout=go.Layout(
        font=dict(family='system-ui, "Segoe UI", sans-serif', color=ENCRE, size=13),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        colorway=SERIES,
        separators=", ",
        margin=dict(l=10, r=10, t=36, b=10),
        xaxis=dict(gridcolor=GRILLE, linecolor=AXE, zerolinecolor=AXE,
                   tickfont=dict(color=ENCRE_ATTENUEE)),
        yaxis=dict(gridcolor=GRILLE, linecolor=AXE, zerolinecolor=AXE,
                   tickfont=dict(color=ENCRE_ATTENUEE)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        hoverlabel=dict(bgcolor="white", font_size=13),
    ))


def fcfa(montant: float, decimales: int = 0) -> str:
    """Formate un montant en francs CFA avec séparateur de milliers."""
    return f"{montant:,.{decimales}f}".replace(",", " ").replace(".", ",") + " F"


def kwh(valeur: float) -> str:
    return f"{valeur:,.0f}".replace(",", " ") + " kWh"
