# Bibliothèque Numérique JC – LOG3550 Devoir 2 (backend FastAPI)

Dépôt Git : https://github.com/Jackooking/Devoir2_LOG3550_JC

## Description

API REST qui gère le catalogue de la bibliothèque du devoir 1 : elle valide les livres, les enregistre dans une base SQLite et se teste automatiquement avec pytest.
Le frontend du devoir 1 (dossier `frontend/`) lit, ajoute et supprime maintenant les livres par cette API avec `fetch`, au lieu de `localStorage`.

Un livre a : `id` (généré par la base), `titre`, `auteur`, `annee`, `categorie` (roman, science, histoire, informatique ou autre), `isbn` (facultatif, unique) et `disponible` (vrai par défaut).

## Structure du projet

```
app/__init__.py
app/main.py            application FastAPI, CORS, routeurs, démarrage (tables + livres de départ)
app/database.py        moteur SQLite, session (dépendance), livres de départ
app/models.py          table Livre (SQLModel) et Enum Categorie
app/schemas.py         schémas Pydantic LivreCreate, LivreUpdate, LivreRead et règles de validation
app/routers/livres.py  points d'accès /livres (CRUD, filtres, pagination, erreurs)
tests/test_livres.py   21 tests pytest sur une base SQLite en mémoire
frontend/              frontend du devoir 1 relié à l'API
requirements.txt       paquets Python (pip freeze)
```

## Installation

Prérequis : Python 3.10 ou plus et Git.

```powershell
git clone https://github.com/Jackooking/Devoir2_LOG3550_JC.git
cd Devoir2_LOG3550_JC
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Lancer l'API

```powershell
uvicorn app.main:app --reload
```

- API : http://127.0.0.1:8000
- Documentation interactive (Swagger) : http://127.0.0.1:8000/docs

Au premier démarrage, la table est créée dans `bibliotheque.db` et 8 livres de départ sont ajoutés (seulement si la table est vide). Ce fichier n'est pas dans le dépôt (`.gitignore`).

## Lancer le frontend

L'API n'accepte que l'origine `http://127.0.0.1:5500` (ou `http://localhost:5500`). Il faut donc servir le dossier `frontend/` sur le port 5500, par exemple :

- avec l'extension **Live Server** de VS Code : clic droit sur `frontend/index.html` → « Open with Live Server » ;
- ou en ligne de commande : `python -m http.server 5500 --directory frontend`, puis ouvrir http://127.0.0.1:5500.

L'API doit être lancée en même temps. Si elle est arrêtée, la page affiche un message d'erreur.

## Lancer les tests

```powershell
pytest -v
```

Les tests utilisent une base SQLite **en mémoire**, neuve pour chaque test : la vraie base n'est jamais modifiée.

## Points d'accès

| Méthode | Chemin | Rôle | Codes |
|---|---|---|---|
| GET | `/livres` | Liste ; filtres `q` (titre ou auteur), `categorie`, `disponible` ; pagination `skip`, `limit` (100 max.) | 200, 422 |
| GET | `/livres/{id}` | Lire un livre | 200, 404 |
| POST | `/livres` | Ajouter un livre (en-tête `Location`) | 201, 409, 422 |
| PUT | `/livres/{id}` | Remplacer un livre (tous les champs) | 200, 404, 409, 422 |
| PATCH | `/livres/{id}` | Modifier seulement les champs envoyés | 200, 404, 409, 422 |
| DELETE | `/livres/{id}` | Supprimer un livre | 204, 404 |
| GET | `/sante` | Renvoie `{"statut": "ok"}` | 200 |

Règles de validation : titre et auteur de 2 à 200 caractères ; année de 1450 à l'année en cours ; catégorie parmi la liste ; ISBN de 10 ou 13 chiffres s'il est présent. Un `id` envoyé par le client est ignoré.

## Choix de conception

- **Trois schémas** : `LivreCreate` (POST et PUT, sans `id`), `LivreUpdate` (PATCH, tous les champs facultatifs, mais `null` refusé sauf pour l'ISBN) et `LivreRead` (réponses, avec l'`id`).
- **Année maximale calculée à chaque requête** dans un `field_validator`, au lieu d'écrire 2026 en dur.
- **ISBN unique garanti par la base** (index unique) : une `IntegrityError` est transformée en 409.
- **Session par `Depends(get_session)`** : ouverte pour chaque requête et fermée à la fin grâce au `with` et au `yield`. Les tests remplacent cette dépendance par une base en mémoire (`dependency_overrides`).
- **Livres de départ** : ceux du devoir 1, sauf « L'Art de la guerre » (année 500), refusé par la règle année ≥ 1450.
- **Frontend** : la recherche, les filtres et le tri restent faits dans le navigateur (la recherche ignore toujours les accents) ; seules les données viennent de l'API. Le bouton « Réinitialiser » du devoir 1 a été retiré, car les livres de départ sont maintenant gérés par le serveur.

