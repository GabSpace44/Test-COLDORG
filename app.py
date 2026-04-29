"""
Interface Gradio pour l'assistant RAG COLDORG.
Permet d'interagir avec l'assistant via une interface de chat.
"""

import gradio as gr
from src.retrieval import retrieve
from src.generate import generate


def chat(message: str, history: list) -> str:
    """
    Fonction de chat appelée par Gradio.

    Args:
        message: Message de l'utilisateur
        history: Historique de la conversation (non utilisé pour le moment)

    Returns:
        str: Réponse de l'assistant avec les sources
    """
    try:
        # Étape 1 : Retrieval
        context = retrieve(message)

        # Vérifier si on a trouvé du contexte
        if context == "Aucun contexte pertinent trouvé dans la base de connaissances.":
            return "Veuillez m'excuser, je n'ai pas l'information que vous désirez."

        # Étape 2 : Génération
        response = generate(message, context)

        # Ajout des sources sous la réponse
        response_with_sources = f"{response}\n\n---\n**Sources utilisées :**\n```\n{context}\n```"

        return response_with_sources

    except Exception as e:
        return f"⚠ Une erreur s'est produite : {str(e)}"


def main():
    """
    Lance l'interface Gradio.
    """
    # Configuration de l'interface
    demo = gr.ChatInterface(
        fn=chat,
        title="🔧 COLDORG RAG Assistant",
        description=(
            "Assistant intelligent pour techniciens CVC.\n"
            "Posez vos questions sur les pannes, codes erreur, et procédures de maintenance."
        ),
        examples=[
            "J'ai un code E133 sur une chaudière Frisquet, que faire ?",
            "Comment entretenir une pompe à chaleur Daikin ?",
            "Quelles sont les pièces d'usure courantes sur les climatiseurs Atlantic ?"
        ],
        retry_btn=None,
        undo_btn=None,
        clear_btn="🗑️ Effacer",
    )

    # Lancement de l'application
    demo.launch()


if __name__ == "__main__":
    print("🚀 Lancement de l'interface Gradio...")
    print("📌 L'application sera accessible sur http://localhost:7860")
    print("\n⚠ Assurez-vous que les données ont été ingérées (exécutez main.py d'abord)")
    main()
