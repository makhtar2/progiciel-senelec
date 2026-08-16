"""Routes du tableau de bord des simulations enregistrées."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from moteur import stockage as db

from .. import formatage, graphiques

router = APIRouter()
templates = Jinja2Templates(directory="templates")
templates.env.globals["fmt"] = formatage


def _contexte() -> dict:
    simulations = db.lister()
    graphique = None
    if simulations:
        recentes = list(reversed(simulations))
        graphique = graphiques.historique_simulations(
            [s["horodatage"].replace("T", " ") for s in recentes],
            [s["total_ttc"] for s in recentes],
            [s["libelle"] for s in recentes],
        )
    total = sum(s["total_ttc"] for s in simulations)
    energie = sum(s["energie_kwh"] for s in simulations)
    return {
        "simulations": simulations, "graphique": graphique,
        "total": total, "energie": energie,
        "prix_moyen": (total / energie) if energie else None,
    }


@router.get("/tableau-de-bord", response_class=HTMLResponse)
def afficher(request: Request):
    contexte = {
        "titre": "Tableau de bord",
        "description": (
            "Historique des simulations enregistrées depuis l'écran de "
            "simulation : suivi des montants, de l'énergie facturée et du "
            "prix moyen du kWh."
        ),
        "page": "tableau_bord",
    }
    contexte.update(_contexte())
    return templates.TemplateResponse(request, "tableau_bord.html", contexte)


@router.post("/tableau-de-bord/supprimer/{identifiant}", response_class=HTMLResponse)
def supprimer(request: Request, identifiant: int):
    db.supprimer(identifiant)
    return templates.TemplateResponse(request, "_tableau_bord_contenu.html", _contexte())
