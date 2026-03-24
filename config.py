"""
Configuration du CryptoEdu Assistant.
Double provider : Groq (prioritaire, meilleur tool-calling) + OpenRouter (fallback).

Architecture identique au projet Cyber Career Compass :
  - Groq en principal (kimi-k2-instruct) : rapide, fiable, bon tool-calling
  - OpenRouter free en fallback : modèle aléatoire, qualité variable

Le switch Groq → OpenRouter est automatique sur RateLimitError (429).
Le switch inverse (OpenRouter → Groq) se fait via reset_cascade()
après un cooldown de 2 minutes.

Les deux clés peuvent coexister dans .env :
  GROQ_API_KEY=gsk_...
  OPENROUTER_API_KEY=sk-or-...
"""

import os
import time as _time
from dotenv import load_dotenv
from agents import OpenAIChatCompletionsModel, AsyncOpenAI, set_tracing_disabled

load_dotenv()

# ── Récupération des clés (compatible .env + Streamlit secrets) ──────────────
try:
    import streamlit as st
    def _secrets_get(key):
        try:
            return st.secrets.get(key, None)
        except Exception:
            return None
except Exception:
    _secrets_get = lambda key: None

GROQ_API_KEY = os.environ.get("GROQ_API_KEY") or _secrets_get("GROQ_API_KEY")
OPENROUTER_API_KEY = (
    os.environ.get("OPENROUTER_API_KEY")
    or _secrets_get("OPENROUTER_API_KEY")
)

# ── Désactiver le tracing ────────────────────────────────────────────────────
set_tracing_disabled(True)

# Vérifier qu'au moins un provider est disponible
if not GROQ_API_KEY and not OPENROUTER_API_KEY:
    raise ValueError(
        "Aucune clé API trouvée.\n"
        "Ajoutez dans votre .env :\n"
        "  GROQ_API_KEY=gsk_...          (prioritaire — meilleur tool-calling)\n"
        "  OPENROUTER_API_KEY=sk-or-...  (fallback — modèles gratuits)\n\n"
        "Idéalement, mettez LES DEUX pour le fallback automatique."
    )

# ══════════════════════════════════════════════════════════════════════════════
# CLIENTS — les deux sont créés au démarrage (si les clés existent)
# ══════════════════════════════════════════════════════════════════════════════

_groq_client = None
_openrouter_client = None

if GROQ_API_KEY:
    _groq_client = AsyncOpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=GROQ_API_KEY,
        max_retries=0,  # Notre cascade gère les retries
    )

if OPENROUTER_API_KEY:
    _openrouter_client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        max_retries=0,  # Notre cascade gère les retries
        default_headers={
            "HTTP-Referer": "https://cryptoedu-assistant.streamlit.app",
            "X-Title": "CryptoEdu Assistant",
        },
    )

# ══════════════════════════════════════════════════════════════════════════════
# MODÈLES — un jeu par provider
# ══════════════════════════════════════════════════════════════════════════════

_groq_model_main = None
_groq_model_fast = None
_openrouter_model_main = None
_openrouter_model_fast = None

if _groq_client:
    _groq_model_main = OpenAIChatCompletionsModel(
        model="moonshotai/kimi-k2-instruct",
        openai_client=_groq_client,
    )
    _groq_model_fast = OpenAIChatCompletionsModel(
        model="llama-3.1-8b-instant",
        openai_client=_groq_client,
    )

if _openrouter_client:
    _openrouter_model_main = OpenAIChatCompletionsModel(
        model="openrouter/free",
        openai_client=_openrouter_client,
    )
    _openrouter_model_fast = OpenAIChatCompletionsModel(
        model="openrouter/free",
        openai_client=_openrouter_client,
    )

# ══════════════════════════════════════════════════════════════════════════════
# PROVIDER ACTIF + MODÈLES EXPORTÉS
# ══════════════════════════════════════════════════════════════════════════════

# Provider initial : Groq si disponible, sinon OpenRouter
if _groq_client:
    PROVIDER = "groq"
    model_main = _groq_model_main
    model_fast = _groq_model_fast
else:
    PROVIDER = "openrouter"
    model_main = _openrouter_model_main
    model_fast = _openrouter_model_fast

HAS_FALLBACK = bool(_groq_client and _openrouter_client)

print(f"[Config] Provider : {PROVIDER} | Modèle : {model_main.model}"
      f"{' (fallback OpenRouter disponible)' if HAS_FALLBACK else ''}")

# ══════════════════════════════════════════════════════════════════════════════
# REGISTRE D'AGENTS — switch à chaud sans reload
# ══════════════════════════════════════════════════════════════════════════════

_registered_agents = []


