# 📓 Notes de Développement — CryptoEdu Assistant

> Journal de bord du développement, jour par jour.
> Chaque section documente les choix techniques, les difficultés rencontrées et les solutions adoptées.

---

## Phase 1 — Pipeline RAG

**Objectif** : Construire le moteur de connaissances de l'assistant à partir de documents officiels.

**Fichier** : `rag_pipeline.py`

### Ce qui a été fait

Le pipeline RAG charge des documents PDF et TXT depuis `docs_crypto/`, les découpe en chunks de 800 tokens avec un chevauchement de 100, puis les indexe dans ChromaDB avec des embeddings HuggingFace (`all-MiniLM-L6-v2`).

Le retriever est hybride : il combine une recherche sémantique (embeddings cosine via ChromaDB) et une recherche lexicale (BM25) avec un poids 50/50. L'idée est qu'une recherche purement sémantique peut rater des termes techniques exacts (comme « PSAN » ou « KYC »), tandis que BM25 seul ne comprend pas les reformulations. L'ensemble couvre les deux cas.

### Choix techniques

- **Embeddings locaux** (`all-MiniLM-L6-v2`) plutôt qu'un service cloud : zéro coût, zéro dépendance externe, suffisant pour un corpus francophone de taille modeste.
- **LangChain** pour l'orchestration RAG : bien intégré avec ChromaDB, HuggingFace et le wrapper OpenAI compatible OpenRouter.
- **Prompt système strict** : l'assistant ne doit répondre qu'à partir du contexte fourni, jamais de ses connaissances générales. Si l'info n'est pas dans le corpus, il oriente vers l'AMF ou Coinbase Learn.

### Analogie

Le pipeline RAG fonctionne comme une bibliothèque spécialisée. Les documents sont les livres, les chunks sont les fiches de lecture, ChromaDB est le catalogue, et BM25 est l'index alphabétique. Quand un utilisateur pose une question, le bibliothécaire (le retriever hybride) cherche à la fois par thème (sémantique) et par mots-clés (BM25), puis présente les 4 fiches les plus pertinentes au LLM pour qu'il rédige la réponse.

### Résultat

Pipeline fonctionnel avec 7 documents, 106 chunks. Temps de réponse : ~1-3 secondes selon le modèle OpenRouter.

---

## Phase 2 — Agents spécialisés

**Objectif** : Créer les agents qui traiteront les différents types de questions.

**Fichiers** : `crypto_agents.py`, `crypto_manager.py`, `config.py`

### Architecture agents

L'orchestrateur (`crypto_manager.py`) dispose de 6 outils répartis en deux catégories :

**Outils déterministes** (Python pur, aucun appel LLM) :

- `get_checklist_debutant` — 7 étapes pour démarrer
- `get_etapes_premier_achat` — guide pas-à-pas
- `get_bonnes_pratiques_wallet` — sécurité et erreurs courantes

Ces outils sont des « fiches Bristol pré-imprimées » : le contenu est fixe, fiable, et ne dépend pas de la qualité du modèle. L'orchestrateur les utilise pour les questions dont la réponse est connue à l'avance.

**Wrappers agents-as-tools** (délèguent à un agent spécialisé) :

- `deleguer_agent_education` → Agent Éducation (interroge le RAG)
- `deleguer_agent_marche` → Agent Marché (appelle CoinGecko)
- `deleguer_agent_risques` → Agent Risques (détecte les questions prescriptives)

Le pattern est le même que sur le projet Cyber : une fonction Python `_f()` pour les tests directs, wrappée dans `function_tool(_f)` pour l'intégration SDK.

### Cascade OpenRouter

Le système utilise exclusivement des modèles gratuits via OpenRouter. Le choix des modèles a été un point délicat : tous les modèles gratuits ne supportent pas le tool-calling du SDK `openai-agents`.

La cascade teste 4 modèles triés par fiabilité. Si le modèle actif retourne une erreur 429 (rate limit), 404 (introuvable), ou 400 (format non supporté), le système bascule automatiquement vers le suivant. La cascade se réinitialise entre chaque question.

**Modèle retiré** : `openrouter/free` sélectionnait aléatoirement des modèles (Trinity, StepFun…) incompatibles avec le tool-calling. Il a été remplacé par des modèles nommés explicitement.

### Analogie

L'orchestrateur est un standard téléphonique. Quand un appel arrive (une question), il identifie le service compétent et transfère l'appel. Il ne répond jamais lui-même de mémoire — il délègue toujours à un spécialiste. Si la ligne est occupée (rate limit), il essaie automatiquement la ligne suivante.

### Résultat

6 outils fonctionnels, cascade automatique testée avec succès sur les 4 modèles.

