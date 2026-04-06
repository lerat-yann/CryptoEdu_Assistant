# 🪙 CryptoEdu Assistant

**Les débutants francophones perdent des heures à chercher des informations fiables sur les cryptomonnaies, noyés entre les arnaques, le jargon technique et les "conseils" douteux sur les réseaux sociaux.**

CryptoEdu Assistant résout ce problème : un chatbot multi-agent qui éduque sans jamais prescrire, alimenté par des sources officielles (AMF, Coinbase Learn), avec des données de marché en temps réel et un système de guardrails qui refuse tout conseil d'investissement.

> ⚠️ **Avertissement** — Cet assistant est **éducatif uniquement**. Il ne donne aucun conseil d'investissement. Les crypto-actifs sont des investissements spéculatifs à haut risque ([AMF](https://www.amf-france.org)).

---

### 🔗 [Tester la démo live sur Streamlit Cloud](https://cryptoeduassistant-pmwwyo8ny659behdtaou8g.streamlit.app)

<!-- Remplacez par vos propres captures d'écran dans le dossier assets/ -->
<!-- ![Screenshot de l'interface](assets/screenshot_main.png) -->

---

## Le problème

Un débutant francophone qui veut comprendre les cryptomonnaies fait face à trois obstacles : des sources en anglais ou non vérifiées, des influenceurs qui poussent à l'achat, et un jargon technique (seed phrase, DeFi, gas fees, CEX vs DEX…) qui décourage. Les guides officiels de l'AMF existent, mais ils sont longs et dispersés.

## La solution

CryptoEdu Assistant concentre les meilleures sources éducatives dans un chatbot accessible, qui :

- **Répond en français** avec un ton pédagogique adapté aux débutants
- **Cite ses sources** (AMF, Coinbase Learn, CoinGecko) grâce à un pipeline RAG
- **Refuse les conseils d'investissement** automatiquement, via un système de guardrails à 3 couches
- **Donne les prix en temps réel** (CoinGecko API) à titre informatif uniquement
- **Propose un quiz interactif** pour tester ses connaissances (40 questions, 6 catégories)
- **S'intègre à Google** (OAuth) : sauvegarde en Google Docs et envoi de récapitulatifs par Gmail

---

## Fonctionnalités

### 🤖 3 agents spécialisés

| Agent | Rôle | Source |
|-------|------|--------|
| **Éducation** | Questions conceptuelles (blockchain, wallets, DeFi, NFT, stablecoins, réglementation…) | Corpus RAG (7 docs, 106 chunks) |
| **Marché** | Prix, variations, capitalisation, volumes en temps réel | API CoinGecko |
| **Risques** | Détection des demandes de conseil → refus poli + redirection éducative | Guardrails internes |

### 🔧 3 outils déterministes (zéro appel LLM)

- **Checklist débutant** — Les 7 étapes pour démarrer en crypto
- **Guide premier achat** — Pas-à-pas du dépôt à la vérification
- **Bonnes pratiques wallet** — Seed phrase, hot/cold wallet, erreurs courantes

### 🎯 Outils post-réponse

Sous chaque réponse de l'assistant, des boutons permettent d'agir :

- **🧠 Quiz** — 40 questions, 6 catégories, 3 niveaux de difficulté (toujours disponible)
- **💾 Google Docs** — Sauvegarde de la réponse dans le Google Drive de l'utilisateur (connexion Google requise)
- **📧 Email** — Récapitulatif de la conversation envoyé par Gmail (connexion Google requise)

### 🛡️ Guardrails à 3 couches

1. **Mots-clés bloquants** — Arnaques, manipulation, hors-sujet flagrant → blocage immédiat
2. **Mots-clés crypto** — Termes éducatifs évidents → passage sans appel LLM
3. **Classifieur LLM** — Cas ambigus, fail-safe en mode passage (un faux négatif est moins grave qu'un débutant légitime bloqué)

### 🔐 Intégration Google OAuth

- Connexion via Google (OAuth2 avec `streamlit-oauth`)
- **📧 Gmail** : envoi du récapitulatif de conversation formaté HTML
- **📄 Google Docs** : sauvegarde des notes dans le Drive de l'utilisateur
- Fallback gracieux : sans connexion Google, seul le quiz reste disponible

### 🎨 Interface Streamlit

- Dark mode (Space Mono + DM Sans, palette orange/vert crypto)
- Multi-sessions avec titres générés par LLM
- Historique contextuel (6 derniers échanges pour les questions de suivi)
- Mode développeur : badge modèle, injection de test
- Sidebar complète : conversations, profil Google, liens officiels

---

## Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│                        app.py (Streamlit)                         │
│     Dark mode · Multi-sessions · Quiz · OAuth Google              │
└────────────┬──────────────────────┬──────────────┬────────────────┘
             │                      │              │
             ▼                      ▼              ▼
┌─────────────────────────┐  ┌────────────┐  ┌──────────────────┐
│  core/                  │  │ mcp/       │  │ integrations/    │
│  crypto_manager.py      │  │ mcp_quiz   │  │ google_oauth.py  │
│  crypto_agents.py       │  │ (40 Q/6cat)│  │ OAuth2 + Gmail   │
│  guardrails.py          │  └────────────┘  │ + Google Docs    │
└────┬──────┬──────┬──────┘                  └──────────────────┘
     │      │      │
     ▼      ▼      ▼
┌────────┐ ┌────────┐ ┌────────┐
│Éducation│ │ Marché │ │Risques │
│  (RAG) │ │(Gecko) │ │(Guard) │
└───┬────┘ └───┬────┘ └────────┘
    │          │
    ▼          ▼
┌────────┐ ┌─────────┐
│rag/    │ │CoinGecko│
│ChromaDB│ │  API    │
│+ BM25  │ └─────────┘
└────────┘
```

### Cascade de modèles (double provider)

L'assistant utilise **Groq** en priorité (rapide, bon tool-calling) avec **OpenRouter** en fallback automatique :

| Provider | Modèle | Rôle |
|----------|--------|------|
| **Groq** (principal) | `kimi-k2-instruct` | Main — rapide, tool-calling fiable |
| **Groq** (rapide) | `llama-3.1-8b-instant` | Classifieur guardrails, génération de titres |
| **OpenRouter** (fallback) | `openrouter/free` | Secours si Groq rate-limité (429/403/400) |

Le switch est automatique sur erreur, avec un cooldown de 2 minutes avant de retenter Groq.

---

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| Agents | SDK `openai-agents` (orchestration, tool-calling, guardrails) |
| LLM principal | **Groq** (kimi-k2-instruct + llama-3.1-8b-instant) |
| LLM fallback | **OpenRouter** free tier |
| RAG | LangChain + ChromaDB + BM25 (retriever hybride 50/50) |
| Embeddings | HuggingFace `all-MiniLM-L6-v2` |
| Données marché | CoinGecko API publique (sans clé) |
| Interface | Streamlit (dark mode custom) |
| OAuth | `streamlit-oauth` (Google OAuth2 → Gmail + Docs) |
| Quiz | `function_tool` local (40 questions, scoring par session) |

---

## Installation rapide

### Prérequis

- Python 3.10+
- Au moins une clé API : **Groq** (recommandé) et/ou **OpenRouter** (gratuit)

### 3 commandes pour lancer

```bash
git clone https://github.com/lerat-yann/CryptoEdu_Assistant.git
cd CryptoEdu_Assistant
pip install -r requirements.txt
```

Puis configurer les clés :

```bash
cp .env.example .env
# Éditer .env :
#   GROQ_API_KEY=gsk_...          (prioritaire)
#   OPENROUTER_API_KEY=sk-or-...  (fallback)
```

Lancer :

```bash
streamlit run app.py          # Interface web
# ou
python main.py                # Mode CLI
```

### OAuth Google (optionnel)

Pour activer Gmail + Google Docs, ajouter dans `.env` :

```bash
GOOGLE_CLIENT_ID=xxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxx
GOOGLE_REDIRECT_URI=http://localhost:8501
```

Sans ces clés, l'app fonctionne normalement — seul le quiz est disponible sous les réponses.

---

## Structure du projet

```
CryptoEdu_Assistant/
├── app.py                          # Interface Streamlit (point d'entrée web)
├── main.py                         # Interface CLI (point d'entrée terminal)
├── config.py                       # Double provider Groq/OpenRouter, registre d'agents
│
├── core/                           # Logique métier (agents + orchestrateur)
│   ├── crypto_agents.py            #   3 agents + 3 outils déterministes + wrappers
│   ├── crypto_manager.py           #   Orchestrateur — 6 outils, guardrails
│   └── guardrails.py               #   Filtrage 3 couches (mots-clés + LLM classifieur)
│
├── rag/                            # Pipeline RAG
│   └── rag_pipeline.py             #   LangChain + ChromaDB + BM25 hybride
│
├── mcp/                            # Quiz interactif
│   └── mcp_quiz.py                 #   40 questions, 6 catégories, 3 niveaux
│
├── integrations/                   # Services externes (Google OAuth2)
│   └── google_oauth.py             #   Gmail API + Google Docs API
│
├── tests/                          # Tests
│   ├── test_groq.py                #   Test connexion Groq
│   └── test_groq_tools.py          #   Test tool-calling Groq
│
├── docs/                           # Documentation projet
│   ├── GUIDE_OAUTH_GOOGLE.md       #   Guide intégration OAuth
│   └── NOTES_DEVELOPPEMENT.md      #   Journal de développement
│
├── docs_crypto/                    # Corpus RAG (7 documents PDF + TXT)
├── .streamlit/                     # Config Streamlit
├── .env.example                    # Template des clés API
├── requirements.txt                # Dépendances Python
├── LICENSE                         # MIT
└── README.md                       # Ce fichier
```

---

## Utilisation

### Questions exemples

| Type | Exemple |
|------|---------|
| 🚀 Débutant | *Par où commencer si je veux me lancer dans les cryptos ?* |
| 🔐 Sécurité | *C'est quoi une seed phrase et comment la protéger ?* |
| 📈 Marché | *Quel est le prix actuel du Bitcoin et de l'Ethereum ?* |
| 🔄 Conceptuel | *Quelle différence entre un CEX et un DEX ?* |
| ⚠️ Risques | *Quels sont les principaux risques des cryptomonnaies ?* |
| ⛓️ Technique | *Comment fonctionne la blockchain ?* |

### Comportement face aux demandes de conseil

L'assistant détecte automatiquement les demandes prescriptives et redirige :

- ❌ *« Quel crypto devrais-je acheter ? »* → Refus poli + explication des critères d'évaluation
- ❌ *« Est-ce le bon moment pour investir ? »* → Refus poli + présentation des risques
- ✅ *« Quels critères pour évaluer un projet crypto ? »* → Réponse éducative complète

---

## Gestion des erreurs

L'application est conçue pour ne **jamais crasher** face à l'utilisateur :

- **Clé API manquante** → Message clair indiquant quelles clés configurer
- **Rate limit LLM (429)** → Switch automatique vers le provider suivant
- **Modèle introuvable (404)** → Cascade vers le modèle disponible
- **CoinGecko timeout** → Message d'erreur propre, pas de stacktrace Python
- **OAuth non configuré** → Seul le quiz reste disponible, pas de crash
- **Corpus RAG vide** → Message indiquant d'ajouter des documents dans `docs_crypto/`

---

## Limites connues

- **Free tier Groq/OpenRouter** : limité en requêtes par minute. La cascade double-provider atténue le problème.
- **Contexte conversationnel limité** : pour rester dans les quotas gratuits, l'assistant envoie un résumé tronqué des échanges précédents au LLM. Sur les conversations longues, il peut ne pas se souvenir du contenu exact d'une réponse antérieure — dans ce cas, il le signale honnêtement plutôt que d'inventer (comportement anti-hallucination volontaire).
- **Qualité variable** : les modèles gratuits peuvent parfois produire des réponses incomplètes.
- **RAG dépendant du corpus** : la qualité des réponses éducatives dépend des documents dans `docs_crypto/`.
- **OAuth Google en mode Test** : les utilisateurs doivent être ajoutés manuellement comme testeurs dans Google Cloud Console.
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
