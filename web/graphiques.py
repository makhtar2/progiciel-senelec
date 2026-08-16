"""Construction des graphiques Plotly, rendus en fragments HTML intégrés
aux pages (bibliothèque Plotly chargée une seule fois dans le gabarit).

La palette et la typographie reprennent exactement les jetons de design
définis dans ``static/css/app.css``, pour que les graphiques se fondent
dans la page plutôt que de ressembler à un composant rapporté.
"""

import plotly.graph_objects as go

from moteur import facturation
from moteur.tarifs import TARIFS_BT

from . import formatage as fmt

INK = "#222222"
INK_ATTENUEE = "#8b8d93"
SURFACE = "#ffffff"
GRILLE = "#eceff2"
AXE = "#d5d9de"

# Palette exacte du site senelec.sn (moteur/../static/css/app.css)
PRIMAIRE = "#004d99"
ACCENT = "#e87a1e"
SARCELLE = "#018a9c"
VERT = "#2ecc71"
ALERTE = "#e74c3c"
SERIES = [PRIMAIRE, ACCENT, SARCELLE, VERT]
RAMPE_BLEUE = ["#0080cc", "#004d99", "#003366"]

_CONFIG = {"displayModeBar": False, "responsive": True}


def _gabarit() -> go.layout.Template:
    return go.layout.Template(layout=go.Layout(
        # Police système uniquement (pas la police web de la page) : le
        # texte SVG de Plotly est mesuré une fois au tracé et ne se
        # réajuste pas quand une police chargée en asynchrone arrive
        # ensuite, contrairement au texte HTML — un mélange des deux
        # produit des libellés d'axe chevauchés.
        font=dict(family='system-ui, -apple-system, sans-serif', color=INK, size=13),
        autosize=True,
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        colorway=SERIES,
        separators=", ",
        margin=dict(l=10, r=10, t=36, b=10),
        xaxis=dict(gridcolor=GRILLE, linecolor=AXE, zerolinecolor=AXE,
                   tickfont=dict(color=INK_ATTENUEE), automargin=True),
        yaxis=dict(gridcolor=GRILLE, linecolor=AXE, zerolinecolor=AXE,
                   tickfont=dict(color=INK_ATTENUEE), automargin=True),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        hoverlabel=dict(bgcolor=INK, bordercolor=INK, font_size=13,
                        font_color=SURFACE,
                        font_family='system-ui, -apple-system, sans-serif'),
    ))


def _fragment(fig: go.Figure) -> str:
    return fig.to_html(full_html=False, include_plotlyjs=False, config=_CONFIG)


def composition_facture(facture) -> str:
    """Barre horizontale empilée : répartition du montant total de la facture."""
    composantes, valeurs = [], []
    energie = sum(m for d, _, _, m in facture.lignes
                  if d.startswith(("Consommation", "Énergie")))
    composantes.append("Énergie")
    valeurs.append(energie)
    prime = sum(m for d, _, _, m in facture.lignes if d.startswith("Prime fixe"))
    if prime:
        composantes.append("Prime fixe")
        valeurs.append(prime)
    autres = sum(m for d, _, _, m in facture.lignes
                 if d.startswith(("Application", "Dépassement")))
    if abs(autres) > 1e-9:
        composantes.append("Application et pénalités")
        valeurs.append(autres)
    composantes += ["Taxes", "Redevance"]
    valeurs += [facture.total_taxes, facture.redevance]

    fig = go.Figure()
    for nom, valeur, couleur in zip(composantes, valeurs, SERIES):
        fig.add_bar(
            y=[""], x=[valeur], name=nom, orientation="h",
            marker=dict(color=couleur, line=dict(color=SURFACE, width=2)),
            hovertemplate=f"{nom} : %{{x:,.0f}} FCFA<extra></extra>",
        )
    fig.update_layout(
        template=_gabarit(), barmode="stack", height=150,
        legend=dict(traceorder="normal"),
        margin=dict(t=6, b=30, r=28),
        xaxis=dict(tickformat=",.0f", ticksuffix=" FCFA"),
        yaxis=dict(showticklabels=False),
    )
    return _fragment(fig)


