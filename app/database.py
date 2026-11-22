from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Livre

# Fichier SQLite créé dans le dossier du projet (ignoré par Git)
DATABASE_URL = "sqlite:///./bibliotheque.db"

# Le moteur gère la connexion à la base.
# check_same_thread=False : FastAPI peut utiliser la connexion depuis plusieurs fils d'exécution.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def creer_tables():
    """Crée les tables (si elles n'existent pas encore) à partir des modèles SQLModel."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Dépendance FastAPI : ouvre une session pour une requête, puis la ferme."""
    with Session(engine) as session:
        yield session


# Livres de départ (ceux du devoir 1 ; « L'Art de la guerre », année 500, est retiré
# car il ne respecte pas la règle année >= 1450)
LIVRES_DEPART = [
    {"titre": "Gouverneurs de la rosée", "auteur": "Jacques Roumain", "annee": 1944, "categorie": "roman", "disponible": True},
    {"titre": "L'Espace d'un cillement", "auteur": "Jacques Stephen Alexis", "annee": 1959, "categorie": "roman", "disponible": True},
    {"titre": "Une tempête", "auteur": "Aimé Césaire", "annee": 1969, "categorie": "autre", "disponible": True},
    {"titre": "Clean Code", "auteur": "Robert C. Martin", "annee": 2008, "categorie": "informatique", "disponible": False},
    {"titre": "Une brève histoire du temps", "auteur": "Stephen Hawking", "annee": 1988, "categorie": "science", "disponible": True},
    {"titre": "Le Plaidoyer pour les Indiens", "auteur": "Bartolomé de Las Casas", "annee": 1552, "categorie": "histoire", "disponible": True},
    {"titre": "JavaScript: The Good Parts", "auteur": "Douglas Crockford", "annee": 2008, "categorie": "informatique", "disponible": False},
    {"titre": "Cosmos", "auteur": "Carl Sagan", "annee": 1980, "categorie": "science", "disponible": True},
]


def charger_livres_depart():
    """Ajoute les livres de départ seulement si la table est vide."""
    with Session(engine) as session:
        deja_un_livre = session.exec(select(Livre)).first()
        if deja_un_livre is None:
            session.add_all([Livre(**donnees) for donnees in LIVRES_DEPART])
            session.commit()
