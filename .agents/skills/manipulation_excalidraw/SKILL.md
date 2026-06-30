---
name: Manipulation Excalidraw
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
Ce skill permet à un agent autonome de créer et de modifier des schémas d'infrastructure ou de workflow dans Excalidraw en utilisant l'API locale. L'agent peut interagir avec le canvas, lire son état, et injecter des modifications directement sans passer par les serveurs d'Excalidraw.

## Étapes d'utilisation
1. **Initialisation de l'API**  
   L'agent doit d'abord établir une connexion avec l'API d'Excalidraw sur le port 3035. Cela peut être fait en utilisant la méthode appropriée pour récupérer l'instance de l'API.

   ```javascript
   const excalidrawAPI = await readyPromise;
   ```

2. **Lire l'état actuel du canvas**  
   Avant de faire des modifications, l'agent peut lire l'état actuel du canvas pour comprendre quels éléments sont déjà présents.
   ```javascript
   const elementsActuels = excalidrawAPI.getSceneElements();
   const configurationVisuelle = excalidrawAPI.getAppState();
   ```

3. **Créer ou modifier des éléments**  
   - **Création d'un nouvel élément**  
     Pour créer un nouvel élément, l'agent doit définir les propriétés nécessaires et appeler la méthode `create_element`. Par exemple, pour créer un rectangle :
     ```javascript
     excalidrawAPI.create_element({
       "type": "rectangle",
       "x": 100,
       "y": 100,
       "width": 200,
       "height": 100,
       "strokeColor": "#1e1e1e",
       "backgroundColor": "#ffffff",
       "fillStyle": "solid",
       "strokeWidth": 2,
       "roughness": 0,
       "seed": 12345
     });
     ```
   - **Modification d'un élément existant**  
     Pour modifier un élément, l'agent doit spécifier l'ID de l'élément et les propriétés à changer. Par exemple, pour changer la couleur de fond d'un rectangle :
     ```javascript
     excalidrawAPI.update_element({
       "id": "rect_1",
       "properties": {
         "backgroundColor": "#ff0000"
       }
     });
     ```

4. **Gestion des erreurs**  
   L'agent doit être capable de gérer les erreurs potentielles, comme des ID d'éléments non valides ou des tentatives de modification d'éléments supprimés. En cas d'erreur, l'agent doit loguer l'erreur et éventuellement alerter l'utilisateur.

5. **Sauvegarde des modifications**  
   Après avoir effectué des modifications, l'agent peut sauvegarder l'état du canvas en utilisant l'API REST d'Excalidraw. Cela se fait en envoyant un POST avec le JSON de la scène :
   ```javascript
   const response = await fetch('/api/v2/scenes', {
     method: 'POST',
     body: JSON.stringify({
       "type": "excalidraw",
       "version": 2,
       "elements": elementsActuels,
       "appState": configurationVisuelle
     })
   });
   ```

## Règles de gestion importantes
- **Espacement des éléments** : Assurez-vous que les éléments créés ne se chevauchent pas. Utilisez un espacement d'au moins 60 pixels entre les éléments pour éviter les collisions visuelles.
- **Consistance du Seed** : Conservez le même numéro seed pour un objet lors de modifications pour éviter des changements de style visuel inattendus.

## Exemples de fichiers JSON
Voici un exemple de fichier JSON que l'agent peut générer ou modifier :
```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://excalidraw.com",
  "elements": [
    {
      "id": "title_01",
      "type": "text",
      "x": 40,
      "y": 30,
      "width": 600,
      "height": 40,
      "text": "Production LLM Architecture - Inference Pipeline",
      "fontSize": 24,
      "fontFamily": 2
    },
    {
      "id": "vpc_frame",
      "type": "frame",
      "x": 200,
      "y": 100,
      "width": 780,
      "height": 450,
      "name": "Private Cloud VPC"
    }
  ],
  "appState": {
    "theme": "light",
    "viewBackgroundColor": "#ffffff"
  }
}
```

## Traitement des valeurs manquantes
Si des valeurs requises sont manquantes lors de la création ou de la modification d'éléments, l'agent doit alerter l'utilisateur et ne pas procéder à l'opération jusqu'à ce que toutes les informations nécessaires soient fournies.

## Documentation utile
- [Documentation du JSON](https://docs.excalidraw.com/docs/codebase/json-schema)
- [Documentation de l'API](https://docs.excalidraw.com/docs/@excalidraw/excalidraw/api)
- [Documentation globale](https://docs.excalidraw.com/docs)

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
