"""
Gestion de la construction du prompt et de l'appel au LLM.
Supporte Groq API et Ollama en fonction de la configuration.
"""

from src.config import (
    LLM_PROVIDER,
    GROQ_API_KEY,
    OLLAMA_MODEL
)


# Template du prompt système — NE PAS MODIFIER
SYSTEM_PROMPT_TEMPLATE = """## ROLE
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
{question}"""


def build_prompt(question: str, context: str) -> str:
    """
    Construit le prompt complet en injectant le contexte et la question.

    Args:
        question: Question de l'utilisateur
        context: Contexte récupéré par le retrieval

    Returns:
        str: Prompt complet prêt à être envoyé au LLM
    """
    return SYSTEM_PROMPT_TEMPLATE.format(
        context=context,
        question=question
    )


def call_groq(prompt: str) -> str:
    """
    Appelle l'API Groq avec le prompt construit.

    Args:
        prompt: Prompt complet

    Returns:
        str: Réponse générée par le LLM

    Raises:
        ValueError: Si GROQ_API_KEY n'est pas configuré
    """
    if not GROQ_API_KEY or GROQ_API_KEY == "your_key_here":
        raise ValueError(
            "GROQ_API_KEY n'est pas configurée. "
            "Ajoutez votre clé API dans le fichier .env : GROQ_API_KEY=votre_clé"
        )

    from groq import Groq

    client = Groq(api_key=GROQ_API_KEY)

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000
    )

    return response.choices[0].message.content


def call_ollama(prompt: str) -> str:
    """
    Appelle Ollama en local avec le prompt construit.

    Args:
        prompt: Prompt complet

    Returns:
        str: Réponse générée par le LLM

    Raises:
        ConnectionError: Si Ollama n'est pas accessible
    """
    try:
        import ollama
    except ImportError:
        raise ImportError(
            "Le package 'ollama' n'est pas installé. "
            "Installez-le avec : pip install ollama"
        )

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        return response["message"]["content"]

    except Exception as e:
        raise ConnectionError(
            f"Impossible de se connecter à Ollama : {e}\n"
            f"Assurez-vous qu'Ollama est démarré et que le modèle '{OLLAMA_MODEL}' est disponible."
        )


def generate(question: str, context: str) -> str:
    """
    Construit le prompt, appelle le LLM, et retourne la réponse.

    Sélectionne automatiquement le provider (Groq ou Ollama) selon la configuration.

    Args:
        question: Question de l'utilisateur
        context: Contexte récupéré par retrieval.retrieve()

    Returns:
        str: Réponse générée par le LLM

    Raises:
        ValueError: Si LLM_PROVIDER n'est pas reconnu
    """
    # Construction du prompt
    prompt = build_prompt(question, context)

    # Appel au LLM selon le provider configuré
    if LLM_PROVIDER == "groq":
        return call_groq(prompt)
    elif LLM_PROVIDER == "ollama":
        return call_ollama(prompt)
    else:
        raise ValueError(
            f"LLM_PROVIDER '{LLM_PROVIDER}' non reconnu. "
            f"Valeurs acceptées : 'groq' ou 'ollama'"
        )
