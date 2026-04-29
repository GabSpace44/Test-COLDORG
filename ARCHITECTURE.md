# Documentation Architecture — COLDORG RAG Assistant

> Document de référence technique rédigé avant développement.  
> Validé par Gabriel SURIER 


---

## 1. Contexte et objectif

Construire un prototype fonctionnel de système RAG (Retrieval-Augmented Generation) permettant à un technicien de maintenance CVC de poser une question en langage naturel et d'obtenir un diagnostic et une procédure de résolution, en s'appuyant sur :
- L'historique des 30 interventions passées
- Les 4 fiches techniques d'équipements

---

## 2. Philosophie du POC

- **Truncate / Insert direct** — pas d'ingestion incrémentale, pas d'ODS, pas de DWH
- **Local first** — ChromaDB local, embeddings locaux, LLM via API gratuite
- **Destructible et réutilisable** — le projet se relance from scratch en une commande
- **Reproductible** — le recruteur clone, configure son `.env`, lance `main.py`

---

## 3. Stack technique

| Composant | Choix | Justification |
|---|---|---|
| Base vectorielle | ChromaDB (local) | Collections nommées, métadonnées natives, zéro serveur, pip install |
| Modèle embeddings | `paraphrase-multilingual-mpnet-base-v2` | Multilingue, français natif, dimension 768, standard sentence-transformers |
| LLM | Groq API (Llama 3.1) | Gratuit, ultra rapide, pas besoin de configuration en RAM , fallback Ollama disponible |
| Interface | Gradio | Chat UI natif, une commande, affichage des sources |
| Langage | Python 3.10+ | Recommandé par les consignes |

---

## 4. Architecture générale

```
données brutes
      │
      ├── interventions.json
      │        │
      │        ▼
      │   ingest_interventions.py
      │   - Chargement JSON
      │   - Transcodification type_equipement
      │   - Construction document (concaténation)
      │   - Insert dans RAG_INTERV
      │
      └── fiches_techniques/*.txt
               │
               ▼
          ingest_fiches.py
          - Parse nom fichier → metadata
          - Détection sections (--- SECTION ---)
          - Détection codes erreur (regex)
          - Chunking par pattern
          - Génération ID MD5
          - Insert dans RAG_FTECH
                    │
                    ▼
              ChromaDB (local)
              ├── RAG_INTERV
              └── RAG_FTECH
                    │
                    ▼
              retrieval.py
              ├── Détection entités (marque, code erreur)
              ├── Filtre metadata si détecté
              ├── Top-2 RAG_INTERV
              └── Top-1 RAG_FTECH
                    │
               Fusion contexte
                    │
                    ▼
              generate.py
              - Construction prompt
              - Injection contexte
              - Appel Groq API
                    │
                    ▼
               Réponse technicien
```

---

## 5. Collections ChromaDB

### 5.1 Collection RAG_INTERV

Une entrée = une intervention complète. Pas de chunking — chaque intervention est déjà un document atomique.

| Champ | Type ChromaDB | Type données | Description |
|---|---|---|---|
| INTERV_ID | id | str | Identifiant natif du JSON (ex: INT-001) |
| INTERV_DT | metadata | str | Date de l'intervention (YYYY-MM-DD) |
| INTERV_MARQUE_CD | metadata | str | Marque de l'équipement (ex: Frisquet) |
| INTERV_TYPEQ_CD | metadata | str | Type d'équipement transcodifié (ex: CGC) |
| INTERV_ERREUR_CD | metadata | str | Code erreur affiché (ex: E133) |
| INTERV_TPSMI_NUM | metadata | int | Temps d'intervention en minutes |
| INTERV_DIFCT_CD | metadata | str | Degré de difficulté (facile / moyen / difficile) |
| INTERV_TECHN_CD | metadata | str | Nom du technicien |
| document | document | str | Concaténation : equipement + symptome + diagnostic + solution + pieces_remplacees |

