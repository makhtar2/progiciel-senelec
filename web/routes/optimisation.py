"""Routes de l'écran d'optimisation tarifaire (quatre onglets)."""

from dataclasses import dataclass

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from moteur import optimisation as opt
from moteur.tarifs import TARIFS_SPECIAUX

from .. import formatage, graphiques

router = APIRouter()
templates = Jinja2Templates(directory="templates")
templates.env.globals["fmt"] = formatage
templates.env.globals["tarifs_sp"] = TARIFS_SPECIAUX


# --------------------------------------------------------------------- BT --

@dataclass
class ParamsBT:
    usage: str
    conso: float
    ps: float


def params_bt(usage: str = Form("domestique"), conso: float = Form(400.0),
              ps: float = Form(0.0)) -> ParamsBT:
    return ParamsBT(usage, conso, ps)


def contexte_bt(p: ParamsBT) -> dict:
    resultats = opt.comparer_bt(p.conso, p.usage, ps_kw=p.ps or None)
    graphique = None
    resultats_affiches = [{**r, "option": f"{r['code']} — {r['mode']}"} for r in resultats]
    if resultats_affiches:
        graphique = graphiques.barres_comparaison(
            resultats_affiches, "Montant toutes taxes du bimestre, par option")
    return {
        "usage": p.usage, "conso": p.conso, "ps": p.ps,
        "resultats": resultats_affiches, "graphique": graphique,
    }


# ------------------------------------------------------------------ MT/HT --

@dataclass
class ParamsMtHt:
    famille: str
    ps: float
    k1: float
    k2: float


def params_mt_ht(famille: str = Form("MT"), ps: float = Form(400.0),
                 k1: float = Form(80000.0), k2: float = Form(15000.0)) -> ParamsMtHt:
    return ParamsMtHt(famille, ps, k1, k2)


def contexte_mt_ht(p: ParamsMtHt) -> dict:
    resultats = opt.comparer_speciaux(p.famille, p.k1, p.k2, p.ps)
    graphique = graphiques.barres_comparaison(resultats, "Montant mensuel toutes taxes, par option")
    recommandee = None
    heures = None
    if p.famille == "MT":
        heures = (p.k1 + p.k2) * 12 / p.ps if p.ps else 0
        recommandee = opt.option_mt_recommandee((p.k1 + p.k2) * 12, p.ps)
    return {
        "famille": p.famille, "ps": p.ps, "k1": p.k1, "k2": p.k2,
        "resultats": resultats, "graphique": graphique,
        "recommandee": recommandee, "heures": heures,
    }


# ----------------------------------------------------------- puissance PS --

@dataclass
class ParamsPS:
    code: str
    saisie: str
    ps_actuelle: float


def params_ps(code: str = Form("PGP"),
             saisie: str = Form("320, 340, 310, 360, 380, 350, 330, 345, 370, 355, 340, 365"),
             ps_actuelle: float = Form(400.0)) -> ParamsPS:
    return ParamsPS(code, saisie, ps_actuelle)


def contexte_ps(p: ParamsPS) -> dict:
    erreur = None
    resultat = None
    economie = None
    try:
        pmax = [float(v.replace(",", ".")) for v in p.saisie.replace(";", ",").split(",") if v.strip()]
    except ValueError:
        pmax = []
        erreur = "Saisie invalide : indiquer des nombres séparés par des virgules."
    if not erreur and not pmax:
        erreur = "Saisir au moins une puissance maximale relevée."
    graphique = None
    if not erreur:
        resultat = opt.ps_optimale(p.code, pmax, ps_max=max(max(pmax), p.ps_actuelle) * 1.2)
        courbe = resultat["courbe"]
        cout_actuel = next((c["cout"] for c in courbe if c["ps"] >= p.ps_actuelle), courbe[-1]["cout"])
        economie = max(cout_actuel - resultat["cout_optimal"], 0)
        graphique = graphiques.courbe_ps_optimale(
            courbe, resultat["ps_optimale"], resultat["cout_optimal"], p.ps_actuelle)
    return {
        "code": p.code, "saisie": p.saisie, "ps_actuelle": p.ps_actuelle,
        "erreur": erreur, "resultat": resultat, "economie": economie,
        "graphique": graphique,
    }


