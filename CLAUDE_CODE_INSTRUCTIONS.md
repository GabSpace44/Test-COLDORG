# Instructions pour Claude Code — COLDORG RAG Assistant

> Ce document contient toutes les instructions nécessaires pour construire le projet.
> Lis l'intégralité de ce document avant d'écrire la moindre ligne de code.
> Respecte scrupuleusement l'ordre des étapes, la nomenclature des champs, et la structure des fichiers.

---

## Contexte du projet

Construire un assistant RAG (Retrieval-Augmented Generation) pour techniciens de maintenance CVC.
Le technicien décrit une panne, l'assistant retourne un diagnostic et une procédure en s'appuyant sur :
- 30 interventions passées (`interventions.json`)
- 4 fiches techniques d'équipements (fichiers `.txt`)

---

## Stack technique — aucune liberté sur ces choix

```
Base vectorielle  : ChromaDB (local, persistant)
Embeddings        : sentence-transformers — paraphrase-multilingual-mpnet-base-v2
LLM               : Groq API (défaut) / Ollama (fallback)
Interface         : Gradio
Langage           : Python 3.10+
```

---

## Structure du projet à créer

Crée exactement cette arborescence, pas une autre :

```
coldorg-rag/
│
├── data/
│   ├── interventions.json
│   └── fiches_techniques/
│       ├── FT_Frisquet_Prestige_CGC.txt
│       ├── FT_Atlantic_Idea_CM.txt
│       ├── FT_Daikin_Altherma_PACAE.txt
│       └── FT_SaunierDuval_ThemaplusCondens_CGC.txt
│
├── src/
│   ├── config.py
│   ├── ingest_interventions.py
│   ├── ingest_fiches.py
│   ├── embed.py
│   ├── retrieval.py
│   └── generate.py
│
├── tests/
│   └── questions_test.json
│
├── chroma_db/
│
├── app.py
├── main.py
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
├── schema.md
└── README.md
```



## Étape 1 — Fichiers de configuration

### `.env.example` (commité sur GitHub)
```env
LLM_PROVIDER=groq
GROQ_API_KEY=your_key_here
OLLAMA_MODEL=mistral
EMBEDDING_MODEL=paraphrase-multilingual-mpnet-base-v2
CHROMA_PATH=./chroma_db
TOP_K_INTERV=2
TOP_K_FTECH=1
DISTANCE_THRESHOLD=0.8
MAX_CHUNK_TOKENS=200
```

### `.env` (jamais commité)
Copie de `.env.example` avec les vraies valeurs.

### `.gitignore`
```
.env
chroma_db/
__pycache__/
*.pyc
.DS_Store
```

### `requirements.txt`
```
chromadb
sentence-transformers
groq
ollama
gradio
python-dotenv
```

---

## Étape 2 — `src/config.py`

Ce fichier charge toutes les variables d'environnement et définit les constantes globales.

**Ce qu'il doit contenir :**
- Chargement du `.env` via `python-dotenv`
- Toutes les variables d'environnement exposées comme constantes Python
- La table de transcodification des types d'équipements :

```python
TYPE_TRANSCO = {
    "chaudiere_gaz": "CGC",
    "pac_air_eau": "PACAE",
    "climatisation": "CM"
}
```

- Les noms des collections ChromaDB :
```python
COLLECTION_INTERV = "RAG_INTERV"
COLLECTION_FTECH = "RAG_FTECH"
```

- Un commentaire par variable expliquant son rôle

---

## Étape 3 — `src/embed.py`

Ce fichier gère la connexion à ChromaDB et la création des collections.

**Ce qu'il doit faire :**
- Se connecter à ChromaDB en mode persistant (chemin depuis `config.py`)
- Initialiser le modèle d'embeddings `paraphrase-multilingual-mpnet-base-v2`
- Créer ou récupérer les deux collections : `RAG_INTERV` et `RAG_FTECH`
- Exposer une fonction `get_collections()` qui retourne les deux collections
- Exposer une fonction `get_embedding_function()` qui retourne la fonction d'embedding

