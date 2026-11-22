from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import Categorie

# ISBN : exactement 10 chiffres OU exactement 13 chiffres
MOTIF_ISBN = r"^(\d{10}|\d{13})$"


def verifier_annee(annee: int | None) -> int | None:
    """Refuse une année dans le futur (l'année en cours est recalculée à chaque appel)."""
    annee_en_cours = date.today().year
    if annee is not None and annee > annee_en_cours:
        raise ValueError(f"l'année ne peut pas dépasser {annee_en_cours}")
    return annee


class LivreCreate(BaseModel):
    """Données envoyées pour créer (POST) ou remplacer (PUT) un livre.
    Il n'y a pas de champ id : c'est la base qui le génère."""

    model_config = ConfigDict(
        str_strip_whitespace=True,  # enlève les espaces au début et à la fin
        json_schema_extra={
            "examples": [
                {
                    "titre": "Gouverneurs de la rosée",
                    "auteur": "Jacques Roumain",
                    "annee": 1944,
                    "categorie": "roman",
                    "isbn": "9782253004509",
                    "disponible": True,
                }
            ]
        },
    )

    titre: str = Field(min_length=2, max_length=200, description="Titre (2 à 200 caractères)")
    auteur: str = Field(min_length=2, max_length=200, description="Auteur (2 à 200 caractères)")
    annee: int = Field(ge=1450, description="Année de publication, de 1450 à l'année en cours")
    categorie: Categorie = Field(description="roman, science, histoire, informatique ou autre")
    isbn: str | None = Field(default=None, pattern=MOTIF_ISBN, description="Facultatif : 10 ou 13 chiffres, unique")
    disponible: bool = Field(default=True, description="Vrai si le livre peut être emprunté")

    @field_validator("annee")
    @classmethod
    def annee_pas_dans_le_futur(cls, annee):
        return verifier_annee(annee)


class LivreUpdate(BaseModel):
    """Modification partielle (PATCH) : tous les champs sont facultatifs.
    Seuls les champs envoyés seront modifiés."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={"examples": [{"disponible": False}]},
    )

    titre: str | None = Field(default=None, min_length=2, max_length=200)
    auteur: str | None = Field(default=None, min_length=2, max_length=200)
    annee: int | None = Field(default=None, ge=1450)
    categorie: Categorie | None = None
    isbn: str | None = Field(default=None, pattern=MOTIF_ISBN)
    disponible: bool | None = None

    @field_validator("annee")
    @classmethod
    def annee_pas_dans_le_futur(cls, annee):
        return verifier_annee(annee)

    @field_validator("titre", "auteur", "annee", "categorie", "disponible")
    @classmethod
    def pas_de_null(cls, valeur):
        """On peut omettre un champ, mais pas l'effacer avec null (seul l'ISBN peut être vidé)."""
        if valeur is None:
            raise ValueError("ce champ ne peut pas être null")
        return valeur


class LivreRead(BaseModel):
    """Ce que l'API renvoie au client, avec l'id généré par la base."""

    model_config = ConfigDict(from_attributes=True)  # accepte directement un objet Livre

    id: int
    titre: str
    auteur: str
    annee: int
    categorie: Categorie
    isbn: str | None
    disponible: bool
