# COLDORG RAG Assistant 🔧

Assistant RAG (Retrieval-Augmented Generation) pour techniciens de maintenance CVC.

Développé par **Gabriel SURIER** dans le cadre d'un test technique COLDORG.

## Préambule 
Ce POC a été développé en alliant conception technique personnelle et assistance par IA. La première phase a été consacrée à la définition de l'architecture globale et à l'élaboration d'un mapping de bout en bout, incluant une structuration rigoureuse des métadonnées. L'IA a été activement sollicitée à chaque étape pour explorer l'état de l'art des architectures RAG et identifier les meilleures approches disponibles. Cette démarche itérative a permis de cadrer précisément le périmètre technique avant toute implémentation, en s'appuyant sur une veille technologique assistée.
Les fichiers de spécifications ont ensuite été rédigés afin de formaliser les intentions techniques et de guider l'implémentation. Claude Code a été utilisé comme assistant technique, permettant d'aboutir à une interface Gradio et des appels API Groq fonctionnels en 4 à 5 itérations.
L'intelligence artificielle a été mobilisée comme outil d'accélération du développement et d'exploration des choix techniques. Les arbitrages finaux, à savoir la validation des approches, la priorisation des contraintes et la cohérence d'ensemble, ont été assumés de manière autonome.
---

## 🎯 Objectif

Permettre à un technicien CVC de poser une question en langage naturel et d'obtenir :
- Un diagnostic probable avec le code erreur
- Une procédure de résolution recommandée
- Les pièces potentielles à prévoir
- Des interventions similaires passées

Le système s'appuie sur :
- **30 interventions passées** (historique terrain)
- **4 fiches techniques** d'équipements constructeurs

---

## 🛠 Stack technique

| Composant | Technologie |
|---|---|
| Base vectorielle | ChromaDB (local, persistant) |
| Embeddings | sentence-transformers (`paraphrase-multilingual-mpnet-base-v2`) |
| LLM | Groq API (Llama 3.1 8B Instant) ou Ollama (fallback) |
| Interface | Gradio |
| Langage | Python 3.10+ |

---

## 📦 Installation

### 1. Cloner le projet

```bash
git clone <url-du-repo>
cd coldorg-rag
```

### 2. Créer un environnement virtuel

```bash
python3 -m venv venv
source venv/bin/activate  # Sur Windows : venv\Scripts\activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement

Copier `.env.example` vers `.env` :

```bash
cp .env.example .env
```

Éditer `.env` et configurer votre clé API Groq :

```env
LLM_PROVIDER=groq
GROQ_API_KEY=votre_clé_api_ici
```

> **Obtenir une clé API Groq :** Créez un compte gratuit sur [console.groq.com](https://console.groq.com)

**Alternative Ollama (local) :**

Si vous préférez utiliser Ollama en local (pas de clé API requise) :

```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=mistral
```

Assurez-vous qu'Ollama est installé et que le modèle est disponible :

```bash
ollama pull mistral
```

---

## 🚀 Utilisation

### Option 1 : Pipeline CLI (tests automatiques)

Exécute l'ingestion complète et teste le système sur les questions de référence.

```bash
python3 main.py
```

**Ce script :**
1. Ingère les interventions dans ChromaDB
2. Ingère les fiches techniques dans ChromaDB
3. Teste le système sur les 5 questions de `tests/questions_test.json`
4. Affiche les contextes récupérés et les réponses générées

### Option 2 : Interface Gradio (chat interactif)

Lance une interface web pour interagir avec l'assistant.

```bash
python app.py
```

Ouvrez votre navigateur sur [http://localhost:7860](http://localhost:7860)

**⚠ Important :** Exécutez `main.py` au moins une fois avant de lancer `app.py` pour ingérer les données.

---

## 📁 Structure du projet

```
coldorg-rag/
│
├── data/                          # Données sources
│   ├── interventions.json         # 30 interventions passées
│   └── fiches_techniques/         # Fiches techniques constructeurs
│       ├── FT_Frisquet_Prestige_CGC.txt
│       ├── FT_Atlantic_Idea_CM.txt
│       ├── FT_Daikin_Altherma_PACAE.txt
│       └── FT_SaunierDuval_ThemaplusCondens_CGC.txt
│
├── src/                           # Code source
│   ├── config.py                  # Configuration centralisée
│   ├── embed.py                   # Connexion ChromaDB et embeddings
│   ├── ingest_interventions.py   # Ingestion des interventions
│   ├── ingest_fiches.py           # Chunking et ingestion des fiches
│   ├── retrieval.py               # Recherche vectorielle
│   └── generate.py                # Génération de réponses LLM
│
├── tests/                         # Tests
│   └── questions_test.json        # Questions de référence
│
├── chroma_db/                     # Base vectorielle (généré)
│
├── app.py                         # Interface Gradio
├── main.py                        # Pipeline CLI
├── .env                           # Configuration locale (non commité)
├── .env.example                   # Template de configuration
├── requirements.txt               # Dépendances Python
├── schema.md                      # Documentation du schéma
└── README.md                      # Ce fichier
```

---

## 🔍 Exemples de questions

```
J'ai un code E133 sur une chaudière Frisquet, que faire ?
Comment entretenir une pompe à chaleur Daikin ?
Quelles sont les pièces d'usure courantes sur les climatiseurs Atlantic ?
La pression de ma chaudière Saunier Duval est trop basse, comment la remonter ?
Mon client se plaint de bruits bizarres sur sa PAC, des idées ?
```

---

## 📊 Collections ChromaDB

Le système utilise deux collections :

### RAG_INTERV (Interventions)
- **30 documents** (une intervention = un document)
- Métadonnées : date, marque, type équipement, code erreur, durée, difficulté, technicien
- Document : concaténation équipement + symptôme + diagnostic + solution + pièces

### RAG_FTECH (Fiches techniques)
- **~50-80 chunks** (chunks générés automatiquement par section et code erreur)
- Métadonnées : marque, modèle, type équipement, section, code erreur, index
- Document : texte brut du chunk

Consultez `schema.md` pour le détail complet du schéma.

---

## ⚙️ Configuration avancée

Toutes les configurations sont dans `.env` :

```env
# Provider LLM
LLM_PROVIDER=groq              # "groq" ou "ollama"
GROQ_API_KEY=your_key_here     # Clé API Groq
OLLAMA_MODEL=mistral           # Modèle Ollama (si LLM_PROVIDER=ollama)

