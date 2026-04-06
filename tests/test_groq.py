"""
Script de diagnostic rapide — teste la connexion Groq.
Lancement : python test_groq.py
Lit automatiquement GROQ_API_KEY depuis .env
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("❌ GROQ_API_KEY non trouvée dans .env")
    exit(1)

print(f"✅ Clé trouvée : {GROQ_API_KEY[:12]}...{GROQ_API_KEY[-4:]}")
print(f"   Longueur : {len(GROQ_API_KEY)} caractères\n")

# Test 1 : modèle principal (kimi-k2-instruct)
print("── Test 1 : moonshotai/kimi-k2-instruct ──")
try:
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "moonshotai/kimi-k2-instruct",
            "messages": [{"role": "user", "content": "Dis juste 'ok'"}],
            "max_tokens": 10,
        },
        timeout=30,
    )
    print(f"   Status : {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        reply = data["choices"][0]["message"]["content"]
        print(f"   ✅ Réponse : {reply}")
    else:
        print(f"   ❌ Erreur : {r.text[:300]}")
except Exception as e:
    print(f"   ❌ Exception : {e}")

# Test 2 : modèle rapide (llama-3.1-8b-instant)
print("\n── Test 2 : llama-3.1-8b-instant ──")
try:
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": "Dis juste 'ok'"}],
            "max_tokens": 10,
        },
        timeout=30,
    )
    print(f"   Status : {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        reply = data["choices"][0]["message"]["content"]
        print(f"   ✅ Réponse : {reply}")
    else:
        print(f"   ❌ Erreur : {r.text[:300]}")
except Exception as e:
    print(f"   ❌ Exception : {e}")

# Test 3 : liste des modèles disponibles
print("\n── Test 3 : Modèles disponibles sur ton compte ──")
try:
    r = requests.get(
        "https://api.groq.com/openai/v1/models",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        timeout=15,
    )
    if r.status_code == 200:
        models = r.json().get("data", [])
        print(f"   {len(models)} modèles disponibles")
        for m in sorted(models, key=lambda x: x["id"]):
            print(f"   - {m['id']}")
    else:
        print(f"   ❌ Status {r.status_code} : {r.text[:200]}")
except Exception as e:
    print(f"   ❌ Exception : {e}")
