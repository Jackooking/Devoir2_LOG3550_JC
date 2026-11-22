from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.database import get_session
from app.main import app

LIVRE = {
    "titre": "Gouverneurs de la rosée",
    "auteur": "Jacques Roumain",
    "annee": 1944,
    "categorie": "roman",
    "isbn": "1234567890",
}


@pytest.fixture
def client():
    """Chaque test reçoit une base SQLite neuve, en mémoire : la vraie base n'est jamais touchée."""
    moteur = create_engine(
        "sqlite://",  # en mémoire
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # une seule connexion partagée, sinon chaque connexion aurait sa propre base vide
    )
    SQLModel.metadata.create_all(moteur)

    def get_session_test():
        with Session(moteur) as session:
            yield session

    # Les routes utiliseront la base de test à la place de la vraie
    app.dependency_overrides[get_session] = get_session_test
    yield TestClient(app)  # sans « with » : le lifespan (vraie base, livres de départ) ne s'exécute pas
    app.dependency_overrides.clear()


def creer(client, **changements):
    """Crée un livre (LIVRE modifié par les changements donnés) et renvoie la réponse."""
    return client.post("/livres", json={**LIVRE, **changements})


# --- Santé -------------------------------------------------------------------

def test_sante(client):
    reponse = client.get("/sante")
    assert reponse.status_code == 200
    assert reponse.json() == {"statut": "ok"}


# --- Création ----------------------------------------------------------------

def test_creer_livre(client):
    reponse = creer(client)
    assert reponse.status_code == 201
    livre = reponse.json()
    assert livre["id"] == 1
    assert livre["titre"] == "Gouverneurs de la rosée"
    assert livre["disponible"] is True  # valeur par défaut
    assert reponse.headers["location"] == "/livres/1"


def test_creer_ignore_id_du_client(client):
    reponse = creer(client, id=999)
    assert reponse.status_code == 201
    assert reponse.json()["id"] == 1  # l'id vient de la base, pas du client


# --- Lecture -----------------------------------------------------------------

def test_lire_livre(client):
    creer(client)
    reponse = client.get("/livres/1")
    assert reponse.status_code == 200
    assert reponse.json()["auteur"] == "Jacques Roumain"


def test_lire_livre_absent_404(client):
    reponse = client.get("/livres/42")
    assert reponse.status_code == 404
    assert reponse.json() == {"detail": "Livre 42 introuvable"}


# --- Liste filtrée et pagination ---------------------------------------------

def test_liste_filtree(client):
    creer(client)
    creer(client, titre="Cosmos", auteur="Carl Sagan", annee=1980, categorie="science", isbn=None)
    creer(client, titre="Clean Code", auteur="Robert C. Martin", annee=2008,
          categorie="informatique", isbn=None, disponible=False)

    assert len(client.get("/livres").json()) == 3

    par_auteur = client.get("/livres", params={"q": "sagan"}).json()  # majuscules ignorées
    assert [l["titre"] for l in par_auteur] == ["Cosmos"]

    par_categorie = client.get("/livres", params={"categorie": "informatique"}).json()
    assert [l["titre"] for l in par_categorie] == ["Clean Code"]

    empruntes = client.get("/livres", params={"disponible": False}).json()
    assert [l["titre"] for l in empruntes] == ["Clean Code"]

    combines = client.get("/livres", params={"q": "co", "disponible": True}).json()
    assert [l["titre"] for l in combines] == ["Cosmos"]


def test_pagination(client):
    for numero in range(5):
        creer(client, titre=f"Livre {numero}", isbn=None)
    page = client.get("/livres", params={"skip": 2, "limit": 2}).json()
    assert [l["titre"] for l in page] == ["Livre 2", "Livre 3"]
    assert client.get("/livres", params={"limit": 101}).status_code == 422  # maximum 100


# --- Mise à jour -------------------------------------------------------------

def test_remplacer_livre_put(client):
    creer(client)
    nouveau = {"titre": "Bois d'ébène", "auteur": "Jacques Roumain", "annee": 1945, "categorie": "autre"}
    reponse = client.put("/livres/1", json=nouveau)
    assert reponse.status_code == 200
    livre = reponse.json()
    assert livre["titre"] == "Bois d'ébène"
    assert livre["isbn"] is None  # remplacement complet : l'ISBN non envoyé est effacé


def test_modifier_livre_patch(client):
    creer(client)
    reponse = client.patch("/livres/1", json={"disponible": False})
    assert reponse.status_code == 200
    livre = reponse.json()
    assert livre["disponible"] is False
    assert livre["titre"] == LIVRE["titre"]  # les autres champs ne changent pas
    assert livre["isbn"] == LIVRE["isbn"]


def test_modifier_livre_absent_404(client):
    assert client.patch("/livres/42", json={"disponible": False}).status_code == 404
    assert client.put("/livres/42", json=LIVRE).status_code == 404


# --- Suppression -------------------------------------------------------------

def test_supprimer_livre(client):
    creer(client)
    reponse = client.delete("/livres/1")
    assert reponse.status_code == 204
    assert reponse.content == b""
    assert client.get("/livres/1").status_code == 404
    assert client.delete("/livres/1").status_code == 404


# --- Validation (422) --------------------------------------------------------

@pytest.mark.parametrize(
    "champ, valeur",
    [
        ("titre", "A"),                      # moins de 2 caractères
        ("auteur", "x" * 201),               # plus de 200 caractères
        ("annee", 1400),                     # avant 1450
        ("annee", date.today().year + 1),    # dans le futur
        ("categorie", "bande dessinée"),     # pas dans la liste
        ("isbn", "12345"),                   # ni 10 ni 13 chiffres
        ("isbn", "123456789X"),              # pas seulement des chiffres
    ],
    ids=["titre-trop-court", "auteur-trop-long", "annee-avant-1450", "annee-future",
         "categorie-inconnue", "isbn-5-chiffres", "isbn-avec-lettre"],
)
def test_creer_livre_invalide_422(client, champ, valeur):
    reponse = creer(client, **{champ: valeur})
    assert reponse.status_code == 422
    erreur = reponse.json()["detail"][0]
    assert erreur["loc"] == ["body", champ]  # l'erreur indique le champ fautif


def test_patch_null_refuse_422(client):
    creer(client)
    assert client.patch("/livres/1", json={"titre": None}).status_code == 422


# --- ISBN en double (409) ----------------------------------------------------

def test_isbn_en_double_409(client):
    creer(client)
    reponse = creer(client, titre="Un autre livre")
    assert reponse.status_code == 409
    assert "1234567890" in reponse.json()["detail"]


def test_patch_isbn_en_double_409(client):
    creer(client)
    creer(client, titre="Cosmos", isbn="9876543210")
    reponse = client.patch("/livres/2", json={"isbn": "1234567890"})
    assert reponse.status_code == 409
    assert client.get("/livres/2").json()["isbn"] == "9876543210"  # rien n'a changé