**Construction du document :**
```
Équipement : [equipement]
Code erreur : [code_erreur]
Symptôme : [symptome]
Diagnostic : [diagnostic]
Solution : [solution]
Pièces remplacées : [pieces_remplacees joints par virgule]
```

---

### 5.2 Collection RAG_FTECH

Une entrée = un chunk d'une fiche technique. Plusieurs chunks par fiche.

| Champ | Type ChromaDB | Type données | Description |
|---|---|---|---|
| FTECH_ID | id | str | MD5(MARQUE + MODEL + TYPEQ + CHUNK_INDEX) |
| FTECH_MARQUE_CD | metadata | str | Marque extraite du nom de fichier |
| FTECH_MODEL_CD | metadata | str | Modèle extrait du nom de fichier |
| FTECH_TYPEQ_CD | metadata | str | Type équipement transcodifié |
| FTECH_SECTN_CD | metadata | str | Section : header / code_erreur / probleme / entretien / pieces_usure |
| FTECH_ERREUR_CD | metadata | str | Code erreur (ex: E133) — null si pas de code erreur |
| FTECH_CHUNK_INDEX_NUM | metadata | int | Position du chunk dans la fiche (0, 1, 2...) |
| document | document | str | Texte du chunk embedé |

---

## 6. Table de transcodification des types d'équipements

Utilisée à l'ingestion pour normaliser le champ `type_equipement` du JSON et le suffixe des noms de fichiers TXT.

| Code | Libellé complet |
|---|---|
| CGC | chaudière gaz à condensation |
| PACAE | pompe à chaleur air/eau |
| CM | climatiseur mural |

> Pour les types non référencés dans la transco (ex: VMC, chauffe_eau_thermo), la valeur brute du JSON est conservée telle quelle.

---

## 7. Convention de nommage des fiches techniques

```
FT_Marque_Modele_TYPE.txt
```

**Exemples :**
```
FT_Frisquet_Prestige_CGC.txt
FT_Atlantic_Idea_CM.txt
FT_Daikin_Altherma_PACAE.txt
FT_SaunierDuval_ThemaplusCondens_CGC.txt
```

**Règles :**
- Préfixe `FT_` obligatoire — permet la validation à l'ingestion
- CamelCase pour les marques/modèles composés
- Pas d'accents, pas d'espaces, pas de caractères spéciaux
- Le suffixe TYPE est le code de la table de transco

Le script d'ingestion parse automatiquement ce nom pour extraire `FTECH_MARQUE_CD`, `FTECH_MODEL_CD`, `FTECH_TYPEQ_CD`. Si le nom ne respecte pas la convention, une erreur explicite est levée.

---

## 8. Stratégie de chunking des fiches techniques

### 8.1 Niveau 1 — Détection des sections

Split sur le pattern `--- SECTION ---` présent sur toutes les fiches.

Sections identifiées :
- `header` — informations fabricant et caractéristiques techniques
- `code_erreur` — codes erreur avec causes et procédures
- `probleme` — problèmes courants sans code erreur (ex: Atlantic CM)
- `entretien` — procédures d'entretien
- `pieces_usure` — pièces d'usure courantes

### 8.2 Niveau 2 — Rechunking de la section codes erreur

Dans la section `code_erreur`, chaque code erreur est un chunk indépendant.

**Regex de détection :**
```
[A-Z0-9]{1,3}[A-Z0-9]{1,3}\s—
```

Matche :
- `E133 —` (Frisquet)
- `F28 —` (Saunier Duval)
- `U4 —` (Daikin)
- `7H —` (Daikin — commence par un chiffre)
- `AH —` (Daikin)

### 8.3 Sections sans rechunking

`entretien`, `pieces_usure`, `header` → 1 chunk par section (taille raisonnable).

### 8.4 Génération de l'ID MD5

```python
import hashlib
chunk_id = hashlib.md5(
    f"{marque}{modele}{typeq}{chunk_index}".encode()
).hexdigest()
```