def register_agent(agent):
    """Enregistre un agent pour que switch_to_next_model puisse
    mettre à jour son .model automatiquement.
    Retourne l'agent (permet d'écrire : agent = register_agent(Agent(...)))."""
    _registered_agents.append(agent)
    return agent


# ══════════════════════════════════════════════════════════════════════════════
# SWITCH GROQ ↔ OPENROUTER (compatible avec l'interface existante)
# ══════════════════════════════════════════════════════════════════════════════

def switch_to_next_model():
    """Bascule vers le provider suivant.
    Groq → OpenRouter → retour Groq (boucle une fois).
    Retourne True si le switch a réussi, False si plus de fallback."""
    global PROVIDER, model_main, model_fast

    if PROVIDER == "groq" and _openrouter_client:
        # Groq en erreur → bascule sur OpenRouter
        PROVIDER = "openrouter"
        model_main = _openrouter_model_main
        model_fast = _openrouter_model_fast

        for agent in _registered_agents:
            agent.model = _openrouter_model_main

        print(f"[Config] Switch → OpenRouter (fallback) | "
              f"{len(_registered_agents)} agents mis à jour")
        return True

    elif PROVIDER == "groq" and not _openrouter_client:
        # Groq en erreur, pas de fallback
        print("[Config] Groq en erreur, pas de fallback OpenRouter")
        return False

    elif PROVIDER == "openrouter" and _groq_client:
        # OpenRouter aussi en erreur → retente Groq (le rate limit a pu se libérer)
        PROVIDER = "groq"
        model_main = _groq_model_main
        model_fast = _groq_model_fast

        for agent in _registered_agents:
            agent.model = _groq_model_main

        print(f"[Config] OpenRouter épuisé → retour Groq | "
              f"{len(_registered_agents)} agents mis à jour")
        return True

    else:
        # Aucun provider disponible
        print("[Config] Tous les providers épuisés")
        return False


def switch_fast_to_next():
    """Bascule le modèle fast vers OpenRouter."""
    global model_fast

    if model_fast == _groq_model_fast and _openrouter_model_fast:
        model_fast = _openrouter_model_fast
        print("[Config] Switch fast → OpenRouter")
        return True
    return False


# ══════════════════════════════════════════════════════════════════════════════
# RESET CASCADE — intelligent avec cooldown
# ══════════════════════════════════════════════════════════════════════════════

_last_reset_time = _time.time()
_RESET_COOLDOWN = 120  # secondes — ne reset pas avant 2 minutes


def reset_cascade():
    """
    Réinitialise vers Groq si disponible.

    Reset intelligent : ne rebascule sur Groq que si au moins 2 minutes
    se sont écoulées depuis le dernier reset. Sinon, on reste sur le provider
    actuel (probablement OpenRouter qui fonctionne).
    """
    global PROVIDER, model_main, model_fast, _last_reset_time

    if not _groq_client:
        return  # Pas de Groq, rien à reset

    if PROVIDER == "groq":
        return  # Déjà sur Groq, rien à faire

    now = _time.time()
    elapsed = now - _last_reset_time

    if elapsed < _RESET_COOLDOWN:
        print(f"[Config] Reset ignoré ({int(elapsed)}s < {_RESET_COOLDOWN}s) "
              f"— reste sur OpenRouter")
        return

    # Cooldown écoulé → retour sur Groq
    PROVIDER = "groq"
    model_main = _groq_model_main
    model_fast = _groq_model_fast

    for agent in _registered_agents:
        agent.model = _groq_model_main

    _last_reset_time = now
    print(f"[Config] Cascade réinitialisée → Groq ({model_main.model})")


def force_reset_cascade():
    """Reset inconditionnel — utilisé par la sidebar (changement de conversation)."""
    global PROVIDER, model_main, model_fast, _last_reset_time

    if not _groq_client:
        return

    PROVIDER = "groq"
    model_main = _groq_model_main
    model_fast = _groq_model_fast

    for agent in _registered_agents:
        agent.model = _groq_model_main

    _last_reset_time = _time.time()
    print(f"[Config] Cascade FORCÉE → Groq ({model_main.model})")


# ══════════════════════════════════════════════════════════════════════════════
# INFO (compatible avec l'interface existante)
# ══════════════════════════════════════════════════════════════════════════════

def get_current_model_info():
    return {
        "main_model": model_main.model if model_main else "none",
        "main_position": f"{'Groq' if PROVIDER == 'groq' else 'OpenRouter (fallback)'}",
        "fast_model": model_fast.model if model_fast else "none",
        "registered_agents": len(_registered_agents),
        "provider": PROVIDER,
        "has_fallback": HAS_FALLBACK,
    }
