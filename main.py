"""
CryptoEdu Assistant — Interface CLI
Adapté depuis main.py du projet Agent_Cyber_Career_Compass.

Lancement : python main.py

Gestion de la cascade :
  - RateLimitError (429) → switch automatique vers le modèle suivant
  - NotFoundError  (404) → switch automatique vers le modèle suivant
  - Cascade épuisée      → message d'erreur clair
"""

import asyncio
from agents import Runner
from agents.exceptions import InputGuardrailTripwireTriggered
from openai import RateLimitError, NotFoundError, BadRequestError, APIStatusError, APIConnectionError
import config
from core.crypto_manager import manager

BANNER = """
╔═══════════════════════════════════════════════════════════════╗
║             CryptoEdu Assistant                               ║
║   Éducation · Marché · Risques · Débutants                   ║
╚═══════════════════════════════════════════════════════════════╝
Posez votre question en français (ou 'quit' pour quitter)

Exemples :
  > Par où commencer si je veux me lancer dans les cryptos ?
  > C'est quoi un wallet et comment le sécuriser ?
  > Quel est le prix du Bitcoin aujourd'hui ?
  > Quelle différence entre un CEX et un DEX ?
  > Quels sont les risques des cryptomonnaies ?
  > Comment fonctionne la blockchain ?
"""

REFUSED_MESSAGE = (
    "Je suis le CryptoEdu Assistant — spécialisé dans l'éducation aux cryptomonnaies.\n"
    "Je ne peux pas répondre à cette demande.\n\n"
    "Ce que je peux faire :\n"
    "  • Expliquer comment fonctionnent les cryptomonnaies\n"
    "  • Vous guider pour démarrer en toute sécurité\n"
    "  • Présenter les données de marché à titre informatif\n"
    "  • Vous informer sur les risques et les arnaques à éviter\n\n"
    "Je ne donne jamais de conseils d'investissement."
)

CASCADE_EXHAUSTED_MESSAGE = (
    "Tous les modèles de la cascade sont temporairement indisponibles "
    "(rate limit ou erreur provider).\n"
    "Patientez 1-2 minutes et réessayez.\n"
    "Conseil : le free tier OpenRouter est limité à ~20 req/min par modèle."
)


async def chat(query: str) -> str:
    """
    Envoie la question au manager avec gestion automatique de la cascade.

    Analogie : comme un central téléphonique qui essaie une ligne,
    et si elle est occupée, passe automatiquement à la suivante.
    """
    while True:
        try:
            result = await Runner.run(manager, input=query, max_turns=20)
            return result.final_output

        except InputGuardrailTripwireTriggered:
            return REFUSED_MESSAGE

        except (RateLimitError, NotFoundError, BadRequestError, APIStatusError, APIConnectionError) as e:
            # Le modèle actuel est rate-limité, introuvable, ou ne supporte pas
            # le format des tool calls (ex: StepFun via openrouter/free)
            if isinstance(e, RateLimitError):
                error_type = "Rate limit (429)"
            elif isinstance(e, NotFoundError):
                error_type = "Modèle introuvable (404)"
            else:
                error_type = "Format non supporté (400)"
            current_info = config.get_current_model_info()
            print(f"\n[Cascade] {error_type} sur {current_info['main_model']} → tentative switch...")

            switched = config.switch_to_next_model()
            if not switched:
                return CASCADE_EXHAUSTED_MESSAGE

            new_info = config.get_current_model_info()
            print(f"[Cascade] Switch OK → {new_info['main_model']} ({new_info['main_position']})\n")
            # On reboucle avec le nouveau modèle

        except Exception as e:
            return f"Erreur inattendue : {type(e).__name__}: {e}"


def main():
    print(BANNER)
    # Affiche le modèle actif au démarrage
    info = config.get_current_model_info()
    print(f"[Modèle actif] {info['main_model']}\n")

    while True:
        try:
            query = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBonne continuation dans votre apprentissage crypto !")
            break

        if not query:
            continue
        if query.lower() in ("quit", "exit", "q"):
            print("Bonne continuation dans votre apprentissage crypto !")
            break

        print("\nAnalyse en cours...\n")
        response = asyncio.run(chat(query))

        # Garde-fou : réponse vide (peut arriver si openrouter/free choisit
        # un modèle qui ne supporte pas le tool calling)
        if not response or not response.strip():
            response = (
                "Le modèle de secours n'a pas pu générer de réponse "
                "(tool calling probablement non supporté).\n"
                "Réessayez dans quelques secondes."
            )

        print(response)

        # Affiche le modèle utilisé (utile pour le debug)
        info = config.get_current_model_info()
        print(f"\n[Modèle utilisé : {info['main_model']}]")

        # Réinitialise la cascade pour la prochaine question.
        # Le rate limit de 20 req/min se libère en ~1 min,
        # donc on repart du meilleur modèle à chaque nouvelle question.
        config.reset_cascade()


if __name__ == "__main__":
    main()
