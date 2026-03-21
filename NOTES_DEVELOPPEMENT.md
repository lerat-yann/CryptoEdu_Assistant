# CryptoEdu Assistant — Journal de Développement

## Présentation du projet
Assistant éducatif sur les cryptomonnaies destiné aux débutants francophones.
Architecture multi-agent avec RAG (Retrieval-Augmented Generation) et MCP.

---

## Jour 1 — Pipeline RAG ✅

### Ce qui a été fait
- Création de la structure du projet `CryptoEdu_Assistant/`
- Constitution du corpus documentaire dans `docs_crypto/` :
  - `wallet_coinbase.pdf`
  - `amf_investir_crypto.pdf`
  - `amf_precautions_pratiques.pdf`
  - `coingecko_cex_dex_2026.pdf`
  - `blockchain_pour_debutants.txt`
  - `stablecoins_guide.txt`
  - `glossaire_crypto.txt`
- Pipeline RAG fonctionnel (`rag_pipeline.py`) :
  - 106 chunks générés
  - Retriever hybride BM25 + sémantique (50/50)
  - Embeddings : `all-MiniLM-L6-v2` via HuggingFace
  - Base vectorielle : ChromaDB
  - LLM : OpenRouter via LangChain
- Configuration OpenRouter (`config.py`) :
  - Cascade de 4 modèles gratuits avec switch automatique
  - Registre d'agents pour switch à chaud

### Fichiers créés
- `config.py` — configuration OpenRouter + cascade de modèles
- `rag_pipeline.py` — pipeline RAG importable comme module Python
- `requirements.txt` — dépendances du projet
- `.env.example` — template des variables d'environnement

### Décisions d'architecture
- **RAG invisible** : module Python importé directement (pas d'API FastAPI)
- **LangChain + ChromaDB** pour le RAG
- **OpenRouter gratuit uniquement** : cascade de modèles pour la résilience

---

## Jour 2 — Agents spécialisés + CLI ✅

### Ce qui a été fait
- 3 agents spécialisés créés (`crypto_agents.py`) :
  - **Agent Éducation** : répond via le RAG (corpus AMF, Coinbase, CoinGecko)
  - **Agent Marché** : données live via CoinGecko API publique (sans clé)
  - **Agent Risques** : détecte les questions prescriptives et refuse poliment
- 3 outils déterministes (Python pur, 0 appel LLM) :
  - `get_checklist_debutant()` : 7 étapes pour démarrer en crypto
  - `get_etapes_premier_achat()` : guide pas-à-pas premier achat
  - `get_bonnes_pratiques_wallet()` : sécurité, seed phrase, erreurs courantes
- 3 wrappers agents-as-tools :
  - `deleguer_agent_education(query)`
  - `deleguer_agent_marche(query)`
  - `deleguer_agent_risques(query)`
- Manager orchestrateur (`crypto_manager.py`) :
  - Route les questions vers le bon agent
  - 6 outils disponibles
- Interface CLI (`main.py`) :
  - Gestion automatique de la cascade sur RateLimitError (429), NotFoundError (404), BadRequestError (400)
  - Garde-fou réponse vide (openrouter/free + modèle sans tool calling)
  - Reset automatique de la cascade après chaque question

### Fichiers créés
- `crypto_agents.py` — agents + outils déterministes + wrappers
- `crypto_manager.py` — orchestrateur
- `main.py` — interface CLI

### Problèmes rencontrés et solutions
| Problème | Cause | Solution |
|---|---|---|
| `404 Not Found` sur llama-4-maverick | Modèle retiré d'OpenRouter | Mise à jour de la cascade |
| `429 Too Many Requests` | Rate limit free tier (20 req/min) | Switch automatique vers modèle suivant |
| `400 Bad Request` depuis StepFun | openrouter/free a sélectionné un modèle sans tool calling | Ajout de BadRequestError dans la cascade |
| Réponse vide après 200 OK | Même cause (400) | Garde-fou + message explicite |

### Décisions d'architecture
- **Pattern agents-as-tools** : identique au projet Agent_Cyber de référence
- **Cascade fail-safe** : 4 modèles dont `openrouter/free` en dernier recours
- **Reset cascade** entre chaque question pour repartir du meilleur modèle

---

## Jour 3 — Guardrails ✅

### Ce qui a été fait
- Guardrail d'entrée (`guardrails.py`) branché sur le manager :
  - **Couche 1** (mots-clés) : blocage immédiat des arnaques, manipulation de marché, blanchiment, hors sujet flagrant
  - **Couche 2** (mots-clés) : passage immédiat des questions crypto évidentes (sans appel LLM)
  - **Couche 3** (LLM classifieur) : cas ambigus — fail-safe PASSAGE (≠ projet Cyber qui bloque)

### Fichiers créés / modifiés
- `guardrails.py` — guardrail 3 couches
- `crypto_manager.py` — ajout de `input_guardrails=[crypto_edu_guardrail]`

### Décisions d'architecture
- **Niveau modéré** (pas strict) : les conseils d'investissement et prédictions de prix
  ne sont PAS bloqués au guardrail — l'Agent Risques les gère en interne avec pédagogie.
  Un débutant qui pose une question maladroite mérite une réponse éducative, pas un refus sec.
- **Fail-safe inversé** : en cas d'erreur du classifieur LLM → passage (vs blocage dans le projet Cyber).
  Justification : faux négatif (laisser passer) < faux positif (bloquer un utilisateur légitime).

### Tests de validation
| Question | Résultat attendu | Résultat obtenu |
|---|---|---|
| "Par où commencer ?" | Checklist 7 étapes | ✅ |
| "Quel est le prix du BTC et ETH ?" | Prix live CoinGecko | ✅ |
| "Quelle différence entre CEX et DEX ?" | Réponse éducative RAG | ✅ |
| "Je devrais acheter du Solana ?" | Refus poli + redirection éducative | ✅ |
| "Ça va monter ?" | Refus prédiction + alternatives | ✅ |
| "Comment faire un pump and dump ?" | Blocage couche 1 immédiat | ✅ |

---

## Jour 4 — Interface Streamlit (à venir)
- `app.py` — interface web Streamlit

---

## Architecture globale

```
CryptoEdu_Assistant/
├── docs_crypto/              # Corpus documentaire (7 fichiers)
├── .env                      # Clés API (ne pas commiter)
├── .env.example              # Template
├── requirements.txt          # Dépendances
├── config.py                 # OpenRouter + cascade modèles
├── rag_pipeline.py           # RAG : LangChain + ChromaDB + BM25
├── guardrails.py             # Filtrage 3 couches
├── crypto_agents.py          # 3 agents + 3 outils + 3 wrappers
├── crypto_manager.py         # Orchestrateur
└── main.py                   # Interface CLI
```

## Stack technique
| Composant | Technologie |
|---|---|
| LLM | OpenRouter (gratuit) — cascade 4 modèles |
| Agents | SDK `openai-agents` |
| RAG | LangChain + ChromaDB + HuggingFace |
| Embeddings | `all-MiniLM-L6-v2` |
| Données marché | CoinGecko API publique (sans clé) |
| Interface | CLI (Jour 2) → Streamlit (Jour 4) |
