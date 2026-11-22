from sqlmodel import Session, SQLModel, create_engine

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
