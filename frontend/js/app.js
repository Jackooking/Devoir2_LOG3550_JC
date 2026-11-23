// Adresse de l'API FastAPI (lancée avec : uvicorn app.main:app --reload)
const API_URL = "http://127.0.0.1:8000";

const MESSAGE_API_ARRETEE =
  "Impossible de joindre l'API. Vérifiez que le serveur est lancé (uvicorn app.main:app --reload).";

// Livres reçus de l'API (la recherche, les filtres et le tri se font sur cette liste)
let livres = [];

// --- Messages d'état (chargement, erreurs) ---------------------------------

function afficherEtat(message, estErreur) {
  const etat = document.querySelector("#message-etat");
  etat.textContent = message;
  etat.classList.toggle("erreur", estErreur);
}

// Transforme la réponse d'erreur de l'API en texte lisible
async function lireMessageErreur(reponse) {
  try {
    const corps = await reponse.json();
    if (typeof corps.detail === "string") {
      return corps.detail; // 404 ou 409 : {"detail": "message"}
    }
    // 422 : {"detail": [{"loc": [...], "msg": "..."}, ...]}
    return corps.detail
      .map(function (erreur) {
        return erreur.loc[erreur.loc.length - 1] + " : " + erreur.msg;
      })
      .join(" ; ");
  } catch {
    return "Erreur " + reponse.status;
  }
}

// fetch lève une TypeError quand le serveur ne répond pas du tout (API arrêtée)
function texteErreur(erreur) {
  return erreur instanceof TypeError ? MESSAGE_API_ARRETEE : erreur.message;
}

// --- Appels à l'API ---------------------------------------------------------

async function chargerLivres() {
  afficherEtat("Chargement des livres…", false);
  try {
    const reponse = await fetch(API_URL + "/livres?limit=100");
    if (!reponse.ok) {
      throw new Error(await lireMessageErreur(reponse));
    }
    livres = await reponse.json();
    afficherEtat("", false);
    actualiserAffichage();
  } catch (erreur) {
    afficherEtat(texteErreur(erreur), true);
  }
}

async function supprimerLivre(id) {
  if (!confirm("Voulez-vous vraiment supprimer ce livre ?")) {
    return;
  }
  try {
    const reponse = await fetch(API_URL + "/livres/" + id, { method: "DELETE" });
    if (!reponse.ok) {
      throw new Error(await lireMessageErreur(reponse));
    }
    livres = livres.filter(function (livre) {
      return livre.id !== id;
    });
    afficherEtat("", false);
    actualiserAffichage();
  } catch (erreur) {
    afficherEtat(texteErreur(erreur), true);
  }
}

async function ajouterLivre(evenement) {
  evenement.preventDefault();
  const formulaire = evenement.target;
  const bouton = formulaire.querySelector("button[type=submit]");
  afficherErreur("api", "");

  if (!validerFormulaire()) {
    return;
  }

  bouton.disabled = true; // évite un double envoi pendant la requête
  bouton.textContent = "Ajout en cours…";
  try {
    const reponse = await fetch(API_URL + "/livres", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(lireFormulaire()),
    });
    if (!reponse.ok) {
      throw new Error(await lireMessageErreur(reponse)); // par exemple 409 ou 422
    }
    const nouveauLivre = await reponse.json(); // le livre avec l'id donné par la base
    livres.push(nouveauLivre);
    formulaire.reset();
    actualiserAffichage();
  } catch (erreur) {
    afficherErreur("api", texteErreur(erreur));
  } finally {
    bouton.disabled = false;
    bouton.textContent = "Ajouter";
  }
}

// --- Affichage --------------------------------------------------------------

function creerCarteLivre(livre) {
  const carte = document.createElement("article");

  const titre = document.createElement("h3");
  titre.textContent = livre.titre;

  const auteur = document.createElement("p");
  auteur.textContent = "Auteur : " + livre.auteur;

  const annee = document.createElement("p");
  annee.textContent = "Année : " + livre.annee;

  const categorie = document.createElement("p");
  categorie.textContent = "Catégorie : " + livre.categorie;

  const etat = document.createElement("span");
  if (livre.disponible) {
    etat.textContent = "Disponible";
    etat.classList.add("etiquette-disponible");
  } else {
    etat.textContent = "Emprunté";
    etat.classList.add("etiquette-empruntee");
  }
  const boutonSupprimer = document.createElement("button");
  boutonSupprimer.type = "button";
  boutonSupprimer.textContent = "Supprimer";
  boutonSupprimer.addEventListener("click", function () {
    supprimerLivre(livre.id);
  });
  carte.append(titre, auteur, annee, categorie, etat, boutonSupprimer);
  return carte;
}

