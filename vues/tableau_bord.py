"""Tableau de bord : suivi des simulations enregistrées."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from moteur import stockage
from . import theme


def _graphique_historique(df: pd.DataFrame):
    fig = go.Figure(go.Bar(
        x=df["Date"], y=df["Montant TTC (F)"],
        marker=dict(color=theme.BLEU, line=dict(color=theme.SURFACE, width=2)),
        customdata=df["Libellé"],
        hovertemplate="%{x}<br>%{customdata} : %{y:,.0f} F<extra></extra>",
    ))
    fig.update_layout(
        template=theme.gabarit(), height=320, showlegend=False,
        title="Montant des factures simulées",
        xaxis=dict(type="category"),
        yaxis=dict(tickformat=",.0f", ticksuffix=" F"),
    )
    return fig


def afficher():
    st.title("Tableau de bord")
    st.caption(
        "Historique des simulations enregistrées depuis l'écran de simulation : "
        "suivi des montants, de l'énergie facturée et du prix moyen du kWh."
    )

    simulations = stockage.lister()
    if not simulations:
        st.info(
            "Aucune simulation enregistrée pour le moment. Depuis l'écran "
            "« Simulation », le bouton « Enregistrer la simulation » alimente "
            "ce tableau de bord."
        )
        return

    df = pd.DataFrame([{
        "Identifiant": s["id"],
        "Date": s["horodatage"].replace("T", " "),
        "Code": s["code_tarif"],
        "Libellé": s["libelle"],
        "Période": s["periode"],
        "Énergie (kWh)": s["energie_kwh"],
        "Montant HT (F)": s["montant_ht"],
        "Montant TTC (F)": s["total_ttc"],
    } for s in simulations])

    total = df["Montant TTC (F)"].sum()
    energie = df["Énergie (kWh)"].sum()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Simulations enregistrées", len(df))
    c2.metric("Montant cumulé", theme.fcfa(total))
    c3.metric("Énergie cumulée", theme.kwh(energie))
    c4.metric("Prix moyen du kWh", theme.fcfa(total / energie, 2) if energie else "—")

    st.plotly_chart(_graphique_historique(df.iloc[::-1]), width="stretch")

    st.dataframe(
        df, hide_index=True, width="stretch",
        column_config={
            "Énergie (kWh)": st.column_config.NumberColumn(format="localized"),
            "Montant HT (F)": st.column_config.NumberColumn(format="localized"),
            "Montant TTC (F)": st.column_config.NumberColumn(format="localized"),
        },
    )

    gauche, droite = st.columns([3, 1])
    with gauche:
        identifiant = st.selectbox(
            "Simulation à supprimer", df["Identifiant"],
            format_func=lambda i: f"n° {i} — "
            + df.loc[df["Identifiant"] == i, "Libellé"].iloc[0],
        )
    with droite:
        st.write("")
        if st.button("Supprimer", icon=":material/delete:"):
            stockage.supprimer(int(identifiant))
            st.rerun()
