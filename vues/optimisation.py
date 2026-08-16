"""Écran d'optimisation : comparaison des options tarifaires et leviers d'économie."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from moteur import optimisation
from moteur.tarifs import TARIFS_SPECIAUX
from . import theme


def _barres_comparaison(resultats, titre, cle_libelle="option"):
    """Comparaison d'options sur une même mesure : barres d'une seule teinte,
    montant affiché en étiquette directe."""
    libelles = [r[cle_libelle] for r in resultats]
    valeurs = [r["total_ttc"] for r in resultats]
    fig = go.Figure(go.Bar(
        x=valeurs, y=libelles, orientation="h",
        marker=dict(color=theme.BLEU, line=dict(color=theme.SURFACE, width=2)),
        text=[theme.fcfa(v) for v in valeurs],
        textposition="outside", cliponaxis=False,
        hovertemplate="%{y} : %{x:,.0f} F<extra></extra>",
    ))
    fig.update_layout(
        template=theme.gabarit(), height=90 + 60 * len(libelles),
        title=titre, showlegend=False,
        xaxis=dict(tickformat=",.0f", ticksuffix=" F"),
        yaxis=dict(autorange="reversed"),
    )
    return fig


def _onglet_basse_tension():
    st.caption(
        "Pour un même profil de consommation, chaque option ouverte au client "
        "est facturée avec la grille en vigueur, puis classée du montant le "
        "plus faible au plus élevé."
    )
    c1, c2, c3 = st.columns(3)
    usage = c1.selectbox("Usage", ["domestique", "professionnel"],
                         format_func=str.capitalize)
    conso = c2.number_input("Consommation du bimestre (kWh)",
                            min_value=0.0, value=400.0, step=10.0)
    ps = c3.number_input("Puissance souscrite (kW)", min_value=0.0,
                         value=0.0, step=0.5,
                         help="Laisser à zéro pour comparer toutes les puissances.")

    resultats = optimisation.comparer_bt(conso, usage, ps_kw=ps or None)
    if not resultats:
        st.warning("Aucune option tarifaire ne correspond à cette puissance souscrite.")
        return

    meilleur = resultats[0]
    pire = resultats[-1]
    economie = pire["total_ttc"] - meilleur["total_ttc"]
    c1, c2 = st.columns(2)
    c1.metric("Option la plus avantageuse",
              f"{meilleur['code']} — {meilleur['mode']}")
    c2.metric("Écart avec l'option la plus chère", theme.fcfa(economie),
              delta=f"-{economie / pire['total_ttc']:.1%}" if pire["total_ttc"] else None,
              delta_color="inverse")

    resultats_affiches = [
        {**r, "option": f"{r['code']} — {r['mode']}"} for r in resultats
    ]
    st.plotly_chart(
        _barres_comparaison(resultats_affiches,
                            "Montant toutes taxes du bimestre, par option"),
        width="stretch",
    )

    df = pd.DataFrame([{
        "Option": r["option"],
        "Montant TTC": theme.fcfa(r["total_ttc"]),
        "Prix moyen du kWh": theme.fcfa(r["prix_moyen"], 2),
        "Surcoût": theme.fcfa(r["surcout"]),
    } for r in resultats_affiches])
    st.dataframe(df, hide_index=True, width="stretch")


def _onglet_mt_ht():
    st.caption(
        "Les clients spéciaux choisissent une option tarifaire selon la durée "
        "annuelle d'utilisation de leur puissance souscrite. Le progiciel "
        "compare les options de la famille sur un mois type."
    )
    c1, c2 = st.columns(2)
    with c1:
        famille = st.selectbox("Famille", ["MT", "HT"],
                               format_func=lambda f: "Moyenne tension" if f == "MT" else "Haute tension")
        ps = st.number_input("Puissance souscrite (kW)", min_value=1.0,
                             value=400.0, step=10.0)
    with c2:
        k1 = st.number_input("Énergie mensuelle heures creuses K1 (kWh)",
                             min_value=0.0, value=80000.0, step=1000.0)
        k2 = st.number_input("Énergie mensuelle heures de pointe K2 (kWh)",
                             min_value=0.0, value=15000.0, step=500.0)

    resultats = optimisation.comparer_speciaux(famille, k1, k2, ps)
    meilleur = resultats[0]

    c1, c2 = st.columns(2)
    c1.metric("Option la plus avantageuse", meilleur["code"])
    c2.metric("Économie annuelle contre l'option la plus chère",
              theme.fcfa(resultats[-1]["economie_annuelle"]))

    if famille == "MT":
        recommandee = optimisation.option_mt_recommandee((k1 + k2) * 12, ps)
        heures = (k1 + k2) * 12 / ps
        st.caption(
            f"Durée d'utilisation annuelle de la puissance souscrite : "
            f"{heures:,.0f} h, ce qui correspond réglementairement à l'option "
            f"{recommandee} ({TARIFS_SPECIAUX[recommandee].libelle}).".replace(",", " ")
        )

    st.plotly_chart(
        _barres_comparaison(resultats, "Montant mensuel toutes taxes, par option"),
        width="stretch",
    )


def _onglet_puissance_souscrite():
    st.caption(
        "La prime fixe rémunère la puissance mise à disposition : une puissance "
        "souscrite trop élevée gonfle la facture, trop faible elle déclenche des "
        "pénalités de dépassement. La courbe ci-dessous parcourt les valeurs "
        "possibles et repère le minimum."
    )
    c1, c2 = st.columns(2)
    with c1:
        code = st.selectbox("Option tarifaire", list(TARIFS_SPECIAUX),
                            format_func=lambda c: f"{c} — {TARIFS_SPECIAUX[c].libelle}",
                            index=3)
        saisie = st.text_input(
            "Puissances maximales relevées sur 12 mois (kW, séparées par des virgules)",
            value="320, 340, 310, 360, 380, 350, 330, 345, 370, 355, 340, 365",
        )
    with c2:
        ps_actuelle = st.number_input("Puissance souscrite actuelle (kW)",
                                      min_value=1.0, value=400.0, step=10.0)

    try:
        pmax = [float(v.replace(",", ".")) for v in saisie.replace(";", ",").split(",") if v.strip()]
    except ValueError:
        st.error("Saisie invalide : indiquer des nombres séparés par des virgules.")
        return
    if not pmax:
        st.info("Saisir au moins une puissance maximale relevée.")
        return

    resultat = optimisation.ps_optimale(code, pmax, ps_max=max(max(pmax), ps_actuelle) * 1.2)
    courbe = resultat["courbe"]

    cout_actuel = next((p["cout"] for p in courbe if p["ps"] >= ps_actuelle), courbe[-1]["cout"])
    economie = cout_actuel - resultat["cout_optimal"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Puissance souscrite optimale", f"{resultat['ps_optimale']:g} kW")
    c2.metric("Coût annuel fixe à l'optimum", theme.fcfa(resultat["cout_optimal"]))
    c3.metric("Économie annuelle sur la partie fixe", theme.fcfa(max(economie, 0)))

    fig = go.Figure()
    fig.add_scatter(
        x=[p["ps"] for p in courbe], y=[p["cout"] for p in courbe],
        mode="lines", line=dict(color=theme.BLEU, width=2), name="Coût annuel",
        hovertemplate="PS %{x:g} kW : %{y:,.0f} F<extra></extra>",
    )
    fig.add_scatter(
        x=[resultat["ps_optimale"]], y=[resultat["cout_optimal"]],
        mode="markers+text", text=["optimum"], textposition="top center",
        marker=dict(color=theme.VERT, size=10,
                    line=dict(color=theme.SURFACE, width=2)),
        name="Optimum", hoverinfo="skip",
    )
    fig.add_vline(x=ps_actuelle, line=dict(color=theme.ENCRE_ATTENUEE, dash="dot"),
                  annotation_text="PS actuelle",
                  annotation_font_color=theme.ENCRE_SECONDAIRE)
    fig.update_layout(
        template=theme.gabarit(), height=380, showlegend=False,
        title="Prime fixe et pénalités annuelles selon la puissance souscrite",
        xaxis=dict(title="Puissance souscrite (kW)"),
        yaxis=dict(tickformat=",.0f", ticksuffix=" F"),
    )
    st.plotly_chart(fig, width="stretch")


def _onglet_pointe_cos_phi():
    st.caption(
        "Deux leviers d'exploitation : déplacer une part de la consommation "
        "des heures de pointe vers les heures creuses, et compenser l'énergie "
        "réactive pour relever le facteur de puissance."
    )
    c1, c2 = st.columns(2)
    with c1:
        code = st.selectbox("Option tarifaire", list(TARIFS_SPECIAUX),
                            format_func=lambda c: f"{c} — {TARIFS_SPECIAUX[c].libelle}",
                            index=3, key="opt_pointe")
        ps = st.number_input("Puissance souscrite (kW)", min_value=1.0,
                             value=400.0, step=10.0, key="ps_pointe")
        reactif = st.number_input("Énergie réactive mensuelle (kVArh)",
                                  min_value=0.0, value=60000.0, step=1000.0)
    with c2:
        k1 = st.number_input("Énergie mensuelle heures creuses K1 (kWh)",
                             min_value=0.0, value=80000.0, step=1000.0, key="k1_pointe")
        k2 = st.number_input("Énergie mensuelle heures de pointe K2 (kWh)",
                             min_value=0.0, value=15000.0, step=500.0, key="k2_pointe")
        part = st.slider("Part de la consommation de pointe déplacée", 0, 100, 30,
                         format="%d %%") / 100

    deplacement = optimisation.deplacement_pointe(code, k1, k2, ps, part,
                                                  energie_reactive=reactif)
    correction = optimisation.correction_cos_phi(code, k1, k2, ps, reactif)

    st.markdown("**Déplacement de consommation hors pointe**")
    c1, c2, c3 = st.columns(3)
    c1.metric("Énergie déplacée", theme.kwh(deplacement["kwh_deplaces"]))
    c2.metric("Économie mensuelle", theme.fcfa(deplacement["economie_mensuelle"]))
    c3.metric("Économie annuelle", theme.fcfa(deplacement["economie_annuelle"]))

    st.markdown("**Compensation de l'énergie réactive**")
    c1, c2, c3 = st.columns(3)
    c1.metric("Facteur de puissance actuel", f"{correction['cos_phi_actuel']:.2f}")
    c2.metric("Économie mensuelle à cos φ = 1", theme.fcfa(correction["economie_mensuelle"]))
    c3.metric("Économie annuelle", theme.fcfa(correction["economie_annuelle"]))


def afficher():
    st.title("Optimisation tarifaire")
    st.caption(
        "Quatre leviers pour réduire la facture à consommation de service "
        "égale : le choix de l'option tarifaire, le dimensionnement de la "
        "puissance souscrite, le placement horaire de la consommation et la "
        "tenue du facteur de puissance."
    )
    onglets = st.tabs([
        "Basse tension", "Moyenne et haute tension",
        "Puissance souscrite", "Heures de pointe et cos φ",
    ])
    with onglets[0]:
        _onglet_basse_tension()
    with onglets[1]:
        _onglet_mt_ht()
    with onglets[2]:
        _onglet_puissance_souscrite()
    with onglets[3]:
        _onglet_pointe_cos_phi()
