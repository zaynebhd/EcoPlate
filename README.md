# EcoPlate 🌿
*Moins de gaspillage, plus d'avenir.*

Site web pour réduire le gaspillage alimentaire : l'utilisateur ajoute ses aliments, consulte des recettes générées par la plateforme, surveille les dates de péremption, réserve des offres et suit son impact. **Aucun aliment utilisateur n'est prérempli.**

**Technologies :** HTML, CSS, JavaScript, Python (Flask), MySQL, Docker

## Lancer le projet
Prérequis : Docker et Docker Compose.

```
docker compose up --build -d
```
Puis ouvrir http://localhost:5000

## Comptes
- À l’ouverture, choisissez « Utilisateur individuel » ou « Association / Hôtel / Restaurant », puis connectez-vous ou créez un compte.
- Les mots de passe sont stockés sous forme hachée. Le cookie de session Flask est signé avec une clé aléatoire au démarrage; les sessions en cours sont donc invalidées après un redémarrage. Pour conserver une clé stable, définissez `FLASK_SECRET_KEY` dans l’environnement avant de lancer Docker.
- Les aliments sont associés au compte individuel connecté. Les anciennes lignes d’aliments sont conservées lors de la mise à jour, mais restent sans propriétaire et ne sont donc pas affichées dans les nouveaux comptes.
- Les organisations publient et gèrent leurs annonces, consultent les offres des autres organisations et voient les noms, quantités et dates des réservations de leurs propres annonces. Les utilisateurs individuels indiquent leur nom complet à l’inscription, filtrent les offres et réservent une quantité, qui est alors retirée du stock disponible.
- Les recettes sont préchargées par la plateforme. Elles sont comparées aux aliments disponibles du compte, triées par proportion d’ingrédients présents, puis départagées selon les aliments qui expirent dans les trois jours.
- Le démarrage de l’application ajoute les tables et colonnes manquantes à la base existante. Aucune suppression de volume n’est nécessaire.

Pour supprimer les données et repartir d'une base vide (attention : cette commande efface le volume de la base) :
```
docker compose down -v
docker compose up --build -d
```

## Pages
| Page | Fichier | Rôle |
|---|---|---|
| Choix du compte | `account-type.html` | Choisir le type de compte avant la connexion ou l'inscription |
| Connexion / inscription | `auth.html` | Ouvrir un compte individuel ou organisation |
| Espace organisation | `organization-dashboard.html` | Publier, modifier et supprimer ses annonces, consulter les réservations reçues |
| Offres | `offers.html` | Filtrer les annonces ; les particuliers peuvent réserver et les organisations consultent les annonces des autres |
| Accueil | `index.html` | Présentation, aliments à consommer en priorité, chiffres (PNUE) |
| Mes aliments | `food.html` | Ajouter un aliment, le marquer consommé / jeté, le supprimer |
| Recettes | `recipes.html` | Comparer les 18 recettes de la plateforme avec ses aliments |
| Mon impact | `impact.html` | Statistiques et graphique des 6 dernières semaines |

## Structure
- `app.py` : backend Flask (pages, sessions, API JSON et migration additive)
- `database.sql` : tables `users`, `organizations`, `announcements`, `reservations`, `recipes`, `recipe_ingredients`, `aliment`
- `css/style.css`, `js/*.js` : interface
- `Dockerfile`, `docker-compose.yml` : environnement

Les anciennes tables `recette` et `ingredient` sont conservées pour ne pas supprimer de données, mais l’interface utilise désormais les recettes préchargées de la plateforme.

## Notes
- **Accents** : MySQL tourne en `utf8mb4` (voir `docker-compose.yml` et `database.sql`), ce qui évite les « pÃ¢tes » / « lÃ©gumes ».
- **Recherche de recettes** : la comparaison ignore les accents, les majuscules et les pluriels (« Tomates » = « tomate », « Œufs » = « oeuf »).
- **Aliment « sauvé »** : consommé au plus tard à sa date de péremption.
- **Chiffres de l'accueil** : PNUE, *Food Waste Index Report 2024*. À revérifier sur le site du PNUE avant la présentation.

## Équipe
- Personne 1 : frontend (`*.html`, `css/`, `js/`)
- Personne 2 : backend et base de données (`app.py`, `database.sql`)
