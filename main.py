"""
Point d'entrée pour le pipeline RAG COLDORG.
Exécute l'ingestion complète et affiche les résultats des questions de test dans Gradio.
"""

import json
import os
import gradio as gr
from src.config import TESTS_FILE
from src.ingest_interventions import ingest_interventions
from src.ingest_fiches import ingest_fiches
from src.retrieval import retrieve
from src.generate import generate


def print_separator(title: str = ""):
    """Affiche un séparateur visuel."""
    if title:
        print(f"\n{'=' * 80}")
        print(f" {title}")
        print(f"{'=' * 80}\n")
    else:
        print(f"{'=' * 80}\n")


def run_ingestion():
    """
    Exécute l'ingestion des données et retourne un message de statut.

    Returns:
        str: Message de statut de l'ingestion
    """
    status_messages = []

    print_separator("COLDORG RAG — Pipeline d'ingestion")

    # Configuration
    print_separator("Paramètres de configuration")
    config_info = f"""
    LLM_PROVIDER: {os.getenv('LLM_PROVIDER')}
    EMBEDDING_MODEL: {os.getenv('EMBEDDING_MODEL')}
    OLLAMA_MODEL: {os.getenv('OLLAMA_MODEL')}
    """
    print(config_info)
    status_messages.append("**Configuration:**\n" + config_info)

    # Ingestion des interventions
    print_separator("ÉTAPE 1/2 : Ingestion des interventions")
    try:
        nb_interv = ingest_interventions()
        msg = f"✓ {nb_interv} interventions ingérées avec succès."
        print(f"\n{msg}\n")
        status_messages.append(msg)
    except Exception as e:
        msg = f"✗ Erreur lors de l'ingestion des interventions : {e}"
        print(f"\n{msg}\n")
        status_messages.append(msg)
        return "\n\n".join(status_messages)

    # Ingestion des fiches techniques
    print_separator("ÉTAPE 2/2 : Ingestion des fiches techniques")
    try:
        nb_chunks = ingest_fiches()
        msg = f"✓ {nb_chunks} chunks de fiches techniques ingérés avec succès."
        print(f"\n{msg}\n")
        status_messages.append(msg)
    except Exception as e:
        msg = f"✗ Erreur lors de l'ingestion des fiches : {e}"
        print(f"\n{msg}\n")
        status_messages.append(msg)
        return "\n\n".join(status_messages)

    print_separator("Ingestion terminée")
    status_messages.append("\n**Ingestion terminée avec succès !**")
    return "\n\n".join(status_messages)


def test_questions():
    """
    Teste le RAG sur les questions de référence et retourne les résultats.

    Returns:
        list: Liste de tuples (question, contexte, réponse)
    """
    results = []

    print_separator("Tests sur les questions de référence")

    # Chargement des questions de test
    if not os.path.exists(TESTS_FILE):
        error_msg = f"⚠ Le fichier {TESTS_FILE} n'existe pas."
        print(error_msg)
        return [(error_msg, "", "")]

    try:
        with open(TESTS_FILE, 'r', encoding='utf-8') as f:
            questions_data = json.load(f)
    except Exception as e:
        error_msg = f"✗ Erreur lors du chargement de {TESTS_FILE} : {e}"
        print(error_msg)
        return [(error_msg, "", "")]

    # Traitement de chaque question
    for i, item in enumerate(questions_data, 1):
        question = item.get("question", "")

        if not question:
            print(f"⚠ Question {i} vide, ignorée.")
            continue

        print_separator(f"Question {i}/{len(questions_data)}")
        print(f"Q: {question}\n")

        # Retrieval
        print("[Retrieval] Recherche de contexte pertinent...")
        try:
            context = retrieve(question)
            print(f"\n{context}\n")
        except Exception as e:
            error_msg = f"✗ Erreur lors du retrieval : {e}"
            print(error_msg)
            results.append((question, error_msg, ""))
            continue

        # Génération
        print("[Génération] Appel au LLM...")
        try:
            response = generate(question, context)
            print(f"\n{response}\n")
            results.append((question, context, response))
        except Exception as e:
            error_msg = f"✗ Erreur lors de la génération : {e}"
            print(error_msg)
            results.append((question, context, error_msg))
            continue

    print_separator("Tests terminés")
    return results


