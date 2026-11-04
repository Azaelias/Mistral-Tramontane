# Mistral-Tramontane
BootCamp S3 

chef d'equipe : Kevin
artisan Bash : Haulgat
mage Python : Mouhamed
Gardien : Tiago


Jour 3

Mission 3.1 : 

+------+---------------------+-------------------------------+-------------------------------------------+
| Code | Signification       | Observé                       | Comportement de l'outil                   |
+------+---------------------+-------------------------------+-------------------------------------------+
| 200  | OK                  | Requêtes 1, 3, 4, 5 et 6      | Lire la réponse JSON et la traiter.       |
|      |                     | (avant la limite)             |                                           |
+------+---------------------+-------------------------------+-------------------------------------------+
| 401  | Non autorisé        | Requête sans jeton            | Ne pas réessayer. Arrêter avec un message |
|      |                     |                               | clair : jeton absent ou invalide.         |
+------+---------------------+-------------------------------+-------------------------------------------+
| 429  | Trop de requêtes    | Requêtes 7 à 12               | Ralentir : attendre (sleep, ou le délai   |
|      | (rate limit)        | (6 fois d'affilée)            | indiqué par l'API), puis réessayer.       |
+------+---------------------+-------------------------------+-------------------------------------------+
| 503  | Service indisponible| Requête 2 (isolée)            | Erreur temporaire : réessayer quelques    |
|      |                     |                               | fois avec une pause, puis abandonner.     |
+------+---------------------+-------------------------------+-------------------------------------------+


3.2

python3 incidents.py --sortie /tmp/incidents.csv

pages=4  total=71
len(tous) = 71
sites = ['Avignon', 'Fos', 'Nice', 'Toulon', 'Vitrolles']
CSV écrit dans /tmp/incidents.csv

