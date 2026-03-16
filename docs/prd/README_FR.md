# PRD Library — Guide humain (FR)

Cette bibliothèque sert à construire des PRD de projet de manière cohérente, réutilisable et exploitable aussi bien par des humains que par des agents de code.

## Idée générale
Le système repose sur trois briques :
- un **core** générique et stable
- des **packs** spécialisés activés seulement quand ils s'appliquent
- des **tools** pour l'intake, l'assemblage, Codex, les skills et l'évolution de la bibliothèque

Le dépôt est organisé pour qu'un humain voie d'abord les documents utiles à la prise en main, tandis que la mécanique réelle est rangée dans `prd_library/`.

## Par où commencer
Lis dans cet ordre :
1. `START_HERE.md`
2. `QUICKSTART.md`
3. `run_wizard.py` ou `prd_library/tools/project_intake_wizard/README.md`
4. `prd_library/README.md`
5. `prd_library/LIBRARY_STRUCTURE.md`
6. `prd_library/PROJECT_ASSEMBLY_MODEL.md`

## Si tu ne sais pas quoi remplir
Tu n'es pas obligé de comprendre tout le PRD pour démarrer.
Le plus simple est d'utiliser le wizard d'intake.

Le wizard peut :
- poser un questionnaire guidé
- lire un brief markdown structuré

Il génère ensuite :
- `PROJECT_INTAKE.md`
- `PROJECT_PROFILE.md`
- `PACKS_ACTIVE.md`
- `NEXT_STEPS_FOR_GPT.md`

Ces fichiers servent de point d'entrée propre pour demander ensuite à GPT de compléter le PRD.

## Rôle des grands répertoires internes
- `prd_library/core/` : squelette générique du PRD
- `prd_library/packs/` : overlays spécialisés par type de projet
- `prd_library/tools/` : méthode de travail, wizard, gouvernance, Codex, skills
- `prd_library/examples/` : exemples et futurs cas de référence

## Règle importante
Le PRD reste la vérité projet.
Les packs complètent.
Les prompts accélèrent.
Les skills assistent.
Mais aucun de ces éléments ne doit devenir une source de vérité cachée à côté du PRD.

## Pourquoi cette bibliothèque existe
Elle sert à éviter trois problèmes classiques :
- des specs dispersées dans les chats
- des projets mal cadrés au départ
- des agents de code qui comprennent la technique mais ratent la logique métier

C'est pour cela que le core inclut aussi une couche métier `06_domain/` pour les projets où la logique opératoire est importante.

## Si tu utilises Codex
Le dépôt contient aussi un kit minimal dans `prd_library/tools/codex/templates/` pour instancier rapidement :
- `AGENTS.md`
- `AGENTS.override.md`
- `PLANS.md`

Cela évite de repartir de zéro sur l’intégration repo/Codex.
