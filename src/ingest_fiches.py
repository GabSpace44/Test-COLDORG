"""
Ingestion des fiches techniques dans la collection RAG_FTECH.
Parse les fichiers TXT, chunke selon la stratégie définie, et insert dans ChromaDB.
"""

import os
import re
import hashlib
from pathlib import Path
from src.config import (
    FICHES_DIR,
    TYPE_TRANSCO_REVERSE
)
from src.embed import get_collections


def parse_filename(filename: str) -> tuple:
    """
    Parse le nom de fichier pour extraire marque, modèle et type.

    Convention : FT_Marque_Modele_TYPE.txt

    Args:
        filename: Nom du fichier (ex: "FT_Frisquet_Prestige_CGC.txt")

    Returns:
        tuple: (marque, modele, type_code)

    Raises:
        ValueError: Si le fichier ne commence pas par "FT_"
    """
    if not filename.startswith("FT_"):
        raise ValueError(
            f"Le fichier '{filename}' ne respecte pas la convention de nommage. "
            f"Attendu : FT_Marque_Modele_TYPE.txt"
        )

    # Retirer l'extension .txt
    name_without_ext = filename.replace(".txt", "")

    # Split sur les underscores
    parts = name_without_ext.split("_")

    if len(parts) < 4:
        raise ValueError(
            f"Le fichier '{filename}' ne contient pas assez de segments. "
            f"Attendu : FT_Marque_Modele_TYPE.txt"
        )

    # FT_Marque_Modele_TYPE
    # parts[0] = "FT"
    # parts[1] = Marque
    # parts[2] = Modele
    # parts[3] = TYPE
    marque = parts[1]
    modele = parts[2]
    type_code = parts[3]

    return marque, modele, type_code


def detect_section_type(section_header: str) -> str:
    """
    Détermine le type de section à partir de l'en-tête.

    Args:
        section_header: Texte de l'en-tête (ex: "--- CODES ERREUR ---")

    Returns:
        str: Code de section ("code_erreur", "probleme", "entretien", "pieces_usure")
    """
    header_upper = section_header.upper().strip()

    if "CODE" in header_upper and "ERREUR" in header_upper:
        return "code_erreur"
    elif "PROBLÈME" in header_upper or "PROBLEME" in header_upper:
        return "probleme"
    elif "ENTRETIEN" in header_upper:
        return "entretien"
    elif "PIÈCE" in header_upper and "USURE" in header_upper:
        return "pieces_usure"
    elif "PIECE" in header_upper and "USURE" in header_upper:
        return "pieces_usure"
    else:
        return "autre"


def split_by_sections(content: str) -> list:
    """
    Split le contenu d'une fiche technique en sections.

    Détecte les sections via le pattern --- XXXXX ---
    Le contenu avant le premier --- est la section "header".

    Args:
        content: Contenu complet du fichier TXT

    Returns:
        list: Liste de tuples (section_type, section_content)
    """
    # Pattern pour détecter les séparateurs de sections
    section_pattern = re.compile(r'^---\s+(.+?)\s+---$', re.MULTILINE)

    sections = []
    last_pos = 0
    current_section_type = "header"

    for match in section_pattern.finditer(content):
        # Récupérer le contenu de la section précédente
        section_content = content[last_pos:match.start()].strip()

        if section_content:  # Ne pas ajouter les sections vides
            sections.append((current_section_type, section_content))

        # Détecter le type de la nouvelle section
        section_header = match.group(1)
        current_section_type = detect_section_type(section_header)

        last_pos = match.end()

    # Ajouter la dernière section
    final_content = content[last_pos:].strip()
    if final_content:
        sections.append((current_section_type, final_content))

    return sections


def chunk_code_erreur_section(content: str) -> list:
    """
    Chunke la section "code_erreur" en un chunk par code erreur.

    Utilise une regex pour détecter chaque code erreur (format : E133 —, A05 —, etc.)
    et split le contenu en conséquence.

    Args:
        content: Contenu de la section code_erreur

    Returns:
        list: Liste de tuples (code_erreur, chunk_content)
    """
    # Pattern pour détecter les codes erreur : 1-3 caractères alphanumériques suivis de " —"
    code_pattern = re.compile(r'^([A-Z0-9]{1,3}[A-Z0-9]{1,3})\s*—', re.MULTILINE)

    chunks = []
    matches = list(code_pattern.finditer(content))

    for i, match in enumerate(matches):
        code_erreur = match.group(1)

        # Déterminer la fin du chunk (début du prochain code ou fin du contenu)
        start = match.start()
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(content)

        chunk_content = content[start:end].strip()

        if chunk_content:
            chunks.append((code_erreur, chunk_content))

    return chunks


