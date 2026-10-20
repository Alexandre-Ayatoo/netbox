# Migration de l'instance 4.6.10

Après validation de la migration et du SSO, le fichier
`/docker-compose.production.yml` permet de conserver l'instance restaurée en
production. Il réutilise exactement les volumes et réglages de ce déploiement.
Conserver `/etc/netbox-migration/settings.json` et les volumes `migration-*`, même
lors du nettoyage des sauvegardes et de l'ancienne installation.

Cette image de préparation utilise NetBox 4.6.10 et les cinq versions de plugins
relevées sur l'ancienne instance. L'archive officielle est vérifiée par SHA-256 ;
les dépendances de NetBox et des plugins sont résolues ensemble.

Test local avec des secrets fictifs (aucune restauration de données réelles) :

```bash
python3 contrib/coolify/smoke_test.py --migration
```

## Export privé sur l'ancien serveur

Copier `export_settings.py` sur le serveur, puis l'exécuter avec l'environnement
de l'ancienne instance. Depuis `/opt/netbox/netbox`, en tant que root :

```bash
install -d -m 0750 -o root -g 1000 /etc/netbox-migration
umask 077
/opt/netbox/venv/bin/python manage.py shell --no-imports \
  < /root/export_settings.py > /etc/netbox-migration/settings.json.tmp
python3 -m json.tool /etc/netbox-migration/settings.json.tmp > /dev/null \
  && chown root:1000 /etc/netbox-migration/settings.json.tmp \
  && chmod 0640 /etc/netbox-migration/settings.json.tmp \
  && mv /etc/netbox-migration/settings.json.tmp /etc/netbox-migration/settings.json
```

Le fichier contient la clé Django, les peppers API et la configuration des plugins,
y compris les secrets IP Fabric et les paramètres `REMOTE_AUTH_*` et `SOCIAL_AUTH_*`
explicitement définis dans l'ancienne configuration (dont les secrets SSO).
Ne pas l'afficher, le committer ou l'ajouter au
contexte de construction Docker. L'image le lit au démarrage depuis un montage
en lecture seule. Le groupe 1000 correspond à l'utilisateur de l'image ; adapter
les permissions en cas de Docker rootless ou de remappage des utilisateurs.

L'export ne reprend pas la base ou Redis de l'hôte. Il ne reprend pas non plus les
éventuels réglages `AUTH_LDAP_*`, email, stockage distant, validateurs ou autres réglages
personnalisés hors plugins : les inventorier avant la bascule.

Pour ajouter le SSO après une première migration, sauvegarder le fichier privé,
puis refaire cet export depuis l'ancienne installation et redéployer l'image
mise à jour. La base migrée et les volumes restent en place ; ne pas refaire la
restauration de la base. Avec le même domaine public, les URL de retour existantes
du client Keycloak peuvent être conservées. Vérifier ensuite la présence du bouton
Keycloak et effectuer une connexion réelle depuis le navigateur.

## Stack de préparation isolée

Utiliser le même dépôt et `/docker-compose.migration.yml` comme fichier Compose.
Ce fichier est autonome, sans `extends`, pour que Coolify puisse analyser tous les
services et leurs volumes. Les six volumes portent le préfixe `migration-` : ils
sont distincts des volumes de la stack 4.7 même dans la même ressource Coolify.
Une nouvelle ressource reste possible pour tester les deux stacks en parallèle.
Le répertoire `/etc/netbox-migration` doit exister sur le serveur Docker ; il est
monté en lecture seule dans les services netbox et worker. Configurer les variables
générées comme pour la stack principale. Pour une nouvelle ressource, un domaine
temporaire sur `web:8080` est facultatif : sans domaine, renseigner manuellement
`SERVICE_URL_WEB` avec l'URL publique prévue.

Ne jamais pointer cette image 4.6.10 vers la base déjà initialisée en 4.7.3.
Ne pas renommer les volumes `migration-*` pour les faire correspondre aux volumes
existants de la stack 4.7. Le déploiement sur la même ressource remplace les
conteneurs actifs par une instance 4.6.10 initialement vide, avant restauration.

La stack isolée permet de tester une restauration du dump avec tous les plugins
avant la migration finale. Arrêter ses services web, netbox et worker avant toute
restauration et sauvegarder sa base avant de la remplacer. Restaurer avec
`pg_restore --exit-on-error --no-owner --no-acl`, puis appliquer les tâches
`manage.py upgrade --no-input`, transférer médias/scripts/rapports et remettre les
services en route. Ne pas restaurer les files Redis de l'ancienne installation.

Avant la bascule finale, laisser terminer les travaux de l'ancienne instance,
arrêter ses services web et worker et les autres écritures/intégrations, puis
refaire une sauvegarde cohérente de la base et des fichiers. Tester les comptes,
permissions, données et plugins sur la cible avant de déplacer le domaine et de
réactiver les intégrations. Conserver l'ancienne installation et les sauvegardes.
Une fois la cible ouverte aux écritures, revenir à l'ancienne base seule perdrait
les nouvelles modifications.
