
# COLDORG RAG Assistant — Brief Claude Code

## Contexte du projet
Assistant RAG pour techniciens de maintenance CVC.
Développé dans le cadre d'un test technique COLDORG.
Développeur : Gabriel SURIER — profil Data Engineer, niveau Python junior.

## Document de référence OBLIGATOIRE
Lis CLAUDE_CODE_INSTRUCTIONS.md avant toute action.
Ce fichier contient le schéma exact des collections,
la stratégie de chunking, et toutes les règles de développement.

## Règles absolues
- Respecter la nomenclature des champs : INTERV_*, FTECH_*
- Ne jamais hardcoder de valeurs — tout passe par config.py et .env
- Un fichier = une responsabilité
- Commenter chaque fonction avec une docstring en français
- Toujours demander confirmation avant de modifier un fichier existant
- Ne jamais modifier CLAUDE.md, CLAUDE_CODE_INSTRUCTIONS.md ou ARCHITECTURE.md

## Stack technique
- Python 3.10+
- ChromaDB local persistant
- sentence-transformers (paraphrase-multilingual-mpnet-base-v2)
- Groq API (défaut) / Ollama (fallback)
- Gradio

## Ordre de développement
Suivre exactement l'ordre des étapes de CLAUDE_CODE_INSTRUCTIONS.md.
Ne pas sauter d'étapes, ne pas anticiper.

## Style de code
- Français pour les commentaires et docstrings
- snake_case pour les variables et fonctions
- MAJUSCULES pour les constantes
- Pas de ligne de code sans commentaire si la logique n'est pas évidente
```