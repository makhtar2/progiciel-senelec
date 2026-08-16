"""Progiciel d'optimisation de la facture électrique au Sénégal.

Point d'entrée de l'application. Lancement :

    uvicorn main:app --reload
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from web.routes import grille, optimisation, simulation, tableau_bord

app = FastAPI(title="Progiciel d'optimisation de la facture électrique — SENELEC")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(simulation.router)
app.include_router(optimisation.router)
app.include_router(grille.router)
app.include_router(tableau_bord.router)
