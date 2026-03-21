"""
Configuration du CryptoEdu Assistant.
Système de cascade : 3 modèles gratuits fiables + openrouter/free en dernier recours.

Cascade mise à jour mars 2026 (llama-4-maverick retiré d'OpenRouter) :
  1. meta-llama/llama-3.3-70b-instruct:free  — fiable, multilingue, bon tool-calling
  2. deepseek/deepseek-r1:free               — excellent raisonnement
  3. mistralai/mistral-small-3.1-24b-instruct:free — bon pour les agents/RAG
  4. openrouter/free                          — dernier recours (modèle aléatoire)

Limites free tier OpenRouter : ~20 req/min, ~200 req/jour par modèle.
Avec 4 modèles en cascade, on a ~800 req/jour au total.
"""

import os
from dotenv import load_dotenv
from agents import OpenAIChatCompletionsModel, AsyncOpenAI, set_tracing_disabled

load_dotenv()

# ── Récupération de la clé ───────────────────────────────────────────────────
try:
    import streamlit as st
    def _secrets_get(key):
        try:
            return st.secrets.get(key, None)
        except Exception:
            return None
except Exception:
    _secrets_get = lambda key: None

OPENROUTER_API_KEY = (
    os.environ.get("OPENROUTER_API_KEY")
    or _secrets_get("OPENROUTER_API_KEY")
)

set_tracing_disabled(True)

if not OPENROUTER_API_KEY:
    raise ValueError(
        "Clé API manquante.\n"
        "Ajoutez dans votre .env :\n"
        "  OPENROUTER_API_KEY=sk-or-...\n\n"
        "Créez un compte gratuit sur https://openrouter.ai/"
    )

# ══════════════════════════════════════════════════════════════════════════════
# CLIENT OPENROUTER
# ══════════════════════════════════════════════════════════════════════════════

_openrouter_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "https://cryptoedu-assistant.streamlit.app",
        "X-Title": "CryptoEdu Assistant",
    },
)

# ══════════════════════════════════════════════════════════════════════════════
# CASCADE DE MODÈLES GRATUITS (du meilleur au dernier recours)
# ══════════════════════════════════════════════════════════════════════════════

MODEL_CASCADE_MAIN = [
    "meta-llama/llama-3.3-70b-instruct:free",       # Fiable, multilingue, bon tool-calling
    "deepseek/deepseek-r1:free",                     # Excellent raisonnement
    "mistralai/mistral-small-3.1-24b-instruct:free", # Bon pour agents/RAG
    "openrouter/free",                               # Dernier recours (modèle aléatoire)
]

MODEL_CASCADE_FAST = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "openrouter/free",
]

_current_main_index = 0
_current_fast_index = 0


def _make_model(model_id):
    return OpenAIChatCompletionsModel(
        model=model_id,
        openai_client=_openrouter_client,
    )


model_main = _make_model(MODEL_CASCADE_MAIN[0])
model_fast = _make_model(MODEL_CASCADE_FAST[0])

PROVIDER = "openrouter"

print(f"[Config] Provider : {PROVIDER}")
print(f"[Config] Modèle principal : {MODEL_CASCADE_MAIN[0]}")
print(f"[Config] Modèle rapide : {MODEL_CASCADE_FAST[0]}")
print(f"[Config] Cascade : {len(MODEL_CASCADE_MAIN)} modèles principaux, "
      f"{len(MODEL_CASCADE_FAST)} modèles rapides")

# ══════════════════════════════════════════════════════════════════════════════
# REGISTRE D'AGENTS
# ══════════════════════════════════════════════════════════════════════════════

_registered_agents = []


def register_agent(agent):
    _registered_agents.append(agent)
    return agent


def switch_to_next_model():
    global _current_main_index, model_main

    _current_main_index += 1
    if _current_main_index >= len(MODEL_CASCADE_MAIN):
        print("[Config] Tous les modèles de la cascade ont été épuisés")
        return False

    new_model_id = MODEL_CASCADE_MAIN[_current_main_index]
    model_main = _make_model(new_model_id)

    for agent in _registered_agents:
        agent.model = model_main

    print(f"[Config] Switch → {new_model_id} "
          f"({_current_main_index + 1}/{len(MODEL_CASCADE_MAIN)}) | "
          f"{len(_registered_agents)} agents mis à jour")
    return True


def switch_fast_to_next():
    global _current_fast_index, model_fast

    _current_fast_index += 1
    if _current_fast_index >= len(MODEL_CASCADE_FAST):
        return False

    model_fast = _make_model(MODEL_CASCADE_FAST[_current_fast_index])
    print(f"[Config] Switch fast → {MODEL_CASCADE_FAST[_current_fast_index]}")
    return True


def reset_cascade():
    global _current_main_index, _current_fast_index, model_main, model_fast

    _current_main_index = 0
    _current_fast_index = 0
    model_main = _make_model(MODEL_CASCADE_MAIN[0])
    model_fast = _make_model(MODEL_CASCADE_FAST[0])

    for agent in _registered_agents:
        agent.model = model_main

    print(f"[Config] Cascade réinitialisée → {MODEL_CASCADE_MAIN[0]}")


def get_current_model_info():
    return {
        "main_model": MODEL_CASCADE_MAIN[_current_main_index],
        "main_position": f"{_current_main_index + 1}/{len(MODEL_CASCADE_MAIN)}",
        "fast_model": MODEL_CASCADE_FAST[_current_fast_index],
        "registered_agents": len(_registered_agents),
    }