def create_gradio_interface():
    """
    Crée et lance l'interface Gradio pour afficher les résultats des tests.
    """

    def run_pipeline_generator():
        """
        Générateur qui exécute le pipeline et yield des mises à jour progressives.
        Permet d'arrêter le pipeline avec le bouton Stop.
        """
        # Étape 1 : Ingestion
        yield "<div style='color: #333;'><h2>⏳ Étape 1/2 : Ingestion en cours...</h2><p>Veuillez patienter...</p></div>"

        ingestion_status = run_ingestion()

        results_html = f"""
        <div style="color: #333;">
            <h2>📊 Résultats de l'ingestion</h2>
            <pre style="color: #333; background: #f5f5f5; padding: 10px; border-radius: 5px;">{ingestion_status}</pre>
        </div>
        """
        yield results_html

        # Étape 2 : Tests - Chargement des questions
        results_html += "<div style='color: #333;'><h2>🧪 Tests sur les questions de référence</h2></div>"
        yield results_html

        # Chargement des questions de test
        if not os.path.exists(TESTS_FILE):
            error_msg = f"⚠ Le fichier {TESTS_FILE} n'existe pas."
            results_html += f"<p style='color: red;'>{error_msg}</p>"
            yield results_html
            return

        try:
            with open(TESTS_FILE, 'r', encoding='utf-8') as f:
                questions_data = json.load(f)
        except Exception as e:
            error_msg = f"✗ Erreur lors du chargement de {TESTS_FILE} : {e}"
            results_html += f"<p style='color: red;'>{error_msg}</p>"
            yield results_html
            return

        # Traitement de chaque question individuellement (permet l'interruption)
        for i, item in enumerate(questions_data, 1):
            question = item.get("question", "")

            if not question:
                continue

            # Afficher "en cours de traitement"
            results_html += f"<div style='color: #333; padding: 10px; background: #fff3cd; border-radius: 5px; margin: 10px 0;'>⏳ Traitement de la question {i}/{len(questions_data)}...</div>"
            yield results_html

            # Retrieval
            try:
                context = retrieve(question)
            except Exception as e:
                error_msg = f"✗ Erreur lors du retrieval : {e}"
                context = error_msg

            # Génération
            try:
                response = generate(question, context)
            except Exception as e:
                response = f"✗ Erreur lors de la génération : {e}"

            # Retirer le message "en cours" et afficher le résultat
            # Trouver et supprimer le dernier div "en cours"
            last_div_start = results_html.rfind('<div style=\'color: #333; padding: 10px; background: #fff3cd;')
            if last_div_start != -1:
                last_div_end = results_html.find('</div>', last_div_start) + 6
                results_html = results_html[:last_div_start] + results_html[last_div_end:]

            # Ajouter le résultat formaté
            results_html += f"""
            <div style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; color: #333;">
                <h3 style="color: #FFFFFF;">Question {i}/{len(questions_data)}</h3>
                <p style="color: #FFFFFF;"><strong>Q:</strong> {question}</p>

                <details>
                    <summary style="color: #333; cursor: pointer;"><strong>📚 Contexte récupéré (cliquez pour afficher)</strong></summary>
                    <pre style="background: #f5f5f5; padding: 10px; border-radius: 3px; white-space: pre-wrap; color: #000;">{context}</pre>
                </details>

                <p style="color: #333;"><strong>💡 Réponse générée:</strong></p>
                <div style="background: #e8f5e9; padding: 10px; border-radius: 3px; color: #000;">
                    {response.replace(chr(10), '<br>')}
                </div>
            </div>
            """
            # Yield après chaque question pour permettre l'arrêt
            yield results_html

        # Ajout d'un message final
        results_html += """
        <div style="background: #333; border: 1px solid #c3e6cb; padding: 15px; border-radius: 5px; margin-top: 20px; color: #155724;">
            <strong>✅ Pipeline terminé avec succès !</strong>
        </div>
        """
        yield results_html

    # Interface Gradio
    with gr.Blocks(title="COLDORG RAG - Pipeline de test", theme=gr.themes.Soft()) as demo:
        gr.Markdown("""
        # 🔧 COLDORG RAG Assistant - Pipeline de test

        Ce pipeline exécute :
        1. L'ingestion des interventions et fiches techniques dans ChromaDB
        2. Les tests sur les questions de référence
        3. Affichage des résultats avec contexte et réponse générée
        """)

        with gr.Row():
            run_button = gr.Button("▶️ Lancer le pipeline complet", variant="primary", size="lg")
            stop_button = gr.Button("⏹️ Arrêter", variant="stop", size="lg")

        output = gr.HTML(label="Résultats")

        # Configuration des événements
        run_event = run_button.click(fn=run_pipeline_generator, outputs=output)
        stop_button.click(fn=None, cancels=[run_event])

        gr.Markdown("""
        ---
        **Note :** Le pipeline peut prendre quelques secondes à quelques minutes selon la taille des données et le LLM utilisé.
        Utilisez le bouton **Arrêter** pour interrompre le pipeline en cours d'exécution.
        """)

    return demo


def main():
    """
    Point d'entrée principal : lance l'interface Gradio.
    """
    print("🚀 Lancement de l'interface Gradio pour le pipeline de test...")
    print("📌 L'application sera accessible sur http://localhost:7860")

    demo = create_gradio_interface()
    demo.launch()


if __name__ == "__main__":
    main()
