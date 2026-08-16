"""Route de l'écran de consultation de la grille tarifaire."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from moteur import tarifs
from moteur.tarifs import TARIFS_BT, TARIFS_SPECIAUX

from .. import formatage

router = APIRouter()
templates = Jinja2Templates(directory="templates")
templates.env.globals["fmt"] = formatage


@router.get("/grille", response_class=HTMLResponse)
def afficher(request: Request):
    return templates.TemplateResponse(request, "grille.html", {
        "titre": "Grille tarifaire",
        "description": (
            "Grille officielle hors taxes reproduite dans le mémoire. Les "
            "valeurs sont centralisées dans le module « moteur/tarifs.py » : "
            "une mise à jour de la grille ne demande de modifier que ce "
            "fichier."
        ),
        "page": "grille",
        "tarifs_bt": TARIFS_BT,
        "tarifs_sp": TARIFS_SPECIAUX,
        "majorations": tarifs.MAJORATIONS_COS_PHI,
        "minorations": tarifs.MINORATIONS_COS_PHI,
        "tarifs": tarifs,
    })