**Important :** ChromaDB avec `sentence-transformers` accepte un `embedding_function` natif — utilise `chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction`

---

## Étape 4 — `src/ingest_interventions.py`

Ce fichier ingère `interventions.json` dans la collection `RAG_INTERV`.

### Schéma exact de la collection RAG_INTERV

| Champ ChromaDB | Source JSON | Transformation |
|---|---|---|
| `id` | `id` | Aucune — ex: `"INT-001"` |
| `metadata["INTERV_DT"]` | `date` | str YYYY-MM-DD |
| `metadata["INTERV_MARQUE_CD"]` | `marque` | str brut |
| `metadata["INTERV_TYPEQ_CD"]` | `type_equipement` | Transco via `TYPE_TRANSCO` — si absent garder valeur brute |
| `metadata["INTERV_ERREUR_CD"]` | `code_erreur` | str ou `""` si null |
| `metadata["INTERV_TPSMI_NUM"]` | `temps_intervention_min` | int |
| `metadata["INTERV_DIFCT_CD"]` | `difficulte` | str |
| `metadata["INTERV_TECHN_CD"]` | `technicien` | str |
| `documents` | Concaténation | Voir construction ci-dessous |

### Construction du document (champ `documents`)

```
Équipement : {equipement}
Code erreur : {code_erreur}
Symptôme : {symptome}
Diagnostic : {diagnostic}
Solution : {solution}
Pièces remplacées : {pieces_remplacees joints par ", " — "aucune" si liste vide}
```

### Comportement attendu

- Truncate de la collection avant insert (supprimer tous les documents existants)
- Insérer tous les documents en un seul appel `collection.add()`
- Logger le nombre d'interventions ingérées
- Gérer proprement les champs null (notamment `code_erreur`)
- Les `pieces_remplacees` sont un array dans le JSON — les joindre en string

---

## Étape 5 — `src/ingest_fiches.py`

Ce fichier chunke les fichiers TXT et ingère les chunks dans `RAG_FTECH`.

### Convention de nommage des fichiers

```
FT_Marque_Modele_TYPE.txt
```

Le script parse le nom de fichier pour extraire :
- `FTECH_MARQUE_CD` → 2ème segment
- `FTECH_MODEL_CD` → 3ème segment
- `FTECH_TYPEQ_CD` → 4ème segment (sans `.txt`)

Si le fichier ne commence pas par `FT_`, lever une `ValueError` explicite.

### Table de transco des types (pour le libellé en metadata)

```python
TYPE_TRANSCO = {
    "CGC": "chaudière gaz à condensation",
    "PACAE": "pompe à chaleur air/eau",
    "CM": "climatiseur mural"
}
```

### Stratégie de chunking — CRITIQUE

**Niveau 1 — Split sur `---`**

Détecter les sections via le pattern `--- XXXXX ---`.

Sections possibles et leur `FTECH_SECTN_CD` :
```
--- CODES ERREUR ---          → "code_erreur"
--- PROBLÈMES COURANTS ---    → "probleme"
--- ENTRETIEN ---             → "entretien"
--- ENTRETIEN ANNUEL ---      → "entretien"
--- ENTRETIEN RECOMMANDÉ ---  → "entretien"
--- PIÈCES D'USURE ---        → "pieces_usure"
--- PIÈCES D'USURE COURANTES --- → "pieces_usure"
```

Le contenu avant le premier `---` (specs fabricant) → section `"header"`.

**Niveau 2 — Rechunking de la section `code_erreur` uniquement**

Dans la section `code_erreur`, détecter chaque code erreur via la regex :
```python
import re
pattern = re.compile(r'^([A-Z0-9]{1,3}[A-Z0-9]{1,3})\s—', re.MULTILINE)
```

Chaque code erreur + son contenu jusqu'au prochain code = 1 chunk indépendant.
Extraire le code erreur (ex: `E133`) et le stocker dans `FTECH_ERREUR_CD`.

Les autres sections (`entretien`, `pieces_usure`, `header`, `probleme`) → 1 chunk par section, pas de rechunking.

