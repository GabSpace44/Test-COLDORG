"""
Gestion de la recherche vectorielle et fusion des résultats.
Détecte les entités dans la question, interroge ChromaDB, et construit le contexte final.
"""

import re
from src.config import (
    TOP_K_INTERV,
    TOP_K_FTECH,
    DISTANCE_THRESHOLD,
    MARQUES_CONNUES
)
from src.embed import get_collections


def detect_marque(question: str) -> str:
    """
    Détecte une marque connue dans la question.

    Args:
        question: Question de l'utilisateur

    Returns:
        str: Nom de la marque détectée ou None
    """
    question_lower = question.lower()

    for marque in MARQUES_CONNUES:
        # Recherche insensible à la casse et aux espaces
        if marque.lower() in question_lower:
            return marque

    return None


def detect_code_erreur(question: str) -> str:
    """
    Détecte un code erreur dans la question via regex.

    Pattern : 1 à 3 caractères alphanumériques suivis de 1 à 3 caractères alphanumériques
    (ex: E133, A05, F12, etc.)

    Args:
        question: Question de l'utilisateur

    Returns:
        str: Code erreur détecté ou None
    """
    # Pattern pour les codes erreur (ex: E133, A05, F12)
    pattern = re.compile(r'\b([A-Z][A-Z0-9]{1,4})\b', re.IGNORECASE)
    match = pattern.search(question)

    if match:
        return match.group(1).upper()

    return None


def build_filters(question: str) -> tuple:
    """
    Construit les filtres metadata pour ChromaDB basés sur les entités détectées.

    Args:
        question: Question de l'utilisateur

    Returns:
        tuple: (filtre_interv, filtre_ftech)
    """
    marque = detect_marque(question)
    code_erreur = detect_code_erreur(question)

    filtre_interv = None
    filtre_ftech = None

    # Filtrage par marque pour les interventions
    if marque:
        filtre_interv = {"INTERV_MARQUE_CD": {"$eq": marque}}

    # Filtrage par marque ou code erreur pour les fiches techniques
    if marque and code_erreur:
        # Les deux critères : marque ET code erreur
        filtre_ftech = {
            "$and": [
                {"FTECH_MARQUE_CD": {"$eq": marque}},
                {"FTECH_ERREUR_CD": {"$eq": code_erreur}}
            ]
        }
    elif marque:
        # Seulement la marque
        filtre_ftech = {"FTECH_MARQUE_CD": {"$eq": marque}}
    elif code_erreur:
        # Seulement le code erreur
        filtre_ftech = {"FTECH_ERREUR_CD": {"$eq": code_erreur}}

    return filtre_interv, filtre_ftech


