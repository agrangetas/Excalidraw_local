---
name: manipulation_excalidraw
description: Permet à l'agent de créer et modifier des schémas d'infrastructure ou de workflow dans Excalidraw via une API locale.
category: Automatisation
---

# [SYSTEM INSTRUCTION - DO NOT EDIT] - Load Preferences
<!-- system_instruction:load_preferences_start -->
## Étape 1 : Initialisation et Règles de Style Dynamiques (Mémoire)
1. Ouvre le fichier local `preferences.json` situé dans ton propre répertoire de skill.
2. Filtre les règles pour ne garder que celles qui ont la clé `"active": true`.
3. Trie-les selon la règle suivante :
   - Conserve TOUTES les règles ayant `"priority": "high"`.
   - Ajoute ensuite jusqu'à un maximum de 5 autres règles (priorité medium/low) triées par récence (`"created_at"`) et fréquence (`"frequency"`).
4. Applique ces règles de style en priorité absolue sur les instructions métier décrites ci-dessous.
<!-- system_instruction:load_preferences_end -->

# Skill: Manipulation Excalidraw

## Objectif
Ce skill permet à un agent autonome de concevoir, lire et modifier des schémas d'infrastructure ou de workflow dans Excalidraw en mode "Diagram-as-Code". L'agent interagit exclusivement avec une API de haut niveau (graphe de scène logique) qui se charge de traduire les intentions en coordonnées physiques et en fichiers JSON valides, garantissant un rendu professionnel et sans collision visuelle.

---

## Étapes d'utilisation par l'Agent

1. **Lecture de l'existant (`get_scene_layout`)**
   Avant toute action ou modification, l'agent doit impérativement appeler `get_scene_layout` pour obtenir la cartographie logique actuelle du canvas (liste des nœuds, connexions et zones).

2. **Calcul et Planification sur Grille**
   L'agent planifie les modifications ou créations en utilisant uniquement des index logiques de **colonnes** et de **lignes**. Il lui est strictement interdit de deviner ou de manipuler des coordonnées en pixels (X/Y).