### Schéma exact de la collection RAG_FTECH

| Champ ChromaDB | Source | Valeur |
|---|---|---|
| `id` | Généré | MD5(`MARQUE + MODEL + TYPEQ + str(CHUNK_INDEX)`) |
| `metadata["FTECH_MARQUE_CD"]` | Nom fichier | ex: `"Frisquet"` |
| `metadata["FTECH_MODEL_CD"]` | Nom fichier | ex: `"Prestige"` |
| `metadata["FTECH_TYPEQ_CD"]` | Nom fichier | ex: `"CGC"` |
| `metadata["FTECH_SECTN_CD"]` | Parsing | ex: `"code_erreur"` |
| `metadata["FTECH_ERREUR_CD"]` | Regex | ex: `"E133"` ou `""` si absent |
| `metadata["FTECH_CHUNK_INDEX_NUM"]` | Compteur | int, commence à 0 |
| `documents` | Texte chunk | Contenu brut du chunk |

### Génération de l'ID MD5

```python
import hashlib
chunk_id = hashlib.md5(
    f"{marque}{modele}{typeq}{chunk_index}".encode()
).hexdigest()
```

### Comportement attendu

- Truncate de la collection avant insert
- Traiter tous les fichiers `.txt` du dossier `fiches_techniques/`
- Logger le nombre de chunks générés par fichier et le total
- Un chunk vide (après strip) ne doit pas être inséré

---

## Étape 6 — `src/retrieval.py`

Ce fichier gère la recherche vectorielle et la fusion des résultats.

### Détection d'entités dans la question

Avant la recherche vectorielle, tenter de détecter dans la question :
- Une marque connue (Frisquet, Daikin, Atlantic, Saunier Duval)
- Un code erreur via regex `[A-Z0-9]{1,3}[A-Z0-9]{1,3}`

Si détectés → construire un filtre metadata ChromaDB :
```python
where = {"INTERV_MARQUE_CD": {"$eq": "Frisquet"}}
```

### Recherche parallèle

```python
# RAG_INTERV — top 2
results_interv = collection_interv.query(
    query_texts=[question],
    n_results=TOP_K_INTERV,
    where=filtre_interv  # None si pas de filtre détecté
)

# RAG_FTECH — top 1
results_ftech = collection_ftech.query(
    query_texts=[question],
    n_results=TOP_K_FTECH,
    where=filtre_ftech  # None si pas de filtre détecté
)
```

### Filtrage par seuil de distance

Rejeter tout chunk dont la distance est supérieure à `DISTANCE_THRESHOLD`.

### Construction du contexte fusionné

Format exact à respecter :

```
SOURCE TERRAIN (interventions passées) :
---
[{INTERV_ID}] Équipement : {INTERV_MARQUE_CD} | Technicien : {INTERV_TECHN_CD} | Durée : {INTERV_TPSMI_NUM}min
{document}
---

SOURCE DOCUMENTAIRE (fiche technique) :
---
[{FTECH_MARQUE_CD} {FTECH_MODEL_CD} — {FTECH_SECTN_CD} — {FTECH_ERREUR_CD}]
{document}
---
```

Si une collection ne retourne aucun résultat valide → ne pas inclure la section correspondante.

### Fonction exposée

```python
def retrieve(question: str) -> str:
    """
    Retourne le contexte fusionné prêt à être injecté dans le prompt.
    """
```

---

## Étape 7 — `src/generate.py`

Ce fichier gère la construction du prompt et l'appel au LLM.

### Prompt système — COPIER EXACTEMENT

```
## ROLE
Tu es un assistant pour techniciens CVC.

## REGLES
- Réponds uniquement avec les informations issues du contexte
- Si le contexte ne contient pas la réponse, dis le explicitement :
  "Veuillez m'excuser, je n'ai pas l'information que vous désirez."
- N'invente pas de codes erreur, de procédures ou de réponses hors contexte
- Cite toujours les sources (identifiant intervention INT-XXX ou fiche technique)
- Distingue les informations issues des interventions terrain
  de celles issues des fiches techniques

## FORMAT DE LA REPONSE
1. Diagnostic probable avec le code erreur
2. Procédure recommandée
3. Pièces potentielles à prévoir
4. Interventions similaires trouvées (INT-XXX uniquement, si disponibles)

## CONTEXTE
{context}

## QUESTION
{question}
```

