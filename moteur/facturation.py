"""Moteur de calcul des factures SENELEC.

Reproduit le déroulé de facturation décrit au chapitre 2 du mémoire :

- clients généraux basse tension (DPP, DMP, PPP, PMP) : facturation
  bimestrielle par tranches de consommation, en postpayé ou en prépaiement
  Woyofal ;
- clients spéciaux (DGP, PGP, MT, HT) : facturation mensuelle avec prime
  fixe sur la puissance souscrite, comptage binôme heures creuses (K1) et
  heures de pointe (K2), application liée au facteur de puissance et
  redevance de dépassement de puissance.
"""

import math
from dataclasses import dataclass, field

from . import tarifs
from .tarifs import TARIFS_BT, TARIFS_SPECIAUX


@dataclass
class Facture:
    """Résultat détaillé d'un calcul de facture."""

    code_tarif: str
    libelle: str
    periode: str                          # "bimestre" ou "mois"
    energie_kwh: float
    lignes: list = field(default_factory=list)   # (désignation, valeur, tarif, montant)
    montant_ht: float = 0.0
    tco: float = 0.0
    redevance: float = 0.0
    base_tva: float = 0.0
    tva: float = 0.0
    total_ttc: float = 0.0

    @property
    def prix_moyen_kwh(self) -> float:
        return self.total_ttc / self.energie_kwh if self.energie_kwh else 0.0

    @property
    def total_taxes(self) -> float:
        return self.tco + self.tva


def repartir_tranches(conso_kwh: float, seuils: tuple) -> tuple:
    """Répartit une consommation entre les trois tranches tarifaires."""
    s1, s2 = seuils
    t1 = min(conso_kwh, s1)
    t2 = min(max(conso_kwh - s1, 0.0), s2 - s1)
    t3 = max(conso_kwh - s2, 0.0)
    return t1, t2, t3


def facture_bt(code: str, conso_kwh: float, woyofal: bool = False,
               redevance: float = tarifs.REDEVANCE_BT) -> Facture:
    """Facture d'un client général basse tension (période bimestrielle).

    En prépaiement Woyofal, la troisième tranche est facturée au prix de la
    deuxième, conformément à la grille reproduite dans le mémoire.
    """
    tarif = TARIFS_BT[code]
    prix = tarif.prix_woyofal if woyofal else tarif.prix
    t1, t2, t3 = repartir_tranches(conso_kwh, tarif.seuils)

    montants = [t1 * prix[0], t2 * prix[1], t3 * prix[2]]
    montant_ht = sum(montants)
    tco = montant_ht * tarifs.TAUX_TCO

    # Base TVA : pour l'usage domestique, seule la troisième tranche est
    # assujettie ; pour l'usage professionnel, la totalité de l'énergie.
    if tarif.usage == "domestique":
        base_tva = montants[2] * (1 + tarifs.TAUX_TCO) + redevance
    else:
        base_tva = montant_ht * (1 + tarifs.TAUX_TCO) + redevance
    tva = base_tva * tarifs.TAUX_TVA

    f = Facture(
        code_tarif=code,
        libelle=tarif.libelle + (" — Woyofal" if woyofal else ""),
        periode="bimestre",
        energie_kwh=conso_kwh,
        montant_ht=montant_ht,
        tco=tco,
        redevance=redevance,
        base_tva=base_tva,
        tva=tva,
        total_ttc=montant_ht + tco + tva + redevance,
    )
    for i, (kwh, p, m) in enumerate(zip((t1, t2, t3), prix, montants), start=1):
        if kwh > 0:
            f.lignes.append((f"Consommation tranche {i}", f"{kwh:g} kWh", p, m))
    f.lignes.append(("Taxe communale (TCO)", f"{tarifs.TAUX_TCO:.1%}", None, tco))
    f.lignes.append(("Redevance", None, None, redevance))
    f.lignes.append(("TVA", f"{tarifs.TAUX_TVA:.0%}", None, tva))
    return f


def cos_phi(energie_active: float, energie_reactive: float) -> float:
    """Facteur de puissance déduit des énergies active et réactive."""
    if energie_active <= 0:
        return 1.0
    return energie_active / math.hypot(energie_active, energie_reactive)


def facture_speciale(code: str, k1_kwh: float, k2_kwh: float, ps_kw: float,
                     pmax_kw: float = None, energie_reactive: float = 0.0,
                     redevance: float = tarifs.REDEVANCE_SPECIAUX) -> Facture:
    """Facture mensuelle d'un client spécial (DGP, PGP, MT ou HT).

    ``pmax_kw`` est la puissance maximale relevée sur la période : tout
    dépassement de la puissance souscrite est facturé au taux de prime fixe
    multiplié par ``COEF_DEPASSEMENT_PS``.
    """
    tarif = TARIFS_SPECIAUX[code]
    energie = k1_kwh + k2_kwh

    montant_k1 = k1_kwh * tarif.prix_hc
    montant_k2 = k2_kwh * tarif.prix_hp
    montant_energie = montant_k1 + montant_k2
    prime_fixe = ps_kw * tarif.prime_fixe

    # Sans mesure d'énergie réactive, aucune application n'est calculée.
    if energie_reactive > 0:
        fp = cos_phi(energie, energie_reactive)
        taux_app = tarifs.taux_application(fp)
    else:
        fp, taux_app = 1.0, 0.0
    application = montant_energie * taux_app

    depassement = max((pmax_kw or 0.0) - ps_kw, 0.0)
    penalite = depassement * tarif.prime_fixe * tarifs.COEF_DEPASSEMENT_PS

    montant_ht = montant_energie + prime_fixe + application + penalite
    tco = montant_ht * tarifs.TAUX_TCO if tarif.tco_applicable else 0.0
    base_tva = montant_ht + tco + redevance
    tva = base_tva * tarifs.TAUX_TVA

    f = Facture(
        code_tarif=code,
        libelle=tarif.libelle,
        periode="mois",
        energie_kwh=energie,
        montant_ht=montant_ht,
        tco=tco,
        redevance=redevance,
        base_tva=base_tva,
        tva=tva,
        total_ttc=montant_ht + tco + tva + redevance,
    )
    f.lignes.append(("Énergie heures creuses (K1)", f"{k1_kwh:g} kWh", tarif.prix_hc, montant_k1))
    f.lignes.append(("Énergie heures de pointe (K2)", f"{k2_kwh:g} kWh", tarif.prix_hp, montant_k2))
    f.lignes.append(("Prime fixe", f"{ps_kw:g} kW", tarif.prime_fixe, prime_fixe))
    if abs(application) > 1e-9:
        nature = "majoration" if application > 0 else "minoration"
        f.lignes.append((f"Application cos φ = {fp:.2f} ({nature})", f"{taux_app:+.2%}", None, application))
    if penalite > 0:
        f.lignes.append(("Dépassement de puissance souscrite", f"{depassement:g} kW", tarif.prime_fixe * tarifs.COEF_DEPASSEMENT_PS, penalite))
    if tco > 0:
        f.lignes.append(("Taxe communale (TCO)", f"{tarifs.TAUX_TCO:.1%}", None, tco))
    f.lignes.append(("Redevance", None, None, redevance))
    f.lignes.append(("TVA", f"{tarifs.TAUX_TVA:.0%}", None, tva))
    return f
