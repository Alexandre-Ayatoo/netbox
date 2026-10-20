# Déployer NetBox sur Coolify

## Instance restaurée avec plugins et Keycloak

Pour l'instance migrée en NetBox **4.6.10** avec ses cinq plugins et Keycloak,
utiliser **`/docker-compose.production.yml`** dans Coolify. Ce fichier utilise les
mêmes images, variables, contrôles de santé et volumes que
`/docker-compose.migration.yml`, qui reste compatible avec les déploiements
existants. Changer le chemin Compose dans la même ressource Coolify ne nécessite
pas de restauration de base.

Conserver les noms des six volumes `migration-*` et le fichier privé
`/etc/netbox-migration/settings.json` sur le serveur Docker : ils contiennent les
données et réglages actifs de production. Le préfixe historique des volumes ne
signifie pas qu'ils peuvent être supprimés après la migration. Le fichier privé
contient notamment la clé Django, les peppers API, les réglages des plugins et les
secrets Keycloak. Il est monté en lecture seule dans netbox et worker.

Les opérations d'export et les précisions sur les réglages repris figurent dans le
[guide de migration](migration/README.md). La mise à niveau de NetBox 4.6.10 et des
plugins se prépare séparément, avec une nouvelle sauvegarde avant la mise à jour.

## Nouvelle installation depuis le code du dépôt

Cette configuration construit NetBox depuis ce dépôt et déploie PostgreSQL, Redis,
NetBox, son worker et Nginx. Les migrations, les fichiers statiques et le premier
compte administrateur sont préparés automatiquement au démarrage.

## Installation

1. Poussez ces fichiers dans votre dépôt Git accessible à Coolify.
2. Dans votre projet Coolify, créez une **Application depuis un dépôt Git** et
   sélectionnez ce dépôt et votre branche.
3. Choisissez **Docker Compose** comme méthode de construction, avec :
   - **Base Directory** : `/`
   - **Docker Compose Location** : `/docker-compose.yml`
4. Enregistrez et chargez la configuration Compose. Dans **Domains**, attribuez au
   service **web** votre domaine, par exemple `https://netbox.example.com:8080`.
   Le port `8080` désigne le port interne ; l'adresse publique sera
   `https://netbox.example.com`. Faites pointer le DNS vers votre serveur Coolify.
5. Dans **Environment Variables**, vérifiez que `SERVICE_URL_WEB` correspond à
   l'adresse publique avec son protocole, sans le port interne
   (`https://netbox.example.com`). Coolify gère cette valeur depuis le domaine.
   Les variables `SERVICE_PASSWORD_64_*` sont générées par Coolify. Vous pouvez
   personnaliser `NETBOX_ADMIN_USERNAME` et `NETBOX_ADMIN_EMAIL` avant le premier
   déploiement.
6. Cliquez sur **Deploy**. Le premier déploiement construit l'image et initialise
   la base : il peut prendre plusieurs minutes. Consultez les logs de **netbox**
   pour suivre les migrations, puis ouvrez votre domaine.

Connectez-vous avec l'utilisateur **admin** (ou `NETBOX_ADMIN_USERNAME`) et le mot
de passe **SERVICE_PASSWORD_64_ADMIN**, consultable dans les variables Coolify.
Vous pouvez ensuite changer ce mot de passe dans NetBox.

Il faut utiliser le déploiement **Git + Docker Compose** : les Dockerfiles et les
fichiers de configuration sont lus dans le dépôt. Le simple collage du YAML dans
« Docker Compose Empty » ne fournit pas ces fichiers.

## Ce qui est déjà configuré

- HTTPS terminé par le proxy Coolify, avec transmission du protocole à Django.
- Hôte autorisé et origine CSRF déduits de l'URL publique.
- Clé Django, pepper des jetons API et mots de passe générés séparément.
- Volumes persistants pour PostgreSQL, Redis, les médias, scripts et rapports.
- Worker RQ avec planification des tâches système de NetBox.
- Contrôles de santé et démarrage du worker après l'initialisation de NetBox.
- Fichiers statiques servis par Nginx ; accès aux médias contrôlé par NetBox.
- Aucun port publié directement sur l'hôte : seul **web:8080** doit être relié
  au domaine Coolify.

## Redéployer et administrer

Un nouveau déploiement applique les migrations existantes et actualise les fichiers
statiques. Les comptes existants et leurs mots de passe sont conservés. Modifier
`SERVICE_PASSWORD_64_ADMIN` ne réinitialise donc pas un compte déjà créé.

Pour réinitialiser le mot de passe depuis le terminal du conteneur **netbox** :

```bash
python manage.py changepassword admin
```

Pour créer un autre administrateur :

```bash
python manage.py createsuperuser
```

Conservez les secrets générés entre les déploiements, notamment
`SERVICE_PASSWORD_64_SECRET`, `SERVICE_PASSWORD_64_PEPPER` et le mot de passe
PostgreSQL. Changer celui-ci dans Coolify ne change pas le mot de passe d'une base
déjà initialisée. Un changement de domaine nécessite un redéploiement pour mettre
à jour les paramètres Django.

Sauvegardez la base PostgreSQL ainsi que les volumes médias, scripts et rapports
avant une mise à jour. Les volumes survivent aux redéploiements ; leur suppression
dans Coolify supprime les données correspondantes. Ne lancez qu'une instance du
service **netbox** avec cette configuration, afin de ne pas appliquer plusieurs
migrations en parallèle.

Le nombre de processus web se règle avec `GUNICORN_WORKERS` (3 par défaut).

Référence : [Docker Compose dans Coolify](https://coolify.io/docs/applications/builds/docker-compose).

## Vérification locale facultative

Avec Docker et Docker Compose installés, depuis la racine du dépôt :

```bash
python3 contrib/coolify/smoke_test.py
```

Ce test construit et démarre une stack isolée avec des secrets temporaires. Il
vérifie la santé des services, les fichiers statiques, la connexion administrateur,
la conservation du mot de passe lors d'une nouvelle initialisation et les contrôles
d'hôte et d'origine CSRF. Ses conteneurs et volumes sont supprimés à la fin.