function afficherLivres(livres) {
  const liste = document.querySelector("#liste-livres");
  liste.replaceChildren();

  livres.forEach(function (livre) {
    liste.append(creerCarteLivre(livre));
  });
}

// Enlève les accents et les majuscules pour comparer les textes
function normaliser(texte) {
  return texte.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

function filtrerLivres(livres) {
  const recherche = normaliser(document.querySelector("#recherche").value);
  const categorie = document.querySelector("#filtre-categorie").value;
  const disponiblesSeulement = document.querySelector("#filtre-disponibles").checked;
  return livres.filter(function (livre) {
    const trouveDansTitre = normaliser(livre.titre).includes(recherche);
    const trouveDansAuteur = normaliser(livre.auteur).includes(recherche);
    const correspondACategorie = categorie ? livre.categorie === categorie : true;
    const estDisponible = disponiblesSeulement ? livre.disponible : true;
    return (trouveDansTitre || trouveDansAuteur) && correspondACategorie && estDisponible;
  });
}

function trierLivres(livres) {
  const tri = document.querySelector("#tri").value;
  const copie = [...livres];

  copie.sort(function (a, b) {
    if (tri === "titre-asc") return a.titre.localeCompare(b.titre, "fr");
    if (tri === "titre-desc") return b.titre.localeCompare(a.titre, "fr");
    if (tri === "annee-asc") return a.annee - b.annee;
    return b.annee - a.annee;
  });

  return copie;
}

function afficherResultats(nombre) {
  const compteur = document.querySelector("#nombre-resultats");
  const messageVide = document.querySelector("#message-vide");

  compteur.textContent = nombre + " résultat(s)";
  messageVide.hidden = nombre > 0;
}

function actualiserAffichage() {
  const resultats = trierLivres(filtrerLivres(livres));
  afficherLivres(resultats);
  afficherResultats(resultats.length);
}

// --- Formulaire -------------------------------------------------------------

// Pas d'id : c'est l'API (la base) qui le génère
function lireFormulaire() {
  return {
    titre: document.querySelector("#titre").value.trim(),
    auteur: document.querySelector("#auteur").value.trim(),
    annee: Number(document.querySelector("#annee").value),
    categorie: document.querySelector("#categorie").value,
    disponible: document.querySelector("#disponible").checked,
  };
}

function afficherErreur(champ, message) {
  document.querySelector("#erreur-" + champ).textContent = message;
}

function validerFormulaire() {
  const livre = lireFormulaire();
  const anneeMax = new Date().getFullYear();
  const erreurs = { titre: "", auteur: "", annee: "", categorie: "" };

  if (livre.titre.length < 2) {
    erreurs.titre = "Le titre doit contenir au moins 2 caractères.";
  }
  if (livre.auteur.length < 2) {
    erreurs.auteur = "L'auteur doit contenir au moins 2 caractères.";
  }
  if (livre.annee < 1450 || livre.annee > anneeMax) {
    erreurs.annee = "L'année doit être entre 1450 et " + anneeMax + ".";
  }
  if (!livre.categorie) {
    erreurs.categorie = "Veuillez choisir une catégorie.";
  }

  Object.keys(erreurs).forEach(function (champ) {
    afficherErreur(champ, erreurs[champ]);
  });

  return Object.values(erreurs).every(function (message) {
    return message === "";
  });
}

// --- Événements -------------------------------------------------------------

document.querySelector("#recherche").addEventListener("input", actualiserAffichage);
document.querySelector("#filtre-categorie").addEventListener("change", actualiserAffichage);
document.querySelector("#filtre-disponibles").addEventListener("change", actualiserAffichage);
document.querySelector("#tri").addEventListener("change", actualiserAffichage);
document.querySelector("#formulaire-livre").addEventListener("submit", ajouterLivre);

chargerLivres();
