"""Routes de l'écran de simulation de facture."""

from dataclasses import dataclass
from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from moteur import facturation
from moteur import stockage as db
from moteur.tarifs import TARIFS_BT, TARIFS_SPECIAUX

from .. import export_pdf, formatage, graphiques

router = APIRouter()
templates = Jinja2Templates(directory="templates")
templates.env.globals["fmt"] = formatage


@dataclass
class ParamsSimulation:
    segment: str
    code_bt: str
    conso: float
    mode: str
    code_sp: str
    ps: float
    pmax: float
    k1: float
    k2: float
    mesure_reactif: bool
    reactif: float


def params_simulation(
    segment: str = Form("bt"),
    code_bt: str = Form("DPP"),
    conso: float = Form(300.0),
    mode: str = Form("postpaye"),
    code_sp: str = Form("DGP"),
    ps: float = Form(250.0),
    pmax: float = Form(0.0),
    k1: float = Form(40000.0),
    k2: float = Form(8000.0),
    mesure_reactif: str | None = Form(None),
    reactif: float = Form(0.0),
) -> ParamsSimulation:
    return ParamsSimulation(segment, code_bt, conso, mode, code_sp, ps, pmax,
                            k1, k2, mesure_reactif is not None, reactif)


def facture_depuis_params(p: ParamsSimulation) -> facturation.Facture:
    if p.segment == "bt":
        return facturation.facture_bt(p.code_bt, p.conso, woyofal=(p.mode == "woyofal"))
    return facturation.facture_speciale(
        p.code_sp, p.k1, p.k2, p.ps, pmax_kw=p.pmax or None,
        energie_reactive=p.reactif if p.mesure_reactif else None,
    )


def _contexte(p: ParamsSimulation, request: Request | None = None) -> dict:
    facture = facture_depuis_params(p)
    graphique_secondaire = (
        graphiques.tranches_bt(p.code_bt, p.conso) if p.segment == "bt" else None
    )
    contexte = {
        "titre": "Simulation de facture",
        "description": (
            "Reconstitution du calcul de la facture SENELEC à partir de la "
            "grille tarifaire en vigueur : tranches de consommation en basse "
            "tension, prime fixe et comptage binôme pour les clients spéciaux."
        ),
        "page": "simulation",
        "tarifs_bt": TARIFS_BT,
        "tarifs_sp": TARIFS_SPECIAUX,
        "facture": facture,
        "graphique_composition": graphiques.composition_facture(facture),
        "graphique_secondaire": graphique_secondaire,
        "segment": p.segment, "code_bt": p.code_bt, "conso": p.conso,
        "mode": p.mode, "code_sp": p.code_sp, "ps": p.ps, "pmax": p.pmax,
        "k1": p.k1, "k2": p.k2, "mesure_reactif": p.mesure_reactif,
        "reactif": p.reactif,
    }
    if request is not None:
        contexte["request"] = request
    return contexte


@router.get("/", response_class=HTMLResponse)
def afficher(request: Request):
    p = ParamsSimulation("bt", "DPP", 300.0, "postpaye", "DGP", 250.0, 0.0,
                         40000.0, 8000.0, False, 0.0)
    return templates.TemplateResponse(request, "simulation.html", _contexte(p, request))


@router.post("/simulation/calculer", response_class=HTMLResponse)
def calculer(request: Request, p: ParamsSimulation = Depends(params_simulation)):
    return templates.TemplateResponse(request, "_simulation_resultats.html", _contexte(p, request))


@router.post("/simulation/enregistrer", response_class=HTMLResponse)
def enregistrer(p: ParamsSimulation = Depends(params_simulation)):
    facture = facture_depuis_params(p)
    db.enregistrer(facture)
    return HTMLResponse(
        '<span class="avis avis--succes">Simulation enregistrée. '
        "Elle est visible dans le tableau de bord.</span>"
    )


@router.post("/simulation/pdf")
def telecharger_pdf(p: ParamsSimulation = Depends(params_simulation)):
    facture = facture_depuis_params(p)
    contenu = export_pdf.facture_pdf_bytes(facture)
    nom = f"facture_{facture.code_tarif}_{datetime.now():%Y%m%d_%H%M}.pdf"
    return Response(
        content=contenu, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nom}"'},
    )