def generate_chunk_id(marque: str, modele: str, type_code: str, chunk_index: int) -> str:
    """
    Génère un ID MD5 unique pour un chunk.

    L'ID est calculé à partir de la concaténation : marque + modele + type + index.

    Args:
        marque: Marque de l'équipement
        modele: Modèle de l'équipement
        type_code: Code type (CGC, PACAE, CM)
        chunk_index: Index du chunk (commence à 0)

    Returns:
        str: Hash MD5 en hexadécimal
    """
    chunk_str = f"{marque}{modele}{type_code}{chunk_index}"
    return hashlib.md5(chunk_str.encode()).hexdigest()


def process_fiche(filepath: str) -> list:
    """
    Traite un fichier de fiche technique et retourne la liste des chunks.

    Args:
        filepath: Chemin complet vers le fichier TXT

    Returns:
        list: Liste de tuples (chunk_id, metadata, document)
    """
    filename = os.path.basename(filepath)
    print(f"[INGEST_FICHES] Traitement de {filename}...")

    # Parse du nom de fichier
    marque, modele, type_code = parse_filename(filename)

    # Lecture du contenu
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split en sections
    sections = split_by_sections(content)

    # Chunking
    chunks = []
    chunk_index = 0

    for section_type, section_content in sections:
        if section_type == "code_erreur":
            # Rechunking de la section code_erreur
            code_chunks = chunk_code_erreur_section(section_content)

            for code_erreur, chunk_content in code_chunks:
                chunk_id = generate_chunk_id(marque, modele, type_code, chunk_index)

                metadata = {
                    "FTECH_MARQUE_CD": marque,
                    "FTECH_MODEL_CD": modele,
                    "FTECH_TYPEQ_CD": type_code,
                    "FTECH_SECTN_CD": section_type,
                    "FTECH_ERREUR_CD": code_erreur,
                    "FTECH_CHUNK_INDEX_NUM": chunk_index
                }

                chunks.append((chunk_id, metadata, chunk_content))
                chunk_index += 1

        else:
            # Une section = un chunk (header, entretien, probleme, pieces_usure)
            if section_content.strip():  # Ignorer les chunks vides
                chunk_id = generate_chunk_id(marque, modele, type_code, chunk_index)

                metadata = {
                    "FTECH_MARQUE_CD": marque,
                    "FTECH_MODEL_CD": modele,
                    "FTECH_TYPEQ_CD": type_code,
                    "FTECH_SECTN_CD": section_type,
                    "FTECH_ERREUR_CD": "",  # Pas de code erreur pour ces sections
                    "FTECH_CHUNK_INDEX_NUM": chunk_index
                }

                chunks.append((chunk_id, metadata, section_content))
                chunk_index += 1

    print(f"[INGEST_FICHES] → {len(chunks)} chunks générés pour {filename}")
    return chunks


def ingest_fiches():
    """
    Ingère toutes les fiches techniques du dossier fiches_techniques/.

    - Truncate la collection avant insertion
    - Traite tous les fichiers .txt du dossier
    - Insert tous les chunks en une seule opération batch
    - Log le nombre de chunks par fichier et le total
    """
    print(f"[INGEST_FICHES] Chargement des fiches depuis {FICHES_DIR}...")

    # Vérifier que le dossier existe
    if not os.path.exists(FICHES_DIR):
        raise FileNotFoundError(
            f"Le dossier {FICHES_DIR} n'existe pas. "
            f"Assurez-vous que les fiches techniques sont présentes."
        )

    # Récupération de la collection
    _, collection_ftech = get_collections()

    # Truncate de la collection
    print(f"[INGEST_FICHES] Suppression des documents existants dans {collection_ftech.name}...")
    existing_ids = collection_ftech.get()["ids"]
    if existing_ids:
        collection_ftech.delete(ids=existing_ids)
        print(f"[INGEST_FICHES] {len(existing_ids)} documents supprimés.")

    # Traitement de tous les fichiers .txt
    all_chunks = []
    txt_files = list(Path(FICHES_DIR).glob("*.txt"))

    if not txt_files:
        print(f"[INGEST_FICHES] ⚠ Aucun fichier .txt trouvé dans {FICHES_DIR}")
        return 0

    for filepath in txt_files:
        try:
            chunks = process_fiche(str(filepath))
            all_chunks.extend(chunks)
        except Exception as e:
            print(f"[INGEST_FICHES] ✗ Erreur lors du traitement de {filepath.name}: {e}")
            raise

    # Préparation des données pour insertion batch
    ids = [chunk[0] for chunk in all_chunks]
    metadatas = [chunk[1] for chunk in all_chunks]
    documents = [chunk[2] for chunk in all_chunks]

    # Insertion en batch
    if all_chunks:
        print(f"[INGEST_FICHES] Insertion de {len(all_chunks)} chunks dans ChromaDB...")
        collection_ftech.add(
            ids=ids,
            metadatas=metadatas,
            documents=documents
        )

        print(f"[INGEST_FICHES] ✓ {len(all_chunks)} chunks ingérés avec succès dans {collection_ftech.name}.")

    return len(all_chunks)


if __name__ == "__main__":
    # Permet de tester l'ingestion indépendamment
    ingest_fiches()