# ------------------------------------------------------- pointe / cos phi --

@dataclass
class ParamsPointe:
    code: str
    ps: float
    k1: float
    k2: float
    reactif: float
    part: int


def params_pointe(code: str = Form("PGP"), ps: float = Form(400.0),
                  k1: float = Form(80000.0), k2: float = Form(15000.0),
                  reactif: float = Form(60000.0), part: int = Form(30)) -> ParamsPointe:
    return ParamsPointe(code, ps, k1, k2, reactif, part)


def contexte_pointe(p: ParamsPointe) -> dict:
    deplacement = opt.deplacement_pointe(p.code, p.k1, p.k2, p.ps, p.part / 100,
                                         energie_reactive=p.reactif)
    correction = opt.correction_cos_phi(p.code, p.k1, p.k2, p.ps, p.reactif)
    return {
        "code": p.code, "ps": p.ps, "k1": p.k1, "k2": p.k2,
        "reactif": p.reactif, "part": p.part,
        "deplacement": deplacement, "correction": correction,
    }


# --------------------------------------------------------------- routage --

_CONTEXTES = {
    "bt": (contexte_bt, params_bt, "_optimisation_bt.html"),
    "mt-ht": (contexte_mt_ht, params_mt_ht, "_optimisation_mt_ht.html"),
    "ps": (contexte_ps, params_ps, "_optimisation_ps.html"),
    "pointe": (contexte_pointe, params_pointe, "_optimisation_pointe.html"),
}


@router.get("/optimisation", response_class=HTMLResponse)
def afficher(request: Request, onglet: str = "bt"):
    contexte = {
        "titre": "Optimisation tarifaire",
        "description": (
            "Quatre leviers pour réduire la facture à consommation de "
            "service égale : le choix de l'option tarifaire, le "
            "dimensionnement de la puissance souscrite, le placement "
            "horaire de la consommation et la tenue du facteur de puissance."
        ),
        "page": "optimisation",
        "onglet": onglet,
    }
    contexte.update(_defaut(onglet))
    return templates.TemplateResponse(request, "optimisation.html", contexte)


def _defaut(onglet: str) -> dict:
    if onglet == "bt":
        return contexte_bt(ParamsBT("domestique", 400.0, 0.0))
    if onglet == "mt-ht":
        return contexte_mt_ht(ParamsMtHt("MT", 400.0, 80000.0, 15000.0))
    if onglet == "ps":
        return contexte_ps(ParamsPS(
            "PGP", "320, 340, 310, 360, 380, 350, 330, 345, 370, 355, 340, 365", 400.0))
    return contexte_pointe(ParamsPointe("PGP", 400.0, 80000.0, 15000.0, 60000.0, 30))


@router.get("/optimisation/{onglet}", response_class=HTMLResponse)
def onglet_defaut(request: Request, onglet: str):
    _, _, gabarit = _CONTEXTES[onglet]
    contexte = {"onglet": onglet}
    contexte.update(_defaut(onglet))
    return templates.TemplateResponse(request, gabarit, contexte)


@router.post("/optimisation/bt/calculer", response_class=HTMLResponse)
def calculer_bt(request: Request, p: ParamsBT = Depends(params_bt)):
    return templates.TemplateResponse(request, "_optimisation_bt_resultats.html", contexte_bt(p))


@router.post("/optimisation/mt-ht/calculer", response_class=HTMLResponse)
def calculer_mt_ht(request: Request, p: ParamsMtHt = Depends(params_mt_ht)):
    return templates.TemplateResponse(request, "_optimisation_mt_ht_resultats.html", contexte_mt_ht(p))


@router.post("/optimisation/ps/calculer", response_class=HTMLResponse)
def calculer_ps(request: Request, p: ParamsPS = Depends(params_ps)):
    return templates.TemplateResponse(request, "_optimisation_ps_resultats.html", contexte_ps(p))


@router.post("/optimisation/pointe/calculer", response_class=HTMLResponse)
def calculer_pointe(request: Request, p: ParamsPointe = Depends(params_pointe)):
    return templates.TemplateResponse(request, "_optimisation_pointe_resultats.html", contexte_pointe(p))
