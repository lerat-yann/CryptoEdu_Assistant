"""
Diagnostic du 400 Bad Request sur Groq.
Teste l'orchestrateur étape par étape pour identifier le problème.

Lancement : python test_groq_tools.py
"""

import asyncio
import json
from dotenv import load_dotenv
load_dotenv()

from agents import Agent, Runner, function_tool
from config import model_main, model_fast, PROVIDER, get_current_model_info

info = get_current_model_info()
print(f"Provider : {info['provider']} | Modèle : {info['main_model']}\n")

# ── Test 1 : Agent simple sans tools ──
print("═" * 60)
print("TEST 1 — Agent simple (sans tools)")
print("═" * 60)

async def test1():
    agent = Agent(
        name="Test Simple",
        instructions="Réponds en une phrase en français.",
        model=model_main,
    )
    try:
        result = await Runner.run(agent, input="Bonjour, ça va ?", max_turns=1)
        print(f"✅ Réponse : {result.final_output[:200]}")
    except Exception as e:
        print(f"❌ Erreur : {type(e).__name__}: {e}")

asyncio.run(test1())

# ── Test 2 : Agent avec 1 tool simple ──
print(f"\n{'═' * 60}")
print("TEST 2 — Agent avec 1 function_tool simple")
print("═" * 60)

@function_tool
def dire_bonjour() -> str:
    """Retourne un message de bienvenue."""
    return json.dumps({"message": "Bienvenue dans le monde crypto !"})

async def test2():
    agent = Agent(
        name="Test Tool Simple",
        instructions="Utilise l'outil dire_bonjour pour répondre.",
        tools=[dire_bonjour],
        model=model_main,
    )
    try:
        result = await Runner.run(agent, input="Salut !", max_turns=3)
        print(f"✅ Réponse : {result.final_output[:200]}")
    except Exception as e:
        print(f"❌ Erreur : {type(e).__name__}: {e}")

asyncio.run(test2())

# ── Test 3 : Agent avec tool qui retourne un gros JSON ──
print(f"\n{'═' * 60}")
print("TEST 3 — Agent avec tool retournant un gros JSON (~2000 chars)")
print("═" * 60)

@function_tool
def get_checklist_test() -> str:
    """Retourne une checklist pour débutant crypto."""
    data = {
        "titre": "Checklist Débutant",
        "etapes": [
            {"numero": i, "etape": f"Étape {i} — Description détaillée de l'étape numéro {i} pour tester le format."}
            for i in range(1, 8)
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)

async def test3():
    agent = Agent(
        name="Test Gros JSON",
        instructions="Utilise l'outil get_checklist_test et présente le résultat.",
        tools=[get_checklist_test],
        model=model_main,
    )
    try:
        result = await Runner.run(agent, input="Donne-moi la checklist.", max_turns=3)
        print(f"✅ Réponse : {result.final_output[:300]}")
    except Exception as e:
        print(f"❌ Erreur : {type(e).__name__}: {e}")

asyncio.run(test3())

# ── Test 4 : Agent-as-tool (wrapper async) ──
print(f"\n{'═' * 60}")
print("TEST 4 — Agent-as-tool (pattern deleguer_agent)")
print("═" * 60)

sub_agent = Agent(
    name="Sous-Agent Test",
    instructions="Tu es un expert. Réponds en 2 phrases en français.",
    model=model_main,
)

@function_tool
async def deleguer_sous_agent(query: str) -> str:
    """Délègue à un sous-agent pour répondre à la question."""
    result = await Runner.run(sub_agent, input=query, max_turns=3)
    return result.final_output

async def test4():
    orchestrateur = Agent(
        name="Orchestrateur Test",
        instructions="Tu délègues toujours à deleguer_sous_agent.",
        tools=[deleguer_sous_agent],
        model=model_main,
    )
    try:
        result = await Runner.run(orchestrateur, input="C'est quoi un wallet ?", max_turns=5)
        print(f"✅ Réponse : {result.final_output[:300]}")
    except Exception as e:
        print(f"❌ Erreur : {type(e).__name__}: {e}")

asyncio.run(test4())

# ── Test 5 : Guardrail classifieur (model_fast) ──
print(f"\n{'═' * 60}")
print("TEST 5 — Classifieur avec model_fast ({})".format(
    info['fast_model']))
print("═" * 60)

async def test5():
    classifieur = Agent(
        name="Classifieur Test",
        instructions="Réponds uniquement 'crypto_educatif' ou 'hors_sujet'.",
        model=model_fast,
    )
    try:
        result = await Runner.run(classifieur, input="C'est quoi le Bitcoin ?", max_turns=1)
        print(f"✅ Réponse : {result.final_output[:100]}")
    except Exception as e:
        print(f"❌ Erreur : {type(e).__name__}: {e}")

asyncio.run(test5())

print(f"\n{'═' * 60}")
print("DIAGNOSTIC TERMINÉ")
print("═" * 60)
