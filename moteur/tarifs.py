"""Grille tarifaire SENELEC.

Valeurs hors taxes issues de la grille officielle reproduite dans le mémoire
(chapitre 2) : tranches de consommation basse tension, prix de l'énergie,
primes fixes des clients spéciaux, barèmes de majoration et de minoration
liés au facteur de puissance.

Toute la grille est centralisée ici : pour actualiser les tarifs, seul ce
fichier doit être modifié.
"""

from dataclasses import dataclass

# Taux réglementaires
TAUX_TVA = 0.18          # Taxe sur la valeur ajoutée
TAUX_TCO = 0.025         # Taxe communale sur les consommations d'énergie
REDEVANCE_BT = 500.0     # Redevance fixe par facture (FCFA), ajustable
REDEVANCE_SPECIAUX = 5000.0

# Coefficient appliqué au taux de prime fixe pour facturer chaque kW
# de dépassement de la puissance souscrite.
COEF_DEPASSEMENT_PS = 2.0


# ---------------------------------------------------------------------------
# Basse tension, petite et moyenne puissance (facturation bimestrielle)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TarifBT:
    code: str
    libelle: str
    usage: str                  # "domestique" ou "professionnel"
    ps_min: float               # bornes de puissance souscrite (kW)
    ps_max: float
    seuils: tuple               # bornes hautes des tranches 1 et 2 (kWh/bimestre)
    prix: tuple                 # prix postpayé par tranche (FCFA/kWh)
    prix_woyofal: tuple         # prix en prépaiement Woyofal (FCFA/kWh)


TARIFS_BT = {
    "DPP": TarifBT(
        "DPP", "Domestique Petite Puissance", "domestique", 0.0, 6.0,
        (150, 250), (90.47, 101.64, 112.65), (90.47, 101.64, 101.64),
    ),
    "DMP": TarifBT(
        "DMP", "Domestique Moyenne Puissance", "domestique", 6.0, 17.0,
        (50, 300), (96.02, 102.44, 112.02), (96.02, 102.44, 102.44),
    ),
    "PPP": TarifBT(
        "PPP", "Professionnel Petite Puissance", "professionnel", 0.0, 6.0,
        (50, 500), (128.85, 135.68, 147.68), (128.85, 135.68, 135.68),
    ),
    "PMP": TarifBT(
        "PMP", "Professionnel Moyenne Puissance", "professionnel", 6.0, 17.0,
        (100, 500), (129.81, 136.53, 149.24), (129.81, 136.53, 136.53),
    ),
}


# ---------------------------------------------------------------------------
# Clients spéciaux : grande puissance BT, moyenne et haute tension
# (facturation mensuelle, comptage binôme heures creuses K1 / heures de pointe K2)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TarifSpecial:
    code: str
    libelle: str
    famille: str                # "BT-GP", "MT" ou "HT"
    prix_hc: float              # heures creuses K1 (FCFA/kWh)
    prix_hp: float              # heures de pointe K2 (FCFA/kWh)
    prime_fixe: float           # FCFA par kW souscrit et par mois
    tco_applicable: bool        # taxe communale : grande puissance BT uniquement
    ps_min: float
    ps_max: float


TARIFS_SPECIAUX = {
    "DGP": TarifSpecial(
        "DGP", "Domestique Grande Puissance", "BT-GP",
        86.30, 120.81, 869.21, True, 17.0, 100.0,
    ),
    "PGP": TarifSpecial(
        "PGP", "Professionnel Grande Puissance", "BT-GP",
        103.36, 165.38, 2607.63, True, 17.0, 100.0,
    ),
    "MT-TCU": TarifSpecial(
        "MT-TCU", "Moyenne Tension, Tarif Courte Utilisation", "MT",
        118.51, 183.48, 907.32, False, 100.0, 1250.0,
    ),
    "MT-TG": TarifSpecial(
        "MT-TG", "Moyenne Tension, Tarif Général", "MT",
        85.29, 136.46, 3861.89, False, 100.0, 1250.0,
    ),
    "MT-TLU": TarifSpecial(
        "MT-TLU", "Moyenne Tension, Tarif Longue Utilisation", "MT",
        70.07, 112.12, 9321.26, False, 100.0, 1250.0,
    ),
    "HT-TG": TarifSpecial(
        "HT-TG", "Haute Tension, Tarif Général", "HT",
        55.69, 80.20, 9461.23, False, 1250.0, 100000.0,
    ),
    "HT-TS": TarifSpecial(
        "HT-TS", "Haute Tension, Tarif Secours", "HT",
        74.16, 106.78, 4206.24, False, 1250.0, 100000.0,
    ),
}

# Plages d'heures d'utilisation annuelle de la puissance souscrite qui
# déterminent l'option tarifaire MT recommandée.
PLAGES_UTILISATION_MT = {
    "MT-TCU": (0, 1000),
    "MT-TG": (1000, 4000),
    "MT-TLU": (4000, 8760),
}


# ---------------------------------------------------------------------------
# Facteur de puissance : barèmes de majoration et de minoration
# appliqués au montant de l'énergie (clients spéciaux)
# ---------------------------------------------------------------------------

# (cos phi minimal inclus, taux de majoration)
MAJORATIONS_COS_PHI = (
    (0.75, 0.05),
    (0.70, 0.10),
    (0.65, 0.15),
    (0.60, 0.20),
    (0.55, 0.30),
    (0.50, 0.40),
    (0.45, 0.50),
    (0.40, 0.65),
    (0.00, 0.80),
)

MINORATIONS_COS_PHI = {
    0.96: 0.0075,
    0.97: 0.0150,
    0.98: 0.0225,
    0.99: 0.0300,
    1.00: 0.0375,
}


def taux_application(cos_phi: float) -> float:
    """Taux de majoration (positif) ou de minoration (négatif) du montant
    de l'énergie selon le facteur de puissance.

    Entre 0,80 et 0,95 inclus, aucune application n'est due.
    """
    if cos_phi >= 0.96:
        arrondi = min(round(cos_phi, 2), 1.00)
        return -MINORATIONS_COS_PHI[arrondi]
    if cos_phi >= 0.80:
        return 0.0
    for seuil, taux in MAJORATIONS_COS_PHI:
        if cos_phi >= seuil:
            return taux
    return MAJORATIONS_COS_PHI[-1][1]
