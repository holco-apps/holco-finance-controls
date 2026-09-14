# HOLCO Finance Controls — démarrer en français

[English](README.md) · [Documentation](docs/README.md) · [Versions](https://github.com/holco-apps/holco-finance-controls/releases)

**Un agent IA produit une réponse financière. HOLCO permet de vérifier les chiffres,
les sources attendues et les limites, puis de conserver les preuves.**

Le dépôt public contient un protocole de contrôle, une implémentation de référence
et des cas synthétiques. Il s'adresse aux développeurs d'agents et d'applications
financières. Le service de production, les connecteurs réels et les dossiers clients
restent privés. Les spécifications et contrats détaillés sont en anglais.

## Essayer sans connexion ni clé API

Python 3.11 ou plus récent suffit :

```sh
git clone https://github.com/holco-apps/holco-finance-controls.git
cd holco-finance-controls
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
holco-controls-demo --output demo-evidence
```

Sous Windows : utilisez `py -m venv .venv`, puis `.venv\Scripts\Activate.ps1`.
À chaque essai, choisissez un nouveau répertoire de sortie, ou omettez `--output`.

L'exemple compare 12 400 € attendus à 12 900 € annoncés. Il détecte l'écart de 500 €,
interrompt puis reprend le travail et conserve l'échec lorsqu'une correction est
soumise. Une correction correcte reste à examiner par un humain.

Le code de sortie **0** confirme que ce scénario fonctionne comme attendu, y compris
le rejet volontaire. Consultez les fichiers JSON dans `demo-evidence/`.

## Comprendre les différents niveaux

| Élément | Ce qu'il apporte |
|---|---|
| [Protocole 1.3.0](CONTROL_PROTOCOL.md) | Fichiers → compréhension → analyse proposée → confirmation humaine → vérification → restitution et décision |
| [40 exigences](CONTROL_CATALOG.md) | 33 disposent de tests de référence ; 7 relèvent de l'application intégratrice |
| [24 cas synthétiques](CONFORMANCE.md) | Comparer des verdicts en réconciliation, FEC, trésorerie et clôture |
| [Intégration](INTEGRATION.md) | API Python, MCP ou commandes avec échanges JSON pour d'autres langages |
| [Sources publiques](PUBLIC_DATA_INDEX.md) | Un index initial de données institutionnelles, sans fichier client |

Après installation, `holco-controls-conformance --self-test` exécute les 24 cas.
Pour votre implémentation, exportez les entrées avec `--tasks` et suivez le
[contrat de réponse](CONFORMANCE.md).

**Réussir ces tests ne certifie pas un agent ni sa conformité comptable complète.**
La reconnaissance documentaire par IA et l'authentification du réviseur sont des
responsabilités de l'application hôte. Le paquet public ne fournit pas ces services.

Pour participer : [question](https://github.com/holco-apps/holco-finance-controls/discussions),
[contre-exemple](https://github.com/holco-apps/holco-finance-controls/issues/new?template=control-counterexample.yml)
ou [retour d'intégration](https://github.com/holco-apps/holco-finance-controls/issues/new?template=integration.yml).
N'ajoutez aucun fichier client ou secret aux échanges publics.