# Embeddings
EMBEDDING_MODEL=paraphrase-multilingual-mpnet-base-v2

# ChromaDB
CHROMA_PATH=./chroma_db        # Chemin de la base vectorielle

# Retrieval
TOP_K_INTERV=2                 # Nombre d'interventions à récupérer
TOP_K_FTECH=1                  # Nombre de chunks de fiches à récupérer
DISTANCE_THRESHOLD=0.8         # Seuil de rejet des chunks non pertinents
MAX_CHUNK_TOKENS=200           # Taille max d'un chunk (référence)
```

---

## 🧪 Tests

Pour tester manuellement chaque composant :

```bash
# Ingestion des interventions uniquement
python3 src/ingest_interventions.py

# Ingestion des fiches techniques uniquement
python3 src/ingest_fiches.py
```

---

## 📚 Documentation

- **ARCHITECTURE.md** — Documentation complète de l'architecture
- **CLAUDE_CODE_INSTRUCTIONS.md** — Instructions de développement
- **CLAUDE.md** — Contexte de développement

---

## 🐛 Troubleshooting

### Erreur : "GROQ_API_KEY n'est pas configurée"

➜ Assurez-vous d'avoir créé le fichier `.env` et d'y avoir ajouté votre clé API Groq.

### Erreur : "Le fichier interventions.json n'existe pas"

➜ Vérifiez que les données sources sont présentes dans `data/interventions.json` et `data/fiches_techniques/*.txt`

### Erreur : "Impossible de se connecter à Ollama"

➜ Si vous utilisez `LLM_PROVIDER=ollama`, assurez-vous qu'Ollama est démarré :

```bash
ollama serve
ollama pull mistral
```

### L'interface Gradio ne retourne rien

➜ Exécutez d'abord `python3 main.py` pour ingérer les données dans ChromaDB.

---

## 📈 Pistes d'amélioration

- **Hybrid search** — combiner recherche vectorielle et BM25
- **Re-ranking** — affiner les résultats avec un cross-encoder
- **Détection d'entités robuste** — utiliser spaCy pour l'extraction de marques et codes erreurs
- **Gestion multi-turn** — intégrer une mémoire de conversation
- **Évaluation automatique** — scorer la qualité des réponses générées
- **Amélioration de l'interface** — enrichir Gradio avec un encart de paramétrage du prompt
- **Expérience utilisateur** — ajouter un bouton d'arrêt propre de l'interface
- **Résultats du retrieval** — afficher le top-1 des fiches techniques dans la réponse finale
---

## 👤 Auteur

**Gabriel SURIER**  
Profil : Ingénieur Data  


---

## 📄 Licence

Projet réalisé dans le cadre d'un test technique pour COLDORG.
