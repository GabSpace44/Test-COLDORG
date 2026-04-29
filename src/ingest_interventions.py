"""
Ingestion des interventions passées dans la collection RAG_INTERV.
Charge interventions.json, transforme selon le schéma défini, et insert dans ChromaDB.
"""

import json
from src.config import (
    INTERVENTIONS_FILE,
    TYPE_TRANSCO
)
from src.embed import get_collections


def build_document(intervention: dict) -> str:
    """
    Construit le texte du document à partir d'une intervention.

    Format attendu:
        Équipement : {equipement}
        Code erreur : {code_erreur}
        Symptôme : {symptome}
        Diagnostic : {diagnostic}
        Solution : {solution}
        Pièces remplacées : {pieces_remplacees}

    Args:
        intervention: Dictionnaire représentant une intervention

    Returns:
        str: Document formaté prêt à être indexé
    """
    # Gestion du code erreur qui peut être null
    code_erreur = intervention.get("code_erreur") or ""

    # Gestion des pièces remplacées (array -> string)
    pieces = intervention.get("pieces_remplacees", [])
    if not pieces or len(pieces) == 0:
        pieces_str = "aucune"
    else:
        pieces_str = ", ".join(pieces)

    document = f"""Équipement : {intervention['equipement']}
Code erreur : {code_erreur}
Symptôme : {intervention['symptome']}
Diagnostic : {intervention['diagnostic']}
Solution : {intervention['solution']}
Pièces remplacées : {pieces_str}"""

    return document


def transform_intervention(intervention: dict) -> tuple:
    """
    Transforme une intervention JSON en format ChromaDB (id, metadata, document).

    Args:
        intervention: Dictionnaire représentant une intervention

    Returns:
        tuple: (id, metadata, document)
    """
    # ID : utiliser l'ID de l'intervention tel quel
    interv_id = intervention["id"]

    # Construction des métadonnées selon le schéma INTERV_*
    metadata = {
        "INTERV_DT": intervention["date"],  # Format YYYY-MM-DD
        "INTERV_MARQUE_CD": intervention["marque"],
        "INTERV_TYPEQ_CD": TYPE_TRANSCO.get(
            intervention["type_equipement"],
            intervention["type_equipement"]  # Si pas dans la table, garder la valeur brute
        ),
        "INTERV_ERREUR_CD": intervention.get("code_erreur") or "",  # Gérer les null
        "INTERV_TPSMI_NUM": intervention["temps_intervention_min"],
        "INTERV_DIFCT_CD": intervention["difficulte"],
        "INTERV_TECHN_CD": intervention["technicien"]
    }

    # Construction du document texte
    document = build_document(intervention)

    return interv_id, metadata, document


def ingest_interventions():
    """
    Charge interventions.json et ingère tous les documents dans RAG_INTERV.

    - Truncate la collection avant insertion (suppression de tous les documents existants)
    - Transforme chaque intervention selon le schéma défini
    - Insert en une seule opération batch
    - Log le nombre d'interventions ingérées
    """
    print(f"[INGEST_INTERVENTIONS] Chargement de {INTERVENTIONS_FILE}...")

    # Chargement du fichier JSON
    try:
        with open(INTERVENTIONS_FILE, 'r', encoding='utf-8') as f:
            interventions = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Le fichier {INTERVENTIONS_FILE} n'existe pas. "
            f"Assurez-vous que les données sont présentes dans le dossier data/"
        )

    print(f"[INGEST_INTERVENTIONS] {len(interventions)} interventions chargées.")

    # Récupération de la collection
    collection_interv, _ = get_collections()

    # Truncate de la collection (suppression de tous les documents)
    print(f"[INGEST_INTERVENTIONS] Suppression des documents existants dans {collection_interv.name}...")
    existing_ids = collection_interv.get()["ids"]
    if existing_ids:
        collection_interv.delete(ids=existing_ids)
        print(f"[INGEST_INTERVENTIONS] {len(existing_ids)} documents supprimés.")

    # Transformation de toutes les interventions
    ids = []
    metadatas = []
    documents = []

    for intervention in interventions:
        interv_id, metadata, document = transform_intervention(intervention)
        ids.append(interv_id)
        metadatas.append(metadata)
        documents.append(document)

    # Insertion en batch
    print(f"[INGEST_INTERVENTIONS] Insertion de {len(ids)} interventions dans ChromaDB...")
    collection_interv.add(
        ids=ids,
        metadatas=metadatas,
        documents=documents
    )

    print(f"[INGEST_INTERVENTIONS] ✓ {len(ids)} interventions ingérées avec succès dans {collection_interv.name}.")
    return len(ids)


if __name__ == "__main__":
    # Permet de tester l'ingestion indépendamment
    ingest_interventions()
