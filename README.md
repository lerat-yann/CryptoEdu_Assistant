# 🪙 CryptoEdu Assistant

> Assistant éducatif sur les cryptomonnaies pour débutants francophones.  
> Architecture multi-agent avec RAG, guardrails et données de marché en temps réel.

---

## 📌 Présentation

CryptoEdu Assistant est un assistant conversationnel pédagogique qui aide les débutants à comprendre l'univers des cryptomonnaies. Il répond aux questions éducatives, présente des données de marché à titre informatif, et refuse systématiquement de donner des conseils d'investissement.

**Ce que l'assistant peut faire :**
- Expliquer les concepts crypto (blockchain, wallet, DeFi, NFT, stablecoin...)
- Guider pas-à-pas pour démarrer en toute sécurité
- Afficher les prix en temps réel (Bitcoin, Ethereum, Solana...)
- Informer sur les risques et les arnaques à éviter
- Rediriger poliment les demandes de conseils vers une réponse éducative

**Ce que l'assistant ne fait jamais :**
- Donner des conseils d'investissement
- Prédire l'évolution des prix
- Répondre aux demandes d'arnaques ou de manipulation de marché

---

## 🏗️ Architecture

```
CryptoEdu_Assistant/
├── docs_crypto/               # Corpus documentaire (7 fichiers)
│   ├── wallet_coinbase.pdf
│   ├── amf_investir_crypto.pdf
│   ├── amf_precautions_pratiques.pdf
│   ├── coingecko_cex_dex_2026.pdf
│   ├── blockchain_pour_debutants.txt
│   ├── stablecoins_guide.txt
│   └── glossaire_crypto.txt
│
├── config.py                  # OpenRouter + cascade de modèles gratuits
├── rag_pipeline.py            # RAG : LangChain + ChromaDB + BM25
├── guardrails.py              # Filtrage 3 couches
├── crypto_agents.py           # 3 agents + 3 outils + 3 wrappers
├── crypto_manager.py          # Orchestrateur multi-agent
├── main.py                    # Interface CLI
│
├── .env.example               # Template des variables d'environnement
├── requirements.txt           # Dépendances Python
└── NOTES_DEVELOPPEMENT.md     # Journal de développement
```

### Agents spécialisés

| Agent | Rôle | Source de données |
|---|---|---|
| **Agent Éducation** | Répond aux questions pédagogiques | RAG (corpus AMF, Coinbase, CoinGecko) |
| **Agent Marché** | Données de prix en temps réel | CoinGecko API publique |
| **Agent Risques** | Détecte et refuse les demandes prescriptives | Analyse + règles métier |

### Outils déterministes (sans LLM)

| Outil | Description |
|---|---|
| `get_checklist_debutant()` | 7 étapes pour démarrer en crypto |
| `get_etapes_premier_achat()` | Guide pas-à-pas pour le premier achat |
| `get_bonnes_pratiques_wallet()` | Sécurité, seed phrase, erreurs courantes |

### Guardrails (filtrage 3 couches)

```
Couche 1 — Mots-clés bloquants  →  arnaques, manipulation, hors sujet flagrant
Couche 2 — Mots-clés crypto     →  passage immédiat (sans LLM)
Couche 3 — LLM classifieur      →  cas ambigus (fail-safe : passage)
```

---

## ⚙️ Stack technique

| Composant | Technologie |
|---|---|
| LLM | OpenRouter (gratuit) — cascade 4 modèles |
| Framework agents | SDK `openai-agents` |
| RAG | LangChain + ChromaDB + HuggingFace |
| Embeddings | `all-MiniLM-L6-v2` |
| Données marché | CoinGecko API publique (sans clé) |
| Interface | CLI → Streamlit (Jour 4) |

### Cascade de modèles OpenRouter

Le système bascule automatiquement sur le modèle suivant en cas d'erreur (429, 404, 400) :

```
1. meta-llama/llama-3.3-70b-instruct:free   ← prioritaire
2. deepseek/deepseek-r1:free
3. mistralai/mistral-small-3.1-24b-instruct:free
4. openrouter/free                           ← filet de sécurité
```

---

## 🚀 Installation

### Prérequis
- Python 3.10+
- Un compte gratuit sur [OpenRouter](https://openrouter.ai/) (aucune carte bancaire requise)

### 1. Cloner le dépôt

```bash
git clone <url-du-repo>
cd CryptoEdu_Assistant
```

### 2. Créer un environnement virtuel

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement

```bash
cp .env.example .env
```

Éditez `.env` et ajoutez votre clé OpenRouter :

```env
OPENROUTER_API_KEY=sk-or-...
```

### 5. Ajouter les documents dans `docs_crypto/`

Placez vos PDF et fichiers `.txt` dans le dossier `docs_crypto/`.  
Le pipeline RAG les indexera automatiquement au premier lancement.

---

## 💬 Utilisation

### Interface CLI

```bash
python main.py
```

```
╔═══════════════════════════════════════════════════════════════╗
║             CryptoEdu Assistant                               ║
║   Éducation · Marché · Risques · Débutants                   ║
╚═══════════════════════════════════════════════════════════════╝

> Par où commencer si je veux me lancer dans les cryptos ?
> C'est quoi un wallet et comment le sécuriser ?
> Quel est le prix du Bitcoin aujourd'hui ?
> Quelle différence entre un CEX et un DEX ?
```

---

## 🔒 Sécurité et éthique

- **Jamais de conseil d'investissement** : l'assistant redirige systématiquement vers une réponse éducative
- **Sources officielles** : les réponses s'appuient sur les guides AMF, Coinbase Learn et CoinGecko
- **Guardrails actifs** : les demandes d'arnaques, manipulation de marché et blanchiment sont bloquées
- **Données de marché informatives** : chaque réponse contenant des prix inclut un avertissement explicite

---

## 📄 Licence

Projet éducatif — Formation Simplon Expert IA.

---

## 🙏 Sources documentaires

- [AMF — Guides crypto-actifs](https://www.amf-france.org)
- [Coinbase Learn](https://www.coinbase.com/fr/learn)
- [CoinGecko Research](https://www.coingecko.com)