def filter_by_distance(results: dict, threshold: float) -> dict:
    """
    Filtre les résultats ChromaDB en rejetant les chunks dont la distance > threshold.

    Args:
        results: Résultats retournés par collection.query()
        threshold: Seuil de distance maximum acceptable

    Returns:
        dict: Résultats filtrés (même structure que l'entrée)
    """
    if not results or not results.get("distances"):
        return results

    # ChromaDB retourne des listes de listes (une par query)
    # Ici on fait une seule query donc on prend le premier élément
    distances = results["distances"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    ids = results["ids"][0]

    # Filtrage
    filtered_ids = []
    filtered_documents = []
    filtered_metadatas = []
    filtered_distances = []

    for i, distance in enumerate(distances):
        if distance <= threshold:
            filtered_ids.append(ids[i])
            filtered_documents.append(documents[i])
            filtered_metadatas.append(metadatas[i])
            filtered_distances.append(distance)

    # Reconstruction du dictionnaire de résultats
    return {
        "ids": [filtered_ids],
        "documents": [filtered_documents],
        "metadatas": [filtered_metadatas],
        "distances": [filtered_distances]
    }


def format_context_interv(results: dict) -> str:
    """
    Formate les résultats des interventions selon le template défini.

    Format :
        [{INTERV_ID}] Équipement : {INTERV_MARQUE_CD} | Technicien : {INTERV_TECHN_CD} | Durée : {INTERV_TPSMI_NUM}min
        {document}

    Args:
        results: Résultats ChromaDB filtrés

    Returns:
        str: Contexte formaté pour les interventions
    """
    if not results or not results.get("documents") or not results["documents"][0]:
        return ""

    ids = results["ids"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    context_parts = ["SOURCE TERRAIN (interventions passées) :"]

    for i, doc_id in enumerate(ids):
        metadata = metadatas[i]
        document = documents[i]

        header = (
            f"[{doc_id}] "
            f"Équipement : {metadata.get('INTERV_MARQUE_CD', 'N/A')} | "
            f"Technicien : {metadata.get('INTERV_TECHN_CD', 'N/A')} | "
            f"Durée : {metadata.get('INTERV_TPSMI_NUM', 'N/A')}min"
        )

        context_parts.append("---")
        context_parts.append(header)
        context_parts.append(document)
        context_parts.append("---")

    return "\n".join(context_parts)


def format_context_ftech(results: dict) -> str:
    """
    Formate les résultats des fiches techniques selon le template défini.

    Format :
        [{FTECH_MARQUE_CD} {FTECH_MODEL_CD} — {FTECH_SECTN_CD} — {FTECH_ERREUR_CD}]
        {document}

    Args:
        results: Résultats ChromaDB filtrés

    Returns:
        str: Contexte formaté pour les fiches techniques
    """
    if not results or not results.get("documents") or not results["documents"][0]:
        return ""

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    context_parts = ["SOURCE DOCUMENTAIRE (fiche technique) :"]

    for i, metadata in enumerate(metadatas):
        document = documents[i]

        # Construction du header avec le code erreur si présent
        erreur_str = metadata.get('FTECH_ERREUR_CD', '')
        if erreur_str:
            erreur_str = f" — {erreur_str}"

        header = (
            f"[{metadata.get('FTECH_MARQUE_CD', 'N/A')} "
            f"{metadata.get('FTECH_MODEL_CD', 'N/A')} — "
            f"{metadata.get('FTECH_SECTN_CD', 'N/A')}{erreur_str}]"
        )

        context_parts.append("---")
        context_parts.append(header)
        context_parts.append(document)
        context_parts.append("---")

    return "\n".join(context_parts)


def retrieve(question: str) -> str:
    """
    Effectue la recherche vectorielle et retourne le contexte fusionné.

    Étapes :
    1. Détection d'entités dans la question (marque, code erreur)
    2. Construction des filtres metadata
    3. Recherche parallèle dans RAG_INTERV et RAG_FTECH
    4. Filtrage par seuil de distance
    5. Construction du contexte fusionné

    Args:
        question: Question de l'utilisateur

    Returns:
        str: Contexte fusionné prêt à être injecté dans le prompt LLM
    """
    # Récupération des collections
    collection_interv, collection_ftech = get_collections()

    # Construction des filtres
    filtre_interv, filtre_ftech = build_filters(question)

    # Recherche dans RAG_INTERV
    try:
        results_interv = collection_interv.query(
            query_texts=[question],
            n_results=TOP_K_INTERV,
            where=filtre_interv
        )
    except Exception as e:
        print(f"[RETRIEVAL] Avertissement : erreur lors de la recherche dans RAG_INTERV : {e}")
        results_interv = None

    # Recherche dans RAG_FTECH
    try:
        results_ftech = collection_ftech.query(
            query_texts=[question],
            n_results=TOP_K_FTECH,
            where=filtre_ftech
        )
    except Exception as e:
        print(f"[RETRIEVAL] Avertissement : erreur lors de la recherche dans RAG_FTECH : {e}")
        results_ftech = None

    # Filtrage par distance
    if results_interv:
        results_interv = filter_by_distance(results_interv, DISTANCE_THRESHOLD)

    if results_ftech:
        results_ftech = filter_by_distance(results_ftech, DISTANCE_THRESHOLD)

    # Construction du contexte fusionné
    context_parts = []

    context_interv = format_context_interv(results_interv)
    if context_interv:
        context_parts.append(context_interv)

    context_ftech = format_context_ftech(results_ftech)
    if context_ftech:
        context_parts.append(context_ftech)

    if not context_parts:
        return "Aucun contexte pertinent trouvé dans la base de connaissances."

    return "\n\n".join(context_parts)
