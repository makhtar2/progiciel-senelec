"""Module d'optimisation tarifaire.

Quatre leviers, correspondant aux stratégies du chapitre 3 du mémoire :

1. comparaison des options tarifaires basse tension (postpayé / Woyofal,
   petite / moyenne puissance) pour un profil de consommation donné ;
2. comparaison des options tarifaires des clients spéciaux (MT : courte,
   générale ou longue utilisation ; HT : général ou secours) ;
3. recherche de la puissance souscrite optimale, celle qui minimise la somme
   prime fixe + pénalités de dépassement sur un historique de puissances
   maximales relevées ;
4. simulation du déplacement de consommation des heures de pointe vers les
   heures creuses.
"""

from . import facturation
from .tarifs import TARIFS_BT, TARIFS_SPECIAUX, PLAGES_UTILISATION_MT


def comparer_bt(conso_kwh: float, usage: str, ps_kw: float = None) -> list:
    """Compare toutes les options tarifaires basse tension ouvertes au client.

    Retourne une liste de dictionnaires triée du moins cher au plus cher.
    ``usage`` vaut "domestique" ou "professionnel" ; si ``ps_kw`` est fourni,
    seules les options compatibles avec cette puissance sont retenues.
    """
    resultats = []
    for code, tarif in TARIFS_BT.items():
        if tarif.usage != usage:
            continue
        if ps_kw is not None and not (tarif.ps_min < ps_kw <= tarif.ps_max):
            continue
        for woyofal in (False, True):
            f = facturation.facture_bt(code, conso_kwh, woyofal=woyofal)
            resultats.append({
                "option": f.libelle,
                "code": code,
                "mode": "Woyofal" if woyofal else "Postpayé",
                "total_ttc": f.total_ttc,
                "prix_moyen": f.prix_moyen_kwh,
            })
    resultats.sort(key=lambda r: r["total_ttc"])
    for r in resultats:
        r["surcout"] = r["total_ttc"] - resultats[0]["total_ttc"]
    return resultats


def comparer_speciaux(famille: str, k1_kwh: float, k2_kwh: float, ps_kw: float,
                      pmax_kw: float = None, energie_reactive: float = 0.0) -> list:
    """Compare les options tarifaires d'une même famille de clients spéciaux.

    ``famille`` vaut "MT" ou "HT". Retourne la liste des factures simulées,
    triée du moins cher au plus cher, avec l'économie annuelle réalisable
    par rapport à l'option la plus chère.
    """
    resultats = []
    for code, tarif in TARIFS_SPECIAUX.items():
        if tarif.famille != famille:
            continue
        f = facturation.facture_speciale(
            code, k1_kwh, k2_kwh, ps_kw,
            pmax_kw=pmax_kw, energie_reactive=energie_reactive,
        )
        resultats.append({
            "option": tarif.libelle,
            "code": code,
            "total_ttc": f.total_ttc,
            "prix_moyen": f.prix_moyen_kwh,
        })
    resultats.sort(key=lambda r: r["total_ttc"])
    for r in resultats:
        r["surcout"] = r["total_ttc"] - resultats[0]["total_ttc"]
        r["economie_annuelle"] = r["surcout"] * 12
    return resultats


def option_mt_recommandee(energie_annuelle_kwh: float, ps_kw: float) -> str:
    """Option tarifaire MT correspondant à la durée d'utilisation annuelle
    de la puissance souscrite (heures = énergie annuelle / PS)."""
    if ps_kw <= 0:
        return "MT-TG"
    heures = energie_annuelle_kwh / ps_kw
    for code, (h_min, h_max) in PLAGES_UTILISATION_MT.items():
        if h_min <= heures < h_max:
            return code
    return "MT-TLU"


def ps_optimale(code: str, pmax_mensuelles: list, ps_min: float = None,
                ps_max: float = None, pas: float = 1.0) -> dict:
    """Puissance souscrite qui minimise prime fixe + pénalités de dépassement
    sur l'historique ``pmax_mensuelles`` (puissances maximales relevées, kW).

    Balaye les valeurs de PS entre ``ps_min`` et ``ps_max`` (par défaut la
    plage observée) et retourne la meilleure, avec la courbe de coût complète.
    """
    tarif = TARIFS_SPECIAUX[code]
    if ps_min is None:
        ps_min = max(min(pmax_mensuelles) * 0.5, pas)
    if ps_max is None:
        ps_max = max(pmax_mensuelles)

    courbe = []
    ps = ps_min
    while ps <= ps_max + 1e-9:
        cout = 0.0
        for pmax in pmax_mensuelles:
            f = facturation.facture_speciale(code, 0.0, 0.0, ps, pmax_kw=pmax,
                                             redevance=0.0)
            cout += f.montant_ht          # prime fixe + pénalités uniquement
        courbe.append({"ps": round(ps, 2), "cout": cout})
        ps += pas

    meilleur = min(courbe, key=lambda p: p["cout"])
    return {
        "ps_optimale": meilleur["ps"],
        "cout_optimal": meilleur["cout"],
        "courbe": courbe,
    }


def deplacement_pointe(code: str, k1_kwh: float, k2_kwh: float, ps_kw: float,
                       part_deplacee: float,
                       energie_reactive: float = 0.0) -> dict:
    """Économie réalisée en déplaçant une part de la consommation des heures
    de pointe (K2) vers les heures creuses (K1), à énergie totale constante.

    ``part_deplacee`` est une fraction de K2 comprise entre 0 et 1.
    """
    avant = facturation.facture_speciale(code, k1_kwh, k2_kwh, ps_kw,
                                         energie_reactive=energie_reactive)
    transfert = k2_kwh * part_deplacee
    apres = facturation.facture_speciale(code, k1_kwh + transfert,
                                         k2_kwh - transfert, ps_kw,
                                         energie_reactive=energie_reactive)
    return {
        "facture_avant": avant,
        "facture_apres": apres,
        "kwh_deplaces": transfert,
        "economie_mensuelle": avant.total_ttc - apres.total_ttc,
        "economie_annuelle": (avant.total_ttc - apres.total_ttc) * 12,
    }


def correction_cos_phi(code: str, k1_kwh: float, k2_kwh: float, ps_kw: float,
                       energie_reactive: float) -> dict:
    """Gain obtenu en relevant le facteur de puissance à 1 (compensation
    de l'énergie réactive par batterie de condensateurs)."""
    avant = facturation.facture_speciale(code, k1_kwh, k2_kwh, ps_kw,
                                         energie_reactive=energie_reactive)
    apres = facturation.facture_speciale(code, k1_kwh, k2_kwh, ps_kw,
                                         energie_reactive=0.0)
    return {
        "cos_phi_actuel": facturation.cos_phi(k1_kwh + k2_kwh, energie_reactive),
        "economie_mensuelle": avant.total_ttc - apres.total_ttc,
        "economie_annuelle": (avant.total_ttc - apres.total_ttc) * 12,
    }
