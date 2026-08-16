"""Progiciel d'optimisation de la facture électrique au Sénégal.

Point d'entrée de l'application. Lancement :

    streamlit run app.py
"""

import streamlit as st

from vues import grille, optimisation, simulation, tableau_bord

st.set_page_config(
    page_title="Optimisation de la facture électrique — SENELEC",
    page_icon=":material/bolt:",
    layout="wide",
)

pages = st.navigation([
    st.Page(simulation.afficher, title="Simulation de facture",
            icon=":material/receipt_long:", default=True),
    st.Page(optimisation.afficher, title="Optimisation tarifaire",
            icon=":material/tune:", url_path="optimisation"),
    st.Page(grille.afficher, title="Grille tarifaire",
            icon=":material/table_view:", url_path="grille"),
    st.Page(tableau_bord.afficher, title="Tableau de bord",
            icon=":material/monitoring:", url_path="tableau-de-bord"),
])

with st.sidebar:
    st.markdown("**Progiciel d'optimisation de la facture électrique**")
    st.caption(
        "École Polytechnique de Thiès — Master interuniversitaire en énergies "
        "renouvelables et efficacité énergétique."
    )

pages.run()
