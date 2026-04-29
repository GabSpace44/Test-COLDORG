"""
Configuration centralisée pour l'assistant RAG COLDORG.
Charge toutes les variables d'environnement et définit les constantes globales.
"""

import os
from dotenv import load_dotenv

# Chargement du fichier .env
load_dotenv()

# ============================================================================
# CONFIGURATION LLM
# ============================================================================

# Provider LLM : "groq" ou "ollama"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")

# Clé API Groq (nécessaire si LLM_PROVIDER=groq)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Modèle Ollama à utiliser (nécessaire si LLM_PROVIDER=ollama)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")

# ============================================================================
# CONFIGURATION EMBEDDINGS ET CHROMADB
# ============================================================================

# Modèle d'embeddings multilingue pour encoder les chunks et les questions
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-mpnet-base-v2")

# Chemin de persistance de la base vectorielle ChromaDB
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")

# ============================================================================
# PARAMETRES DE RECHERCHE VECTORIELLE
# ============================================================================

# Nombre de chunks à récupérer dans la collection RAG_INTERV (interventions)
TOP_K_INTERV = int(os.getenv("TOP_K_INTERV", "2"))

# Nombre de chunks à récupérer dans la collection RAG_FTECH (fiches techniques)
TOP_K_FTECH = int(os.getenv("TOP_K_FTECH", "1"))

# Seuil de distance cosine au-delà duquel un chunk est rejeté (0.0 = identique, 2.0 = opposé)
DISTANCE_THRESHOLD = float(os.getenv("DISTANCE_THRESHOLD", "0.8"))

# Taille maximale d'un chunk en tokens (pour référence future)
MAX_CHUNK_TOKENS = int(os.getenv("MAX_CHUNK_TOKENS", "200"))

# ============================================================================
# NOMS DES COLLECTIONS CHROMADB
# ============================================================================

# Collection contenant les interventions passées
COLLECTION_INTERV = "RAG_INTERV"

# Collection contenant les fiches techniques
COLLECTION_FTECH = "RAG_FTECH"

# ============================================================================
# TABLE DE TRANSCODIFICATION DES TYPES D'EQUIPEMENTS
# ============================================================================

# Permet de normaliser les types d'équipements entre le format JSON et le format code
TYPE_TRANSCO = {
    "chaudiere_gaz": "CGC",
    "pac_air_eau": "PACAE",
    "climatisation": "CM"
}

# Table inverse pour obtenir le libellé complet depuis le code
TYPE_TRANSCO_REVERSE = {
    "CGC": "chaudière gaz à condensation",
    "PACAE": "pompe à chaleur air/eau",
    "CM": "climatiseur mural"
}

# ============================================================================
# MARQUES CONNUES (pour détection d'entités dans les questions)
# ============================================================================

MARQUES_CONNUES = ["Frisquet", "Daikin", "Atlantic", "Saunier Duval", "SaunierDuval"]

# ============================================================================
# CHEMINS DES FICHIERS DE DONNEES
# ============================================================================

DATA_DIR = "./data"
INTERVENTIONS_FILE = os.path.join(DATA_DIR, "interventions.json")
FICHES_DIR = os.path.join(DATA_DIR, "fiches_techniques")
TESTS_FILE = "./tests/questions_test.json"
