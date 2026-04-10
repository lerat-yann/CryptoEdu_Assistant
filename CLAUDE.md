# CLAUDE.md — CryptoEdu Assistant

Contexte projet et décisions techniques pour les sessions Claude Code.

---

## Structure du projet

```
CryptoEdu_Assistant/
├── app.py              # Interface Streamlit (point d'entrée)
├── main.py             # Interface CLI
├── config.py           # Providers LLM (Groq + OpenRouter), registre d'agents
│
├── core/               # Logique métier (agents + orchestrateur)
│   ├── crypto_agents.py
│   ├── crypto_manager.py
│   └── guardrails.py
│
├── rag/                # Pipeline RAG (LangChain + ChromaDB + BM25)
│   └── rag_pipeline.py
│
├── quiz/               # Quiz interactif (anciennement mcp/)
│   ├── mcp_quiz.py         # function_tool openai-agents (utilisé par app.py) — NE PAS MODIFIER
│   └── mcp_quiz_server.py  # Vrai serveur MCP FastMCP (standalone)
│
├── integrations/
│   ├── google_oauth.py     # OAuth2 Google flux redirect direct — voir section dédiée
│   └── composio_google.py  # Gmail + Google Docs via Composio MCP
│
├── tests/
│   ├── test_groq.py
│   └── test_groq_tools.py
│
├── docs_crypto/        # Corpus RAG (PDF + TXT) — NE PAS TOUCHER
└── .streamlit/         # Config Streamlit — NE PAS TOUCHER
```

---

## Conflits de noms à connaître

Le projet utilise des packages Python dont les noms entrent en conflit avec des noms de dossiers évidents :

| Package SDK | Dossier qu'on NE peut PAS utiliser | Nom choisi |
|-------------|-------------------------------------|------------|
| `agents` (openai-agents SDK) | `agents/` | `core/` |
| `mcp` (SDK MCP) | `mcp/` | `quiz/` |

**Règle :** ne jamais créer de dossier nommé `agents/` ou `mcp/` à la racine — ils masquent les packages SDK installés.

---

## Variables d'environnement

| Variable | Obligatoire | Usage |
|----------|-------------|-------|
| `GROQ_API_KEY` | Oui (ou OpenRouter) | LLM principal |
| `OPENROUTER_API_KEY` | Oui (ou Groq) | LLM fallback |
| `GOOGLE_CLIENT_ID` | Non | OAuth Google (sidebar) |
| `GOOGLE_CLIENT_SECRET` | Non | OAuth Google (sidebar) |
| `GOOGLE_REDIRECT_URI` | Non | OAuth Google (défaut : localhost:8501) |
| `COMPOSIO_API_KEY` | Non | Gmail + Google Docs via Composio MCP |

---

## Architecture outils post-réponse (boutons sous les réponses)

### Sans connexion Google
- 🧠 Quiz uniquement

### Avec connexion Google
- 💾 Google Docs → `create_google_doc_via_composio()` dans `integrations/composio_google.py`
- 🧠 Quiz → `quiz/mcp_quiz.py` (function_tool local)
- 📧 Email → `send_gmail_via_composio()` dans `integrations/composio_google.py`

### Flux Composio (integrations/composio_google.py)
1. `get_mcp_url(user_email)` — **get-or-create** : cherche d'abord avec `composio.mcp.list(name=...)`, crée seulement si absent
2. URL mise en cache dans `st.session_state.composio_mcp_url` (une seule création par session)
3. `MCPServerStreamableHttp` + agent temporaire avec `model=model_main` (Groq — pas OPENAI_API_KEY)

---

## OAuth Google (integrations/google_oauth.py)

### Flux implémenté : redirect direct (pas de popup)

**Historique du problème :** Streamlit 1.55 (installé avec streamlit-oauth) a cassé le mécanisme
de popup de streamlit-oauth. La popup s'ouvrait en nouvel onglet = nouvelle session = `session_state`
vide = nouveau `code_verifier` PKCE généré = incompatible avec le `code_challenge` original = **400**.

**Solution adoptée :** abandon de `OAuth2Component.authorize_button()` au profit d'un flux
redirect direct dans le même onglet, géré entièrement côté serveur.

**Flux actuel :**
1. `st.link_button()` → construit l'URL Google avec `_build_google_auth_url()`, redirige dans le même onglet
2. `state` anti-CSRF généré avec `secrets.token_urlsafe(32)`, stocké dans `session_state["google_oauth_state"]`
3. Google redirige vers `redirect_uri?code=...&state=...` (même onglet = même session)
4. `render_google_auth_sidebar()` détecte `?code=` **en premier** (return early), vérifie le state, échange le code côté serveur avec `client_secret`
5. Token sauvegardé → `st.query_params.clear()` → `st.rerun()`

**Pourquoi pas de PKCE :** PKCE protège les apps sans secret côté client (SPA, mobile). Ici le
`client_secret` est sur le serveur Streamlit → Authorization Code Flow standard sans PKCE est approprié
et conforme aux recommandations Google pour les apps serveur.

**À ne pas faire :**
- Ne pas remettre `pkce="S256"` dans `authorize_button` — incompatible avec le nouvel onglet
- Ne pas utiliser `OAuth2Component.authorize_button()` — abandonné définitivement
- Ne pas appeler `_handle_oauth_callback_fallback()` — remplacée par la logique inline dans `render_google_auth_sidebar()`

---

## Décisions techniques

- **`model=model_main`** doit être passé explicitement à tout `Agent()` créé dans le projet —
  sans ça, le SDK cherche `OPENAI_API_KEY` qui n'existe pas.
- **mcp_quiz.py ne doit pas être modifié** — il contient le code métier du quiz utilisé
  par app.py via function_tool. `mcp_quiz_server.py` est le wrapper FastMCP par-dessus.
- **Le venv est dans `.venv/`** — utiliser `.venv/Scripts/pip.exe` pour installer des packages,
  pas le pip global.
- **Contexte conversationnel** : `_build_input_with_context()` dans app.py — fenêtre de 6 tours.
- **Débogage Composio** : `create_google_doc_via_composio()` est wrappée dans un try/except dans
  app.py qui affiche le traceback complet dans l'UI Streamlit (bloc `action == "note"`).

---

## Bugs connus / TODO

- **`_run_with_mcp()` : 403 Groq lors de Runner.run()** — La connexion Composio MCP fonctionne
  (200 OK, protocole MCP négocié confirmé dans les logs). L'erreur vient de Groq qui retourne
  un 403 lors de l'appel LLM dans `Runner.run()` (probablement le modèle kimi-k2 non supporté
  pour les appels avec outils MCP, ou quota dépassé).
  **Fix en cours :** ajouter la cascade Groq → OpenRouter dans `composio_google.py`,
  identique à celle de `config.py` / `app.py`.

---

## Commandes utiles

```bash
# Lancer l'app
streamlit run app.py

# Lancer le serveur MCP quiz en standalone
python quiz/mcp_quiz_server.py

# Installer un package dans le venv
.venv/Scripts/pip.exe install <package>

# Vérifier les imports clés
python -c "from core.crypto_manager import manager"
python -c "from quiz.mcp_quiz import _get_question"
python -c "from integrations.composio_google import is_composio_configured"
```