---

## Phase 3 — Guardrails

**Objectif** : Filtrer les demandes hors périmètre sans bloquer les débutants légitimes.

**Fichier** : `guardrails.py`

### Architecture 3 couches

Le guardrail fonctionne comme un filtre progressif. Chaque couche est plus fine (et plus coûteuse) que la précédente :

**Couche 1 — Blocage immédiat** : une liste de mots-clés identifie les cas évidents (arnaques, manipulation de marché, hors-sujet flagrant comme « recette de cuisine » ou « score du match »). Zéro appel LLM, réponse instantanée.

**Couche 2 — Passage immédiat** : une liste de termes crypto éducatifs reconnus (« blockchain », « wallet », « DeFi »…) laisse passer la question sans appeler le classifieur LLM. Cela évite de consommer des tokens pour des questions évidemment dans le périmètre.

**Couche 3 — Classifieur LLM** : pour les cas ambigus (ni clairement bloqué, ni clairement crypto), un agent classifieur détermine si la question est `crypto_educatif` ou `hors_sujet`.

### Choix du fail-safe

Le fail-safe est en mode **passage** (≠ projet Cyber qui bloquait par défaut). Justification : en éducation crypto, bloquer un débutant qui pose maladroitement sa question est plus grave que laisser passer une question ambiguë. L'Agent Risques gère les cas problématiques en interne avec un refus poli et une redirection éducative.

### Niveau de filtrage modéré

Les demandes de conseil d'investissement et les prédictions de prix ne sont **pas** bloquées au niveau du guardrail. Elles sont gérées en interne par l'Agent Risques, qui peut fournir une réponse éducative utile. Bloquer ces questions au guardrail priverait l'utilisateur de toute réponse.

### Analogie

