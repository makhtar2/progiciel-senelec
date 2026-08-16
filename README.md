# Progiciel d'optimisation de la facture électrique au Sénégal

Application web de simulation et d'optimisation de la facture d'électricité
SENELEC, développée dans le cadre du mémoire de Master II « Mise en place d'un
progiciel d'optimisation de la facture électrique au Sénégal » (École
Polytechnique de Thiès, Master interuniversitaire en énergies renouvelables et
efficacité énergétique).

## Fonctionnalités

- **Simulation de facture** : reconstitution du calcul de la facture pour
  toutes les catégories de clients — basse tension par tranches (DPP, DMP,
  PPP, PMP, en postpayé ou en prépaiement Woyofal) et clients spéciaux (DGP,
  PGP, moyenne et haute tension) avec prime fixe, comptage binôme heures
  creuses / heures de pointe, application liée au facteur de puissance et
  pénalités de dépassement de puissance.
- **Optimisation tarifaire** : comparaison des options ouvertes au client,
  recherche de la puissance souscrite optimale, simulation du déplacement de
  consommation hors pointe et de la compensation d'énergie réactive, avec
  chiffrage des économies en francs CFA.
- **Grille tarifaire** : consultation des tarifs, barèmes et taxes utilisés
  par le moteur de calcul.
- **Tableau de bord** : historique des simulations enregistrées (base SQLite
  embarquée).

## Installation et lancement

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

L'application s'ouvre dans le navigateur à l'adresse http://localhost:8501.

## Structure du projet

```
progiciel-senelec/
├── app.py                   Point d'entrée et navigation
├── moteur/
│   ├── tarifs.py            Grille tarifaire (seul fichier à modifier
│   │                        lors d'une révision des tarifs)
│   ├── facturation.py       Moteur de calcul des factures
│   ├── optimisation.py      Leviers d'optimisation et comparaisons
│   └── stockage.py          Persistance SQLite des simulations
├── vues/
│   ├── simulation.py        Écran de simulation de facture
│   ├── optimisation.py      Écran d'optimisation tarifaire
│   ├── grille.py            Écran de consultation de la grille
│   ├── tableau_bord.py      Tableau de bord
│   └── theme.py             Charte graphique commune
└── data/                    Base de données locale (créée au premier
                             enregistrement)
```

## Hypothèses de calcul

Les valeurs tarifaires proviennent de la grille officielle reproduite dans le
mémoire (grille hors taxes 2017). Deux paramètres ne figurent pas dans la
grille publiée et sont posés comme hypothèses ajustables dans
`moteur/tarifs.py` :

- le montant de la redevance fixe par facture (`REDEVANCE_BT`,
  `REDEVANCE_SPECIAUX`) ;
- le coefficient appliqué au taux de prime fixe pour facturer le dépassement
  de puissance souscrite (`COEF_DEPASSEMENT_PS`).

Les tests du moteur de calcul se lancent avec :

```bash
python3 -m pytest tests
```