### Appel LLM selon `LLM_PROVIDER`

**Si `LLM_PROVIDER=groq` :**
```python
from groq import Groq
client = Groq(api_key=GROQ_API_KEY)
response = client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[{"role": "user", "content": prompt}],
    max_tokens=1000
)
```

**Si `LLM_PROVIDER=ollama` :**
```python
import ollama
response = ollama.chat(
    model=OLLAMA_MODEL,
    messages=[{"role": "user", "content": prompt}]
)
```

### Fonction exposée

```python
def generate(question: str, context: str) -> str:
    """
    Construit le prompt, appelle le LLM, retourne la réponse.
    """
```

---

## Étape 8 — `main.py`

Point d'entrée CLI. Exécute le pipeline complet sur les 5 questions de test.

**Ce qu'il doit faire :**
1. Appeler `ingest_interventions.py` — ingestion RAG_INTERV
2. Appeler `ingest_fiches.py` — ingestion RAG_FTECH
3. Charger `tests/questions_test.json`
4. Pour chaque question :
   - Appeler `retrieval.retrieve(question)`
   - Appeler `generate.generate(question, context)`
   - Afficher : la question, les chunks retrouvés, la réponse générée
5. Logger clairement chaque étape

---

## Étape 9 — `app.py`

Interface Gradio avec `gr.ChatInterface`.

**Ce qu'il doit faire :**
- Exposer une fonction `chat(message, history)` qui appelle `retrieve` puis `generate`
- Afficher la réponse du LLM dans le chat
- Afficher les sources utilisées sous la réponse (chunks retrouvés)
- Lancer sur `localhost` avec `demo.launch()`

---

## Étape 10 — `schema.md`

Documenter le schéma des deux collections avec les tableaux de métadonnées,
la table de transco, la convention de nommage des fichiers,
et la règle de génération des IDs MD5.

Ce fichier existe déjà dans `ARCHITECTURE.md` — extraire les sections pertinentes.

---

## Règles de développement — à respecter absolument

### Nomenclature
- Tous les champs des collections respectent exactement la nomenclature définie :
  `INTERV_*` pour RAG_INTERV, `FTECH_*` pour RAG_FTECH
- Pas de renommage, pas de raccourcis

### Commentaires
- Chaque fonction a une docstring expliquant ce qu'elle fait
- Chaque champ de metadata a un commentaire inline expliquant son rôle
- Les choix non évidents sont commentés (ex: pourquoi MD5 sur ces 4 champs)

### Gestion des erreurs
- Fichier TXT avec nom non conforme → `ValueError` explicite avec message clair
- Clé API manquante → message d'erreur qui dit exactement quoi configurer dans `.env`
- Collection ChromaDB vide lors du retrieval → message clair, pas de crash

### Pas de hardcoding
- Aucune valeur en dur dans le code — tout passe par `config.py` et `.env`
- Les marques connues pour la détection d'entités peuvent être une liste dans `config.py`

### Un fichier = une responsabilité
- `ingest_interventions.py` ne fait que l'ingestion des interventions
- `retrieval.py` ne fait que la recherche
- `generate.py` ne fait que la génération
- Pas de logique métier dans `main.py` — il orchestre uniquement

---

## Ordre de développement recommandé

1. `requirements.txt` + `.env` + `.env.example` + `.gitignore`
2. `src/config.py`
3. `src/embed.py`
4. `src/ingest_interventions.py` → tester avec `python src/ingest_interventions.py`
5. `src/ingest_fiches.py` → tester avec `python src/ingest_fiches.py`
6. `src/retrieval.py` → tester une question simple
7. `src/generate.py` → tester bout en bout
8. `main.py` → tester les 5 questions
9. `app.py` → interface Gradio
10. `schema.md` + `README.md`