def tranches_bt(code: str, conso: float) -> str:
    """Consommation ventilée par tranche tarifaire (rampe ordonnée)."""
    tarif = TARIFS_BT[code]
    t1, t2, t3 = facturation.repartir_tranches(conso, tarif.seuils)
    s1, s2 = tarif.seuils
    bornes = [f"0 à {s1} kWh", f"{s1 + 1} à {s2} kWh", f"au-delà de {s2} kWh"]
    fig = go.Figure(go.Bar(
        x=["Tranche 1", "Tranche 2", "Tranche 3"], y=[t1, t2, t3],
        customdata=bornes,
        marker=dict(color=RAMPE_BLEUE, line=dict(color=SURFACE, width=2)),
        hovertemplate="%{x} (%{customdata}) : %{y:,.0f} kWh<extra></extra>",
    ))
    fig.update_layout(
        template=_gabarit(), height=280, showlegend=False,
        title="Consommation par tranche",
        yaxis=dict(title="kWh", tickformat=",.0f"),
    )
    return _fragment(fig)


def barres_comparaison(resultats: list, titre: str, cle_libelle: str = "option") -> str:
    libelles = [r[cle_libelle] for r in resultats]
    valeurs = [r["total_ttc"] for r in resultats]
    fig = go.Figure(go.Bar(
        x=valeurs, y=libelles, orientation="h",
        marker=dict(color=PRIMAIRE, line=dict(color=SURFACE, width=2)),
        text=[fmt.fcfa(v) for v in valeurs],
        textposition="outside", cliponaxis=False,
        hovertemplate="%{y} : %{x:,.0f} FCFA<extra></extra>",
    ))
    fig.update_layout(
        template=_gabarit(), height=90 + 55 * len(libelles),
        title=titre, showlegend=False,
        margin=dict(l=10),
        xaxis=dict(tickformat=",.0f", ticksuffix=" FCFA"),
        yaxis=dict(autorange="reversed", automargin=True),
    )
    return _fragment(fig)


def courbe_ps_optimale(courbe: list, ps_optimale: float, cout_optimal: float,
                       ps_actuelle: float) -> str:
    fig = go.Figure()
    fig.add_scatter(
        x=[p["ps"] for p in courbe], y=[p["cout"] for p in courbe],
        mode="lines", line=dict(color=PRIMAIRE, width=2), name="Coût annuel",
        hovertemplate="PS %{x:g} kW : %{y:,.0f} FCFA<extra></extra>",
    )
    fig.add_scatter(
        x=[ps_optimale], y=[cout_optimal],
        mode="markers+text", text=["optimum"], textposition="top center",
        marker=dict(color=ACCENT, size=10, line=dict(color=SURFACE, width=2)),
        name="Optimum", hoverinfo="skip",
    )
    fig.add_vline(x=ps_actuelle, line=dict(color=INK_ATTENUEE, dash="dot"),
                  annotation_text="PS actuelle", annotation_font_color=INK_ATTENUEE)
    fig.update_layout(
        template=_gabarit(), height=360, showlegend=False,
        title="Prime fixe et pénalités annuelles selon la puissance souscrite",
        xaxis=dict(title="Puissance souscrite (kW)"),
        yaxis=dict(tickformat=",.0f", ticksuffix=" FCFA"),
    )
    return _fragment(fig)


def historique_simulations(dates: list, montants: list, libelles: list) -> str:
    fig = go.Figure(go.Bar(
        x=dates, y=montants,
        marker=dict(color=PRIMAIRE, line=dict(color=SURFACE, width=2)),
        customdata=libelles,
        hovertemplate="%{x}<br>%{customdata} : %{y:,.0f} FCFA<extra></extra>",
    ))
    fig.update_layout(
        template=_gabarit(), height=300, showlegend=False,
        title="Montant des factures simulées",
        xaxis=dict(type="category"),
        yaxis=dict(tickformat=",.0f", ticksuffix=" FCFA"),
    )
    return _fragment(fig)