Stable pour les upserts futurs — l'ID ne change pas si le contenu est modifié.

---

## 9. Stratégie de retrieval

### 9.1 Recherche parallèle sur les 2 collections

```
Question technicien
        │
        ├── Détection entités (marque, code erreur dans la question)
        │
        ├── Top-2 RAG_INTERV (avec filtre metadata si entités détectées)
        │
        └── Top-1 RAG_FTECH (avec filtre metadata si entités détectées)
                    │
              Fusion positionnelle
                    │
              Contexte final (3 chunks max)
```

### 9.2 Seuil de distance

```
DISTANCE_THRESHOLD = 0.8
```
Un chunk avec un score supérieur au seuil est rejeté — évite d'injecter du contexte non pertinent.

### 9.3 Construction du contexte injecté

```
SOURCE TERRAIN (interventions passées) :
---
[INT-001] Équipement : Frisquet Prestige | Technicien : Martin D. | Durée : 45min
Symptôme : ...
Diagnostic : ...
Solution : ...
---
[INT-029] ...

SOURCE DOCUMENTAIRE (fiche technique) :
---
[FT_Frisquet_Prestige_CGC — code_erreur — E133]
...
```

Les interventions passent en premier — c'est l'information prioritaire pour le technicien terrain.

---

## 10. Prompt système

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

---

## 11. Configuration — variables d'environnement

```env
# LLM
LLM_PROVIDER=groq
GROQ_API_KEY=your_key_here
OLLAMA_MODEL=mistral

# Embeddings
EMBEDDING_MODEL=paraphrase-multilingual-mpnet-base-v2

# ChromaDB
CHROMA_PATH=./chroma_db

# Retrieval
TOP_K_INTERV=2
TOP_K_FTECH=1
DISTANCE_THRESHOLD=0.8
MAX_CHUNK_TOKENS=200
```

---

## 12. Arborescence du projet

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
│   ├── config.py                  # Lecture .env, constantes, transco
│   ├── ingest_interventions.py    # Chargement JSON → RAG_INTERV
│   ├── ingest_fiches.py           # Chunking TXT → RAG_FTECH
│   ├── embed.py                   # Connexion ChromaDB, collections
│   ├── retrieval.py               # Recherche vectorielle, fusion
│   └── generate.py                # Prompt, appel LLM, réponse
│
├── tests/
│   └── questions_test.json        # 5 questions de référence
│
├── chroma_db/                     # Base vectorielle locale (gitignore)
│
├── app.py                         # Interface Gradio
├── main.py                        # Pipeline CLI — tests des 5 questions
├── .env                           # Secrets locaux (gitignore)
├── .env.example                   # Template public
├── .gitignore
├── requirements.txt
├── schema.md                      # Ce document
└── README.md
```

---

## 13. À l'échelle — 10 000 interventions

Points identifiés nécessitant une évolution architecturale :

- **Ingestion incrémentale** — détecter les nouvelles interventions via `INTERV_ID` plutôt que truncate/insert total
- **Batch processing** — embeddings par paquets de 100-500 pour réduire le temps d'ingestion selon la construction des fichiers.
- **Base vectorielle managée** — ChromaDB local atteint ses limites, migration vers Qdrant ou Pinecone
- **Table de transco étendue** — normalisation des variantes de nommage (`Frisquet` vs `frisquet` vs `FRISQUET`)
- **Champs techniques** — ajout de `CREATED_AT` et `UPDATED_AT` pour tracer les mises à jour de fiches
- **Hybrid search** — BM25 + vectoriel pour améliorer la précision sur les codes erreur exacts
- **Re-ranking** — cross-encoder pour affiner le top-K avant injection LLM
- **PGVector** — alternative PostgreSQL pour unifier données relationnelles et vectorielles en entreprise
- **Parsing avancé** — fiches techniques en PDF nécessiteraient Unstructured.io ou LlamaParse avant ingestion


---

*Document rédigé en phase de conception — avant tout développement.*
