# 🪙 CryptoEdu Assistant

**Assistant éducatif sur les cryptomonnaies pour débutants francophones.**

> ⚠️ Cet assistant est **éducatif uniquement**. Il ne donne aucun conseil d'investissement.
> Les crypto-actifs sont des investissements spéculatifs à haut risque ([AMF](https://www.amf-france.org)).

---

## Présentation

CryptoEdu Assistant est un chatbot multi-agent qui aide les débutants francophones à comprendre les cryptomonnaies en toute sécurité. Il combine un pipeline RAG alimenté par des sources officielles (AMF, Coinbase Learn, CoinGecko), des données de marché en temps réel, et un système de guardrails qui refuse systématiquement tout conseil d'investissement.

**Philosophie** : éduquer sans jamais prescrire. Chaque question reçoit une réponse pédagogique sourcée ; chaque demande de conseil est poliment redirigée vers une explication des critères d'évaluation.

---

## Fonctionnalités

### Agents spécialisés
- **Agent Éducation** — Répond aux questions conceptuelles via le corpus RAG (blockchain, wallets, DeFi, NFT, stablecoins, réglementation…)
- **Agent Marché** — Données en temps réel via l'API CoinGecko : prix, variations, capitalisation, volumes
- **Agent Risques** — Détecte les demandes de conseil, refuse poliment, redirige vers du contenu éducatif

### Outils déterministes (sans appel LLM)
- **Checklist débutant** — Les 7 étapes pour démarrer en crypto
- **Guide premier achat** — Pas-à-pas du dépôt à la vérification
- **Bonnes pratiques wallet** — Seed phrase, hot/cold wallet, erreurs courantes

### MCP local (outils post-réponse)
- **Notes** — Sauvegarde des réponses en fichiers Markdown (`notes_crypto/`)
- **Tâches** — Liste d'apprentissage avec priorités et catégories (`tasks_crypto.json`)
- **Quiz** — 13 questions, 6 catégories, 3 niveaux de difficulté (`quiz_crypto.json`)

### Guardrails à 3 couches
1. **Mots-clés bloquants** — Arnaques, manipulation, hors-sujet flagrant → blocage immédiat
2. **Mots-clés crypto** — Termes éducatifs évidents → passage sans appel LLM
3. **Classifieur LLM** — Cas ambigus, avec fail-safe en mode passage (un faux négatif est moins grave qu'un débutant légitime bloqué)

### Interface Streamlit
- Dark mode (Space Mono + DM Sans, palette orange/vert)
- Multi-sessions avec titres générés par LLM
- Historique contextuel (3 derniers échanges pour les questions de suivi)
- Sidebar : conversations, avertissement AMF, exemples cliquables, stack technique, liens officiels
- Mode développeur : badge modèle, bouton d'injection de test MCP
- Boutons MCP sous chaque réponse : 💾 Sauvegarder · ✅ Tâche · 🧠 Quiz

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     app.py (Streamlit)                       │
│          Dark mode · Multi-sessions · Boutons MCP            │
└──────────────┬───────────────────────────┬───────────────────┘
               │                           │
               ▼                           ▼
┌──────────────────────────┐   ┌──────────────────────────────┐
│   crypto_manager.py      │   │   MCP local                  │
│   Orchestrateur (6 outils)│   │   mcp_notes.py (Markdown)   │
│   + guardrails.py        │   │   mcp_tasks.py (JSON)        │
└──────┬───────┬───────┬───┘   │   mcp_quiz.py  (JSON)        │
       │       │       │       └──────────────────────────────┘
       ▼       ▼       ▼
┌────────┐ ┌────────┐ ┌────────┐
│Éducation│ │ Marché │ │Risques │
│  (RAG) │ │(Gecko) │ │(Guard) │
└────┬───┘ └────┬───┘ └────────┘
     │          │
     ▼          ▼
┌────────┐ ┌────────┐
│ChromaDB│ │CoinGecko│
│+ BM25  │ │  API   │
└────────┘ └────────┘
```

### Cascade de modèles

L'assistant utilise exclusivement des modèles gratuits via OpenRouter, organisés en cascade automatique. Si un modèle atteint sa limite de requêtes (429), est introuvable (404), ou ne supporte pas le format (400), le système bascule automatiquement vers le suivant :

| Position | Modèle | Rôle |
|----------|--------|------|
| 1 | `meta-llama/llama-3.3-70b-instruct:free` | Principal — multilingue, tool-calling fiable |
| 2 | `mistralai/mistral-small-3.1-24b-instruct:free` | Backup — bon pour agents/RAG |
| 3 | `google/gemini-flash-1.5:free` | Backup — contexte long |
| 4 | `qwen/qwen3-14b:free` | Dernier recours — raisonnement |

La cascade se réinitialise automatiquement entre chaque question pour repartir du meilleur modèle.

---

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| Agents | SDK `openai-agents` (orchestration, tool-calling, guardrails) |
| LLM | OpenRouter free tier (4 modèles en cascade) |
| RAG | LangChain + ChromaDB + BM25 (retriever hybride 50/50) |
| Embeddings | HuggingFace `all-MiniLM-L6-v2` |
| Données marché | CoinGecko API publique (sans clé) |
| Interface | Streamlit (dark mode custom) |
| MCP | `function_tool` local (notes Markdown, tâches JSON, quiz JSON) |

---

## Installation

### Prérequis
- Python 3.10+
- Compte OpenRouter gratuit → [openrouter.ai](https://openrouter.ai/)

### Étapes

```bash
# 1. Cloner le projet
git clone https://github.com/<votre-repo>/cryptoedu-assistant.git
cd cryptoedu-assistant

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Configurer la clé API
cp .env.example .env
# Éditer .env et ajouter : OPENROUTER_API_KEY=sk-or-...

# 4. Ajouter des documents au corpus RAG (optionnel)
# Placer des PDF ou fichiers .txt dans le dossier docs_crypto/

# 5. Lancer l'interface
streamlit run app.py

# Ou en mode CLI :
python main.py
```

### Dépendances principales

```
openai-agents
langchain langchain-community langchain-openai langchain-huggingface langchain-chroma langchain-classic
chromadb
sentence-transformers
streamlit
python-dotenv
requests
rank-bm25
```

---

## Structure du projet

```
cryptoedu-assistant/
├── app.py                  # Interface Streamlit (dark mode, multi-sessions, MCP)
├── main.py                 # Interface CLI avec cascade automatique
├── config.py               # Cascade OpenRouter, client, registre d'agents
├── crypto_manager.py       # Orchestrateur — 6 outils, guardrails
├── crypto_agents.py        # 3 agents + 3 outils déterministes + wrappers
├── guardrails.py           # Filtrage 3 couches (mots-clés + LLM classifieur)
├── rag_pipeline.py         # Pipeline RAG (LangChain + ChromaDB + BM25)
├── mcp_notes.py            # MCP Notes — sauvegarde Markdown
├── mcp_tasks.py            # MCP Tâches — apprentissage JSON
├── mcp_quiz.py             # MCP Quiz — 13 questions, 6 catégories
├── docs_crypto/            # Corpus RAG (PDF + TXT)
├── notes_crypto/           # Notes sauvegardées (générées)
├── tasks_crypto.json       # Tâches d'apprentissage (généré)
├── quiz_crypto.json        # Questions du quiz (généré au 1er lancement)
├── quiz_scores.json        # Scores du quiz (généré)
├── .env                    # Clé API OpenRouter
├── requirements.txt        # Dépendances Python
└── README.md               # Ce fichier
```

---

## Utilisation

### Questions exemples

| Type | Exemple |
|------|---------|
| Débutant | *Par où commencer si je veux me lancer dans les cryptos ?* |
| Éducatif | *C'est quoi une seed phrase et comment la protéger ?* |
| Marché | *Quel est le prix actuel du Bitcoin et de l'Ethereum ?* |
| Conceptuel | *Quelle différence entre un CEX et un DEX ?* |
| Risques | *Quels sont les principaux risques des cryptomonnaies ?* |
| Technique | *Comment fonctionne la blockchain ?* |

### Comportement face aux demandes de conseil

L'assistant détecte automatiquement les demandes prescriptives et redirige :

- ❌ *« Quel crypto devrais-je acheter ? »* → Refus poli + explication des critères d'évaluation
- ❌ *« Est-ce le bon moment pour investir ? »* → Refus poli + présentation des risques
- ✅ *« Quels critères pour évaluer un projet crypto ? »* → Réponse éducative complète

---

## Limites connues

- **Free tier OpenRouter** : ~20 req/min par modèle, ~200 req/jour. La cascade (4 modèles) offre ~800 req/jour au total.
- **Qualité variable** : les modèles gratuits peuvent parfois produire des réponses incomplètes ou mal formatées.
- **RAG dépendant du corpus** : la qualité des réponses éducatives dépend des documents placés dans `docs_crypto/`.
- **MCP local uniquement** : les notes, tâches et quiz sont stockés localement (pas de synchronisation cloud).
- **CoinGecko API publique** : limitée en nombre de requêtes et sans données historiques avancées.

---

## Licence

Ce projet est distribué sous licence MIT. Voir le fichier [`LICENSE`](LICENSE) pour les détails.

---

## Ressources officielles

- [AMF — Guides crypto-actifs](https://www.amf-france.org)
- [Coinbase Learn (FR)](https://www.coinbase.com/fr/learn)
- [CoinGecko](https://www.coingecko.com)
- [ACPR — Crypto et risques](https://acpr.banque-france.fr)
