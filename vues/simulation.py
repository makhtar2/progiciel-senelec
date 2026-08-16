"""Écran de simulation : reconstitution détaillée d'une facture SENELEC."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from moteur import facturation, stockage
from moteur.tarifs import TARIFS_BT, TARIFS_SPECIAUX
from . import theme


def _tableau_facture(facture) -> pd.DataFrame:
    lignes = [{
        "Désignation": designation,
        "Valeur": valeur or "",
        "Tarif (F/unité)": f"{tarif:,.2f}".replace(",", " ") if tarif else "",
        "Montant": theme.fcfa(montant),
    } for designation, valeur, tarif, montant in facture.lignes]
    lignes.append({
        "Désignation": "Montant total toutes taxes",
        "Valeur": "", "Tarif (F/unité)": "",
        "Montant": theme.fcfa(facture.total_ttc),
    })
    return pd.DataFrame(lignes)


def _graphique_composition(facture):
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
    composantes += ["Taxes (TCO et TVA)", "Redevance"]
    valeurs += [facture.total_taxes, facture.redevance]

    fig = go.Figure()
    for nom, valeur, couleur in zip(composantes, valeurs, theme.SERIES):
        fig.add_bar(
            y=[""], x=[valeur], name=nom, orientation="h",
            marker=dict(color=couleur, line=dict(color=theme.SURFACE, width=2)),
            hovertemplate=f"{nom} : %{{x:,.0f}} F<extra></extra>",
        )
    fig.update_layout(
        template=theme.gabarit(), barmode="stack", height=150,
        legend=dict(traceorder="normal"),
        margin=dict(t=10),
        xaxis=dict(tickformat=",.0f", ticksuffix=" F"),
        yaxis=dict(showticklabels=False),
    )
    return fig


def _graphique_tranches(code: str, conso: float):
    """Consommation ventilée par tranche tarifaire (rampe ordonnée)."""
    tarif = TARIFS_BT[code]
    t1, t2, t3 = facturation.repartir_tranches(conso, tarif.seuils)
    s1, s2 = tarif.seuils
    bornes = [f"0 à {s1} kWh", f"{s1 + 1} à {s2} kWh", f"au-delà de {s2} kWh"]
    fig = go.Figure(go.Bar(
        x=["Tranche 1", "Tranche 2", "Tranche 3"], y=[t1, t2, t3],
        customdata=bornes,
        marker=dict(color=theme.RAMPE_BLEUE, line=dict(color=theme.SURFACE, width=2)),
        hovertemplate="%{x} (%{customdata}) : %{y:,.0f} kWh<extra></extra>",
    ))
    fig.update_layout(
        template=theme.gabarit(), height=300, showlegend=False,
        title="Consommation par tranche",
        yaxis=dict(title="kWh", tickformat=",.0f"),
    )
    return fig


def _resultats(facture, graphique_secondaire=None):
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Montant toutes taxes", theme.fcfa(facture.total_ttc))
    c2.metric("Énergie facturée", theme.kwh(facture.energie_kwh))
    c3.metric("Prix moyen du kWh", theme.fcfa(facture.prix_moyen_kwh, 2))
    part_taxes = facture.total_taxes / facture.total_ttc if facture.total_ttc else 0
    c4.metric("Part des taxes", f"{part_taxes:.1%}")

    st.markdown("**Répartition du montant total**")
    st.plotly_chart(_graphique_composition(facture), width="stretch")

    if graphique_secondaire is not None:
        gauche, droite = st.columns([1, 1])
        with gauche:
            st.plotly_chart(graphique_secondaire, width="stretch")
        with droite:
            st.markdown("**Détail de la facture**")
            st.dataframe(_tableau_facture(facture), hide_index=True,
                         width="stretch")
    else:
        st.markdown("**Détail de la facture**")
        st.dataframe(_tableau_facture(facture), hide_index=True,
                     width="stretch")

    if st.button("Enregistrer la simulation", icon=":material/save:"):
        stockage.enregistrer(facture)
        st.success("Simulation enregistrée. Elle est visible dans le tableau de bord.")


def afficher():
    st.title("Simulation de facture")
    st.caption(
        "Reconstitution du calcul de la facture SENELEC à partir de la grille "
        "tarifaire en vigueur : tranches de consommation en basse tension, "
        "prime fixe et comptage binôme pour les clients spéciaux."
    )

    segment = st.radio(
        "Catégorie de client",
        ["Basse tension (usage général)", "Clients spéciaux (GP, MT, HT)"],
        horizontal=True,
    )

    if segment == "Basse tension (usage général)":
        gauche, milieu, droite = st.columns(3)
        with gauche:
            code = st.selectbox(
                "Option tarifaire", list(TARIFS_BT),
                format_func=lambda c: f"{c} — {TARIFS_BT[c].libelle}",
            )
        with milieu:
            conso = st.number_input("Consommation du bimestre (kWh)",
                                    min_value=0.0, value=300.0, step=10.0)
        with droite:
            mode = st.selectbox("Mode de facturation", ["Postpayé", "Prépaiement Woyofal"])

        facture = facturation.facture_bt(code, conso,
                                         woyofal=(mode == "Prépaiement Woyofal"))
        _resultats(facture, _graphique_tranches(code, conso))

    else:
        gauche, droite = st.columns(2)
        with gauche:
            code = st.selectbox(
                "Option tarifaire", list(TARIFS_SPECIAUX),
                format_func=lambda c: f"{c} — {TARIFS_SPECIAUX[c].libelle}",
            )
            ps = st.number_input("Puissance souscrite (kW)", min_value=1.0,
                                 value=250.0, step=10.0)
            pmax = st.number_input("Puissance maximale relevée (kW)",
                                   min_value=0.0, value=0.0, step=10.0,
                                   help="Laisser à zéro si aucun dépassement n'est à facturer.")
        with droite:
            k1 = st.number_input("Énergie heures creuses K1 (kWh)",
                                 min_value=0.0, value=40000.0, step=1000.0)
            k2 = st.number_input("Énergie heures de pointe K2 (kWh)",
                                 min_value=0.0, value=8000.0, step=500.0)
            reactif = st.number_input("Énergie réactive (kVArh)",
                                      min_value=0.0, value=0.0, step=500.0,
                                      help="Sert au calcul du facteur de puissance et de l'application.")

        facture = facturation.facture_speciale(code, k1, k2, ps,
                                               pmax_kw=pmax or None,
                                               energie_reactive=reactif)
        _resultats(facture)