## Réponses aux questions

### 1. Rôle de FastAPI, d'Uvicorn et de Pydantic ; pourquoi séparer modèle et schémas

FastAPI est le framework : il associe chaque URL et méthode HTTP à une fonction Python et génère la documentation `/docs`.
Uvicorn est le serveur ASGI : il écoute sur le port 8000, reçoit les requêtes HTTP et les transmet à l'application FastAPI.
Pydantic valide et convertit les données : il vérifie le JSON reçu selon les types et les règles des schémas et renvoie une erreur 422 sinon.
On sépare le modèle de base de données (la forme de la table) des schémas d'échange (ce que le client peut envoyer et ce qu'on lui renvoie)
pour que le client ne puisse pas, par exemple, choisir l'`id`, et pour pouvoir changer la table sans changer l'API, ou l'inverse.

### 2. Format d'une erreur 422

Quand les données ne respectent pas les règles, FastAPI renvoie le code 422 avec un objet JSON `detail` qui est une **liste** : une entrée par erreur. Exemple pour un titre trop court et une année future :

```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "titre"],
      "msg": "String should have at least 2 characters",
      "input": "A",
      "ctx": {"min_length": 2}
    },
    {
      "type": "value_error",
      "loc": ["body", "annee"],
      "msg": "Value error, l'année ne peut pas dépasser 2026",
      "input": 2099,
      "ctx": {"error": {}}
    }
  ]
}
```

- `type` : le genre d'erreur ;
- `loc` : où elle se trouve (`body` = le corps JSON, puis le nom du champ ; `query` pour un paramètre d'URL comme `limit`) ;
- `msg` : le message lisible (en anglais pour les règles automatiques de Pydantic, en français pour mes propres validateurs) ;
- `input` : la valeur reçue ;
- `ctx` : des détails sur la règle (par exemple la longueur minimale).

Les autres erreurs (404, 409) ont un `detail` qui est un simple texte, par exemple `{"detail": "Livre 42 introuvable"}`.

### 3. PUT ou PATCH ; idempotence

PUT remplace la ressource au complet : on envoie tous les champs, et un champ facultatif omis reprend sa valeur par défaut.
PATCH modifie seulement les champs envoyés ; les autres ne changent pas.
Une requête est idempotente si l'envoyer une ou plusieurs fois laisse le serveur dans le même état.
PUT l'est, car remettre deux fois les mêmes valeurs donne le même livre ; DELETE aussi, car après la première suppression le livre n'existe plus et le renvoyer ne change rien (on reçoit 404, mais l'état est le même).
POST ne l'est pas : chaque envoi crée un nouveau livre avec un nouvel `id`.

## Difficultés rencontrées

- Pour `requirements.txt` : la commande `pip freeze > requirements.txt` dans PowerShell avait créé le fichier en UTF-16, que certains outils lisent mal. Je l'ai régénéré en UTF-8.
- Pour l'erreur 409 : quand un PATCH mettait un ISBN déjà utilisé, le message affichait « l'ISBN None ». Après le `rollback`, SQLAlchemy recharge le livre depuis la base, donc `livre.isbn` n'avait plus la valeur envoyée. J'ai gardé l'ISBN dans une variable avant le `commit`.
- Pour les captures des erreurs 422 : au début, je ne trouvais pas `POST /livres` dans Swagger. Il fallait ouvrir exactement `http://127.0.0.1:8000/docs`, puis cliquer sur la barre verte et sur « Try it out ».
- Pour la capture de l'onglet Réseau : j'ouvrais d'abord les outils sur la page de l'API au lieu de mon frontend (port 5500). Ensuite, je voyais 200 au lieu de 201, parce que je cliquais sur la requête GET ou OPTIONS (la vérification CORS) au lieu de la requête POST.

## Captures

Les captures sont regroupées dans le document Word `Captures_devoir2_Jackensly.docx`, joint dans l'archive ZIP :

1. page `/docs` (Swagger) avec tous les points d'accès
2. réponse 422 (titre trop court)
3. réponse 422 (année hors limites)
4. `pytest -v`, tous les tests au vert
5. catalogue alimenté par l'API
6. requête POST dans l'onglet Réseau du navigateur

## Sources et outils d'assistance

- **Claude (assistant d'IA d'Anthropic)** : utilisé pour m'expliquer les notions (FastAPI, Pydantic, SQLModel, `Depends`, CORS, pytest, `fetch` avec `async`/`await`), me guider étape par étape, écrire et tester le code avec moi et m'en expliquer chaque partie, et rédiger une première version de ce README, que j'ai relue.
- [Documentation de FastAPI](https://fastapi.tiangolo.com/) : tutoriel, SQL databases, testing, CORS.
- [Documentation de SQLModel](https://sqlmodel.tiangolo.com/) et [de Pydantic](https://docs.pydantic.dev/).
- [MDN Web Docs](https://developer.mozilla.org/fr/) : `fetch`, `async`/`await`, CORS.
