"""
Gestion de la connexion à ChromaDB et création des collections.
Initialise le modèle d'embeddings et expose les fonctions pour accéder aux collections.
"""

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from src.config import (
    CHROMA_PATH,
    EMBEDDING_MODEL,
    COLLECTION_INTERV,
    COLLECTION_FTECH
)

# Instance globale du client ChromaDB
_chroma_client = None

# Instance globale de la fonction d'embedding
_embedding_function = None

# Collections globales
_collection_interv = None
_collection_ftech = None


def get_chroma_client():
    """
    Retourne le client ChromaDB en mode persistant.
    Initialise la connexion si ce n'est pas déjà fait.
    """
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    return _chroma_client


def get_embedding_function():
    """
    Retourne la fonction d'embedding SentenceTransformer.
    Initialise le modèle si ce n'est pas déjà fait.

    Le modèle utilisé est paraphrase-multilingual-mpnet-base-v2,
    qui produit des embeddings de qualité pour le français.
    """
    global _embedding_function
    if _embedding_function is None:
        _embedding_function = SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL
        )
    return _embedding_function


def get_collections():
    """
    Retourne un tuple (collection_interv, collection_ftech).
    Crée ou récupère les collections si elles n'existent pas.

    Returns:
        tuple: (collection RAG_INTERV, collection RAG_FTECH)
    """
    global _collection_interv, _collection_ftech

    if _collection_interv is None or _collection_ftech is None:
        client = get_chroma_client()
        embed_fn = get_embedding_function()

        # Création ou récupération de la collection des interventions
        _collection_interv = client.get_or_create_collection(
            name=COLLECTION_INTERV,
            embedding_function=embed_fn,
            metadata={"description": "Interventions terrain passées"}
        )

        # Création ou récupération de la collection des fiches techniques
        _collection_ftech = client.get_or_create_collection(
            name=COLLECTION_FTECH,
            embedding_function=embed_fn,
            metadata={"description": "Fiches techniques constructeurs"}
        )

    return _collection_interv, _collection_ftech


def reset_collections():
    """
    Supprime et recrée les deux collections (utilisé pour réinitialiser la base).
    Utile avant chaque ingestion pour repartir d'un état propre.
    """
    global _collection_interv, _collection_ftech

    client = get_chroma_client()
    embed_fn = get_embedding_function()

    # Suppression des collections si elles existent
    try:
        client.delete_collection(name=COLLECTION_INTERV)
    except Exception:
        pass  # Collection n'existe pas encore

    try:
        client.delete_collection(name=COLLECTION_FTECH)
    except Exception:
        pass  # Collection n'existe pas encore

    # Recréation des collections vides
    _collection_interv = client.create_collection(
        name=COLLECTION_INTERV,
        embedding_function=embed_fn,
        metadata={"description": "Interventions terrain passées"}
    )

    _collection_ftech = client.create_collection(
        name=COLLECTION_FTECH,
        embedding_function=embed_fn,
        metadata={"description": "Fiches techniques constructeurs"}
    )

    return _collection_interv, _collection_ftech
