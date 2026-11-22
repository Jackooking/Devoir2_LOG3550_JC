from enum import Enum

from sqlmodel import Field, SQLModel


class Categorie(str, Enum):
    """Catégories permises pour un livre."""

    roman = "roman"
    science = "science"
    histoire = "histoire"
    informatique = "informatique"
    autre = "autre"


class Livre(SQLModel, table=True):
    """Table « livre » dans la base SQLite."""

    id: int | None = Field(default=None, primary_key=True)
    titre: str = Field(max_length=200, index=True)
    auteur: str = Field(max_length=200, index=True)
    annee: int
    categorie: Categorie
    # unique=True : la base elle-même refuse deux fois le même ISBN (index unique)
    isbn: str | None = Field(default=None, unique=True, index=True)
    disponible: bool = Field(default=True)
