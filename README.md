# Serveur WoW Classic local

Base : SPP Classics V2 vanilla (CMaNGOS classic, branche ike3-bots de celguar) + playerbots ike3.
Les sources d'origine ne sont pas copiées ici : `sources.txt` fige chaque dépôt sur le commit
correspondant au serveur installé sur le PC (build du 11/10/2026).

- `overlay/` : nos fichiers modifiés ou ajoutés, copiés par-dessus le cœur avant compilation
  (même arborescence que mangos-classic).
- `custom/` : scripts SQL du projet.
- La compilation Windows se lance dans l'onglet **Actions** (automatique à chaque modification de `overlay/`).
  Le résultat `mangosd.exe` va dans `SPP_Server\Server\Binaries\vanilla\Bin64` (serveur arrêté).
