"""Écran de consultation de la grille tarifaire SENELEC."""

import pandas as pd
import streamlit as st

from moteur import tarifs
from moteur.tarifs import TARIFS_BT, TARIFS_SPECIAUX
from . import theme


def afficher():
    st.title("Grille tarifaire")
    st.caption(
        "Grille officielle hors taxes reproduite dans le mémoire. Les valeurs "
        "sont centralisées dans le module « moteur/tarifs.py » : une mise à "
        "jour de la grille ne demande de modifier que ce fichier."
    )

    st.subheader("Basse tension, petite et moyenne puissance")
    st.caption("Facturation bimestrielle par tranches de consommation. "
               "En prépaiement Woyofal, la troisième tranche est facturée au "
               "prix de la deuxième.")
    df_bt = pd.DataFrame([{
        "Code": t.code,
        "Catégorie": t.libelle,
        "Puissance souscrite": f"{t.ps_min:g} à {t.ps_max:g} kW",
        "Tranche 1": f"0 à {t.seuils[0]} kWh",
        "Tranche 2": f"{t.seuils[0] + 1} à {t.seuils[1]} kWh",
        "Tranche 3": f"au-delà de {t.seuils[1]} kWh",
        "Prix T1 (F/kWh)": t.prix[0],
        "Prix T2 (F/kWh)": t.prix[1],
        "Prix T3 (F/kWh)": t.prix[2],
        "Prix T3 Woyofal": t.prix_woyofal[2],
    } for t in TARIFS_BT.values()])
    st.dataframe(df_bt, hide_index=True, width="stretch")

    st.subheader("Clients spéciaux : grande puissance, moyenne et haute tension")
    st.caption("Facturation mensuelle : prime fixe sur la puissance souscrite "
               "et comptage binôme heures creuses (K1) / heures de pointe (K2).")
    df_sp = pd.DataFrame([{
        "Code": t.code,
        "Catégorie": t.libelle,
        "Heures creuses (F/kWh)": t.prix_hc,
        "Heures de pointe (F/kWh)": t.prix_hp,
        "Prime fixe (F/kW/mois)": t.prime_fixe,
        "Taxe communale": "oui" if t.tco_applicable else "non",
    } for t in TARIFS_SPECIAUX.values()])
    st.dataframe(df_sp, hide_index=True, width="stretch")

    st.subheader("Facteur de puissance")
    gauche, droite = st.columns(2)
    with gauche:
        st.caption("Majoration du montant de l'énergie lorsque cos φ "
                   "descend sous 0,80.")
        df_maj = pd.DataFrame([{
            "cos φ": f"{seuil:.2f} et plus" if seuil > 0 else "moins de 0,40",
            "Majoration": f"{taux:.0%}",
        } for seuil, taux in tarifs.MAJORATIONS_COS_PHI])
        st.dataframe(df_maj, hide_index=True, width="stretch")
    with droite:
        st.caption("Minoration accordée entre 0,96 et 1,00.")
        df_min = pd.DataFrame([{
            "cos φ": f"{v:.2f}", "Minoration": f"{t:.2%}",
        } for v, t in tarifs.MINORATIONS_COS_PHI.items()])
        st.dataframe(df_min, hide_index=True, width="stretch")

    st.subheader("Taxes et paramètres")
    df_taxes = pd.DataFrame([
        {"Paramètre": "Taxe sur la valeur ajoutée (TVA)",
         "Valeur": f"{tarifs.TAUX_TVA:.0%}"},
        {"Paramètre": "Taxe communale sur les consommations (TCO)",
         "Valeur": f"{tarifs.TAUX_TCO:.1%}"},
        {"Paramètre": "Redevance par facture, clients généraux",
         "Valeur": theme.fcfa(tarifs.REDEVANCE_BT)},
        {"Paramètre": "Redevance par facture, clients spéciaux",
         "Valeur": theme.fcfa(tarifs.REDEVANCE_SPECIAUX)},
        {"Paramètre": "Coefficient de facturation du dépassement de puissance",
         "Valeur": f"{tarifs.COEF_DEPASSEMENT_PS:g} × prime fixe"},
    ])
    st.dataframe(df_taxes, hide_index=True, width="stretch")