Le guardrail est un videur à l'entrée d'un lieu éducatif. La couche 1 repère les cas dangereux (mots-clés d'arnaque) et les refuse immédiatement. La couche 2 reconnaît les habitués (termes crypto) et les laisse passer sans formalités. La couche 3, pour les visiteurs inconnus, demande une vérification rapide (classifieur LLM) — et en cas de doute, laisse entrer plutôt que de refouler.

### Résultat

Guardrail fonctionnel, testé avec des questions légitimes, hors-sujet et ambiguës. Zéro faux positif constaté sur les tests.

---

## Phase 4 — Interface Streamlit

**Objectif** : Construire une interface web complète en dark mode.

**Fichier** : `app.py`

### Design

L'interface utilise un dark mode crypto inspiré des dashboards de trading, avec la palette suivante :

- Fond : `#0d0f14` (primaire), `#13161e` (secondaire), `#1a1d27` (cartes)
- Accents : `#f7931a` (orange Bitcoin pour l'utilisateur), `#00d395` (vert pour l'assistant)
- Typographie : Space Mono (monospace, titres et labels) + DM Sans (corps de texte)

Les messages utilisateur ont une bordure gauche orange, les réponses de l'assistant une bordure gauche verte. Le tout est lisible et cohérent visuellement.

### Multi-sessions

Chaque conversation est indépendante, identifiée par un UUID court (8 caractères). Le titre de la conversation est généré automatiquement par un agent LLM dédié (« Titreur ») à partir de la première question, avec un fallback sur la troncature si le LLM échoue.

### Historique contextuel

Pour permettre les questions de suivi (« et pour ça ? », « tu peux résumer ? »), l'assistant injecte les 3 derniers échanges comme contexte dans le prompt envoyé à l'orchestrateur. Cela fonctionne sans mémoire persistante côté LLM.

### Cascade intégrée

La même logique de cascade que le CLI est intégrée dans l'interface. Les erreurs 429, 404, 400 et 402 déclenchent un switch automatique. La cascade se réinitialise entre chaque question et à chaque changement de conversation.

### Sidebar

La sidebar contient : liste des conversations (avec suppression), avertissement AMF, 8 questions exemples cliquables, stack technique, liens officiels, et un toggle mode développeur.

Le mode développeur affiche un badge avec le modèle LLM utilisé sous chaque réponse, et un bouton pour injecter un faux message (utile pour tester les boutons MCP sans consommer de tokens).

### Résultat

Interface complète, responsive, avec toutes les fonctionnalités intégrées.

---

## Phase 5 — MCP local

**Objectif** : Ajouter des outils post-réponse pour enrichir l'expérience d'apprentissage.

**Fichiers** : `mcp_notes.py`, `mcp_tasks.py`, `mcp_quiz.py`

### MCP Notes (`mcp_notes.py`)

Permet de sauvegarder n'importe quelle réponse de l'assistant en fichier Markdown dans `notes_crypto/`. Chaque note inclut un titre, des tags, la date, et le contenu formaté. Les fichiers sont nommés avec la date et un slug du titre (`2025-03-23_difference-cex-et-dex.md`).

Outils exposés : `save_note`, `list_notes`, `get_note`, `delete_note`.

### MCP Tasks (`mcp_tasks.py`)

Permet de créer des tâches d'apprentissage à partir des conseils reçus. Chaque tâche a un titre, une description, une priorité (haute/normale/basse) et une catégorie (apprentissage/sécurité/achat/fiscalité/autre). Les tâches sont stockées dans `tasks_crypto.json` avec un suivi de progression.

Outils exposés : `add_task`, `list_tasks`, `complete_task`, `delete_task`.

### MCP Quiz (`mcp_quiz.py`)

13 questions réparties en 6 catégories (fondamentaux, wallets, exchanges, risques, DeFi, fiscalité) et 3 niveaux de difficulté (débutant, intermédiaire, avancé). Chaque question a 4 choix (A/B/C/D) et une explication pédagogique détaillée. Les scores sont persistés dans `quiz_scores.json` avec un historique.

Outils exposés : `get_question`, `check_answer`, `get_score`, `list_categories`.

### Intégration dans app.py

Les 3 MCP apparaissent sous forme de boutons sous le dernier message de l'assistant :

- 💾 **Sauvegarder** — Ouvre un formulaire (titre + tags) puis crée la note Markdown
- ✅ **Tâche** — Ouvre un formulaire (titre + priorité + catégorie) puis crée la tâche
- 🧠 **Quiz** — Permet de choisir catégorie et difficulté, pose une question, vérifie la réponse avec explication

Les MCP sont appelés directement en Python (pas via LLM) pour une exécution instantanée et fiable.

### Analogie

Les MCP sont comme un carnet de notes, une to-do list et un cahier d'exercices intégrés dans le même espace. L'étudiant écoute le cours (réponse de l'assistant), puis peut immédiatement prendre une note, s'ajouter un devoir, ou se tester sur ce qu'il vient d'apprendre — sans quitter la conversation.

### Résultat

3 MCP fonctionnels, intégrés dans l'interface Streamlit, testés en standalone et via les boutons UI.

---

## Décisions techniques transversales

### Pourquoi OpenRouter free tier ?

Le projet vise les débutants — il doit être accessible sans coût. OpenRouter offre un accès gratuit à des modèles performants via une API compatible OpenAI. La cascade de 4 modèles compense les limites de débit (~20 req/min par modèle) en offrant ~800 req/jour au total.

### Pourquoi le SDK `openai-agents` ?

Le SDK fournit nativement l'orchestration multi-agent, le tool-calling, les guardrails, et le pattern agents-as-tools. Il abstrait la complexité du routing entre agents et permet un code déclaratif lisible.

### Pourquoi un retriever hybride (sémantique + BM25) ?

Les termes techniques crypto (PSAN, KYC, CEX, DEX) sont souvent des acronymes courts que les embeddings seuls peuvent confondre. BM25 excelle sur ces correspondances exactes. Le mélange 50/50 donne les meilleurs résultats sur le corpus testé.

### Pourquoi des outils déterministes ?

La checklist débutant, le guide premier achat et les bonnes pratiques wallet sont des contenus stables qui ne changent pas d'une question à l'autre. Les coder en Python pur (dictionnaires JSON) garantit une réponse instantanée, fiable et identique à chaque appel — sans dépendre de la qualité ou de la disponibilité du LLM.

### Pourquoi un fail-safe en mode passage ?

Dans un contexte éducatif, un faux positif (bloquer un débutant légitime) est plus dommageable qu'un faux négatif (laisser passer une question ambiguë). L'Agent Risques constitue un second filet de sécurité interne qui gère les cas problématiques avec un refus poli et une redirection éducative.

---

## Pistes d'amélioration

- **Migration MCP externe** : Notes → GitHub Gist (API token), Tâches → Todoist (free tier), Quiz → rester local
- **Enrichissement du corpus RAG** : ajouter les rapports AMF récents, les guides Binance Academy, les whitepapers simplifiés
- **Streaming des réponses** : afficher les tokens au fil de l'eau dans Streamlit (nécessite le support streaming d'OpenRouter)
- **Internationalisation** : adapter pour l'anglais, l'espagnol (le corpus et les prompts sont actuellement 100% français)
- **Tests automatisés** : écrire des tests unitaires pour les outils déterministes et des tests d'intégration pour la cascade
- **Analytics** : tracker les questions les plus posées pour améliorer le corpus RAG
