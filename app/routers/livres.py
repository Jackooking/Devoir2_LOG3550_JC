from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, or_, select

from app.database import get_session
from app.models import Categorie, Livre
from app.schemas import LivreCreate, LivreRead, LivreUpdate

router = APIRouter(prefix="/livres", tags=["Livres"])

# Réponses d'erreur affichées dans /docs
ERREUR_404 = {404: {"description": "Aucun livre ne porte cet identifiant"}}
ERREUR_409 = {409: {"description": "Un autre livre a déjà cet ISBN"}}


def trouver_livre(livre_id: int, session: Session) -> Livre:
    """Renvoie le livre, ou lève une erreur 404 s'il n'existe pas."""
    livre = session.get(Livre, livre_id)
    if livre is None:
        raise HTTPException(status_code=404, detail=f"Livre {livre_id} introuvable")
    return livre


def enregistrer(livre: Livre, session: Session) -> Livre:
    """Enregistre le livre. Si la base refuse l'ISBN (index unique), renvoie 409."""
    isbn = livre.isbn  # gardé avant le commit : après un rollback, l'objet est rechargé
    session.add(livre)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()  # annule la transaction ratée
        raise HTTPException(status_code=409, detail=f"Un livre avec l'ISBN {isbn} existe déjà")
    session.refresh(livre)  # relit le livre (id généré, etc.)
    return livre


@router.get(
    "",
    response_model=list[LivreRead],
    summary="Lister les livres",
    description="Renvoie les livres, triés par id. Filtres combinables : recherche `q` dans le titre "
    "ou l'auteur, `categorie` et `disponible`. Pagination avec `skip` et `limit` (100 au maximum).",
)
def lister_livres(
    q: str | None = Query(default=None, description="Texte cherché dans le titre ou l'auteur"),
    categorie: Categorie | None = Query(default=None, description="Garder une seule catégorie"),
    disponible: bool | None = Query(default=None, description="true : disponibles, false : empruntés"),
    skip: int = Query(default=0, ge=0, description="Nombre de livres à sauter"),
    limit: int = Query(default=20, ge=1, le=100, description="Nombre maximal de livres renvoyés"),
    session: Session = Depends(get_session),
):
    requete = select(Livre)
    if q:
        motif = f"%{q}%"
        requete = requete.where(or_(col(Livre.titre).ilike(motif), col(Livre.auteur).ilike(motif)))
    if categorie is not None:
        requete = requete.where(Livre.categorie == categorie)
    if disponible is not None:
        requete = requete.where(Livre.disponible == disponible)
    requete = requete.order_by(Livre.id).offset(skip).limit(limit)
    return session.exec(requete).all()


@router.get(
    "/{livre_id}",
    response_model=LivreRead,
    summary="Lire un livre",
    description="Renvoie le livre dont l'identifiant est donné, ou 404.",
    responses=ERREUR_404,
)
def lire_livre(livre_id: int, session: Session = Depends(get_session)):
    return trouver_livre(livre_id, session)


@router.post(
    "",
    response_model=LivreRead,
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter un livre",
    description="Crée un livre. L'id est généré par la base. Réponse 201 avec l'en-tête "
    "`Location` qui donne l'adresse du nouveau livre. 409 si l'ISBN existe déjà.",
    responses=ERREUR_409,
)
def creer_livre(donnees: LivreCreate, response: Response, session: Session = Depends(get_session)):
    livre = enregistrer(Livre(**donnees.model_dump()), session)
    response.headers["Location"] = f"/livres/{livre.id}"
    return livre


@router.put(
    "/{livre_id}",
    response_model=LivreRead,
    summary="Remplacer un livre",
    description="Remplacement complet : tous les champs doivent être envoyés. "
    "Un champ facultatif omis (isbn, disponible) reprend sa valeur par défaut.",
    responses={**ERREUR_404, **ERREUR_409},
)
def remplacer_livre(livre_id: int, donnees: LivreCreate, session: Session = Depends(get_session)):
    livre = trouver_livre(livre_id, session)
    livre.sqlmodel_update(donnees.model_dump())  # tous les champs
    return enregistrer(livre, session)


@router.patch(
    "/{livre_id}",
    response_model=LivreRead,
    summary="Modifier une partie d'un livre",
    description="Modification partielle : seuls les champs envoyés sont changés.",
    responses={**ERREUR_404, **ERREUR_409},
)
def modifier_livre(livre_id: int, donnees: LivreUpdate, session: Session = Depends(get_session)):
    livre = trouver_livre(livre_id, session)
    livre.sqlmodel_update(donnees.model_dump(exclude_unset=True))  # seulement les champs envoyés
    return enregistrer(livre, session)


@router.delete(
    "/{livre_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un livre",
    description="Supprime le livre. Réponse 204 sans contenu, ou 404 s'il n'existe pas.",
    responses=ERREUR_404,
)
def supprimer_livre(livre_id: int, session: Session = Depends(get_session)):
    livre = trouver_livre(livre_id, session)
    session.delete(livre)
    session.commit()
