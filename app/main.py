from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import charger_livres_depart, creer_tables
from app.routers import livres

# Seule origine autorisée : le frontend servi en local sur le port 5500 (pas d'astérisque).
# 127.0.0.1 et localhost sont deux origines différentes pour le navigateur, on garde les deux.
ORIGINES_FRONTEND = ["http://127.0.0.1:5500", "http://localhost:5500"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Code exécuté au démarrage du serveur (avant yield) et à l'arrêt (après yield)."""
    creer_tables()
    charger_livres_depart()
    yield


app = FastAPI(
    title="API Bibliothèque JC",
    description="API REST du catalogue de la bibliothèque (LOG3550, devoir 2) : "
    "lister, chercher, ajouter, modifier et supprimer des livres enregistrés dans SQLite.",
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Livres", "description": "Gestion du catalogue de livres"},
        {"name": "Santé", "description": "Vérifier que l'API répond"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINES_FRONTEND,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)

app.include_router(livres.router)


@app.get(
    "/sante",
    tags=["Santé"],
    summary="État de l'API",
    description='Renvoie `{"statut": "ok"}` si le serveur fonctionne.',
)
def sante():
    return {"statut": "ok"}