3. **Exécution des modifications (Appels d'Outils)**
   L'agent ordonne les modifications en appelant une ou plusieurs fonctions atomiques disponibles (`add_node`, `connect_nodes`, `update_node`, `delete_node`, `add_group_frame`).

4. **Compilation et Clôture (`compile_and_save`)**
   Une fois sa logique métier terminée, l'agent valide les changements en appelant `compile_and_save` pour générer le fichier de scène final et récupérer l'URL de visualisation.

---

## Règles de Gestion et de Design Impératives

### RÈGLE 1 : Système de Grille Virtuelle (Zéro Collision)
L'agent doit positionner les éléments sur une grille logique pour éviter tout chevauchement. 
- **Dimensions par défaut d'un composant (Rectangle) :** `width: 160`, `height: 80`.
- **Dimensions par défaut d'une base de données (Ellipse) :** `width: 140`, `height: 70`.
- **Pas horizontal (colonnes) :** Un écart de 100px minimum est appliqué, soit un pas de `260` pixels par colonne.
- **Pas vertical (lignes) :** Un écart de 80px minimum est appliqué, soit un pas de `160` pixels par ligne.

Le backend applique automatiquement les formules suivantes :
$$X = \text{colonne} \times 260 + \text{offset\_origine}$$
$$Y = \text{ligne} \times 160 + \text{offset\_origine}$$

### RÈGLE 2 : Association Texte-Conteneur
L'agent ne doit jamais tenter de calculer la taille ou le wrapping d'un texte. Pour insérer du texte dans une forme :
- Le système crée la forme géométrique (ex: `id: "node_api"`).
- Le système crée un élément `text` superposé possédant la propriété `"containerId": "node_api"`, avec `"textAlign": "center"` et `"verticalAlign": "middle"`. Le moteur d'Excalidraw gérera le centrage automatique.

### RÈGLE 3 : Dynamique des Flèches (Câblage Relatif)
Les flèches (`arrow`) doivent être solidement ancrées aux nœuds pour rester connectées si l'utilisateur déplace un bloc manuellement.
- Le premier point du tableau `points` de la flèche doit **toujours** être `[0, 0]`. Les points suivants sont des deltas relatifs `[dX, dY]`.
- Les champs `startBinding` et `endBinding` doivent obligatoirement être renseignés avec les ID des nœuds sources et cibles.

### RÈGLE 4 : Charte Graphique "Professionnelle"
Pour bannir l'effet "croquis/brouillon" et obtenir des schémas d'architecture rigoureux :
- `"roughness": 0` (Désactive les lignes tremblantes, force des traits droits).
- `"fillStyle": "solid"` (Remplissage propre, uniforme et opaque).
- **Palette de couleurs stricte (4 maximum) :**
  - `#e8f0fe` (Bleu clair) : Services standards, APIs, Compute.
  - `#e6f4ea` (Vert clair) : Entrées, Utilisateurs, Clients, Accès publics.
  - `#fff3e0` (Orange) : Stockage, Bases de données, Files d'attente (Kafka/RabbitMQ).
  - `#fce8e6` (Rouge/Rose) : Éléments critiques, Caches rapides, Sécurité/Guardrails.

### RÈGLE 5 : Persistance, Idempotence et Suppression en Cascade
Lors de la modification d'un schéma existant :
- **Conservation :** Ne jamais modifier l'ID ou le `seed` d'un élément qui n'a pas changé.
- **Incrémentation :** Augmenter la `version` de +1 et mettre à jour le timestamp `updated` pour chaque élément modifié.
- **Sécurité de suppression :** La suppression d'un nœud (`delete_node`) doit obligatoirement déclencher une **suppression en cascade** : toutes les flèches liées à ce nœud (via `startBinding` ou `endBinding`) doivent automatiquement passer à `"isDeleted": true`.

---

## Spécifications des Fonctions Disponibles (Tools)

### 1. `get_scene_layout`
- **Rôle :** Retourne un résumé logique et léger de la scène actuelle.
- **Input :** `json {}` (Aucun paramètre requis).
- **Output :** ```json
{
  "nodes": [
    { "id": "node_api_gw", "label": "API Gateway", "type": "rectangle", "col": 1, "row": 2, "color": "blue" }
  ],
  "connections": [
    { "id": "arrow_01", "from": "node_users", "to": "node_api_gw", "label": "HTTPS" }
  ],
  "frames": []
}
```

### 2. `add_node`
- **Rôle :** Ajoute une forme et son texte lié sur la grille virtuelle.
- **Input :**
  - `label` *(string, requis)* : Texte à afficher dans le bloc.
  - `type` *(string, requis)* : `"rectangle"` | `"ellipse"` | `"diamond"`.
  - `col` *(integer, requis)* : Index de colonne sur la grille.
  - `row` *(integer, requis)* : Index de ligne sur la grille.
  - `color` *(string, optionnel)* : `"blue"` | `"green"` | `"orange"` | `"red"` | `"gray"`. (Défaut : `"blue"`).
- **Output :** `json { "success": true, "node_id": "node_12345" }`

### 3. `connect_nodes`
- **Rôle :** Crée une flèche directionnelle aimantée entre deux nœuds.
- **Input :**
  - `from_node_id` *(string, requis)* : ID du nœud de départ.
  - `to_node_id` *(string, requis)* : ID du nœud d'arrivée.
  - `label` *(string, optionnel)* : Libellé textuel sur la flèche.
  - `style` *(string, optionnel)* : `"solid"` (par défaut) ou `"dashed"` (pointillés).
- **Output :** `json { "success": true, "connection_id": "arrow_67890" }`

### 4. `update_node`
- **Rôle :** Modifie les propriétés d'un nœud existant (le déplacement recalcule automatiquement les flèches liées).
- **Input :**
  - `node_id` *(string, requis)* : ID du nœud à modifier.
  - `new_label` *(string, optionnel)* : Nouveau texte.
  - `new_col` *(integer, optionnel)* : Nouvelle colonne.
  - `new_row` *(integer, optionnel)* : Nouvelle ligne.
  - `new_color` *(string, optionnel)* : Nouvelle couleur de la charte.
- **Output :** `json { "success": true, "mutated_fields": [...] }`

### 5. `delete_node`
- **Rôle :** Supprime logiquement un nœud et nettoie en cascade les flèches orphelines.
- **Input :**
  - `node_id` *(string, requis)* : ID du nœud à supprimer.
- **Output :** `json { "success": true, "cascade_deleted_arrows": [...] }`

### 6. `add_group_frame`
- **Rôle :** Crée un encadré (Frame) englobant une zone de la grille et y associe les nœuds situés à l'intérieur.
- **Input :**
  - `title` *(string, requis)* : Nom de la zone (ex: "Zone Privée VPC").
  - `start_col` *(integer, requis)* : Colonne de départ (haut gauche).
  - `start_row` *(integer, requis)* : Ligne de départ (haut gauche).
  - `end_col` *(integer, requis)* : Colonne de fin (bas droit).
  - `end_row` *(integer, requis)* : Ligne de fin (bas droit).
- **Output :** `json { "success": true, "frame_id": "frame_99" }`

### 7. `compile_and_save`
- **Rôle :** Compile le JSON final Excalidraw, l'enregistre sur l'instance locale (Port `3030`) et fournit l'URL.
- **Input :**
  - `filename` *(string, requis)* : Nom du fichier (ex: `infra.excalidraw`).
- **Output :** `json { "success": true, "download_url": "http://localhost:3030/api/v2/scenes/..." }`

---

## Traitement des Valeurs Manquantes et Erreurs
- **Valeurs manquantes :** Si un paramètre optionnel (comme la couleur ou le style de flèche) n'est pas spécifié par l'utilisateur, l'agent doit **appliquer la valeur par défaut** définie dans la spécification du Tool plutôt que de bloquer l'exécution ou d'interrompre le workflow.
- **Gestion des erreurs :** Si l'agent tente d'appeler une fonction sur un `node_id` inexistant ou déjà supprimé (`isDeleted: true`), le système renvoie un échec. L'agent doit intercepter l'erreur, rafraîchir sa cartographie via `get_scene_layout` et corriger sa trajectoire.

---

## Exemple de Format JSON Cible (Généré par le Backend)
Voici le rendu exact d'un nœud standardisé généré en conformité avec la charte professionnelle (Règle 4) :

```json
{
  "id": "node_api_gw",
  "type": "rectangle",
  "x": 260,
  "y": 160,
  "width": 160,
  "height": 80,
  "angle": 0,
  "strokeColor": "#1a73e8",
  "backgroundColor": "#e8f0fe",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "strokeStyle": "solid",
  "roughness": 0,
  "opacity": 100,
  "seed": 424242,
  "version": 1,
  "isDeleted": false,
  "roundness": { "type": 3 }
}
```

# [SYSTEM INSTRUCTION - DO NOT EDIT] - Write Preferences
<!-- system_instruction:write_preferences_start -->
## Étape Finale : Capitalisation et Auto-Apprentissage
1. À la fin de cette tâche, si l'utilisateur a formulé des critiques, des corrections ou des préférences durables sur le résultat produit :
   - Formule une règle générique et concise correspondante.
   - Demande poliment à l'utilisateur : *"J'ai noté que vous préférez [la règle]. Voulez-vous que je m'en souvienne pour les prochaines exécutions ?"*
2. Si l'utilisateur confirme :
   - Ouvre le fichier local `preferences.json` situé dans ton propre répertoire de skill.
   - Ajoute la règle avec les valeurs : `id: "pref_random", preference: "la règle", created_at: "timestamp", priority: "medium", frequency: 1, active: true`.
   - Si la règle existe déjà dans le fichier, incrémente sa valeur `frequency` de 1.
   - Sauvegarde les modifications dans le fichier.
<!-- system_instruction:write_preferences_end -->
