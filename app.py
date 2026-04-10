"""
CryptoEdu Assistant — Interface Streamlit
Jour 6 : OAuth Google (Gmail + Google Docs) + dark mode + multi-sessions.

Lancement : streamlit run app.py
"""

import asyncio
import json
import re
import traceback
import uuid
import streamlit as st
from agents import Agent, Runner
from agents.exceptions import InputGuardrailTripwireTriggered
from openai import RateLimitError, NotFoundError, BadRequestError, APIStatusError, APIConnectionError, AuthenticationError, PermissionDeniedError
import config
from core.crypto_manager import manager

from quiz.mcp_quiz  import _get_question, _check_answer, _get_score, QUESTIONS as QUIZ_QUESTIONS
from integrations.google_oauth import (
    is_google_configured, is_user_logged_in, get_user_info,
    render_google_auth_sidebar,
)
from integrations.composio_google import (
    is_composio_configured, get_mcp_url,
    create_google_doc_via_composio, send_gmail_via_composio,
)


def _get_unique_question(category: str, difficulty: str) -> dict:
    """
    Retourne une question de quiz non encore posée dans cette session.
    Si toutes les questions du filtre ont été posées, réinitialise le pool.
    """
    import random as _random

    asked = st.session_state.quiz_asked_ids

    # Filtrage identique à _get_question
    pool = QUIZ_QUESTIONS
    if category != "aléatoire":
        filtered = [q for q in pool if q["category"] == category]
        pool = filtered if filtered else pool
    if difficulty != "aléatoire":
        filtered = [q for q in pool if q["difficulty"] == difficulty]
        pool = filtered if filtered else pool

    # Exclure les questions déjà posées
    available = [q for q in pool if q["id"] not in asked]

    # Si tout le pool est épuisé, réinitialiser (et élargir si filtre trop restrictif)
    if not available:
        st.session_state.quiz_asked_ids = set()
        available = pool

    question = _random.choice(available)
    st.session_state.quiz_asked_ids.add(question["id"])

    return {
        "question_id": question["id"],
        "category": question["category"],
        "difficulty": question["difficulty"],
        "question": question["question"],
        "choices": question["choices"],
    }

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION DE LA PAGE
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="CryptoEdu Assistant",
    page_icon="🪙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# CSS — Dark mode crypto
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

:root {
    --bg-primary:    #0d0f14;
    --bg-secondary:  #13161e;
    --bg-card:       #1a1d27;
    --bg-input:      #1e2130;
    --accent-orange: #f7931a;
    --accent-green:  #00d395;
    --text-primary:  #e8eaf0;
    --text-muted:    #6b7280;
    --border:        #2a2d3a;
    --border-accent: #f7931a44;
}

.stApp {
    background-color: var(--bg-primary);
    font-family: 'DM Sans', sans-serif;
    color: var(--text-primary);
}

/* ── Header ── */
.crypto-header {
    text-align: center;
    padding: 2rem 0 1.5rem 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 1.5rem;
}
.crypto-header h1 {
    font-family: 'Space Mono', monospace;
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--accent-orange);
    letter-spacing: -0.02em;
    margin: 0;
}
.crypto-header p {
    color: var(--text-muted);
    font-size: 0.9rem;
    margin: 0.4rem 0 0 0;
    font-weight: 300;
}

/* ── Messages ── */
.msg-user {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent-orange);
    border-radius: 0 12px 12px 12px;
    padding: 0.4rem 1.1rem 0.1rem 1.1rem;
    margin: 0.8rem 3rem 0rem 0;
}
.msg-assistant-header { margin: 0.8rem 0 0 3rem; }
.msg-assistant-wrap {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent-green);
    border-radius: 12px 12px 12px 0;
    padding: 0.4rem 1.1rem 0.1rem 1.1rem;
    margin: 0.2rem 0 0.5rem 3rem;
    line-height: 1.65;
}
.msg-label-user {
    font-family: 'Space Mono', monospace;
    font-size: 0.7rem;
    color: var(--accent-orange);
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
.msg-label-assistant {
    font-family: 'Space Mono', monospace;
    font-size: 0.7rem;
    color: var(--accent-green);
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
.model-badge {
    display: inline-block;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 0.15rem 0.6rem;
    font-family: 'Space Mono', monospace;
    font-size: 0.65rem;
    color: var(--text-muted);
    margin-top: 0.4rem;
    margin-bottom: 0.4rem;
}

/* ── Conversations dans la sidebar ── */
.conv-item {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.5rem 0.8rem;
    margin-bottom: 0.3rem;
    cursor: pointer;
    font-size: 0.82rem;
    color: var(--text-primary);
    transition: all 0.15s ease;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.conv-item:hover { border-color: var(--accent-orange); }
.conv-item-active {
    border-color: var(--accent-orange) !important;
    background: var(--bg-input) !important;
    color: var(--accent-orange) !important;
}

/* ── Boutons ── */
.stButton > button {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text-primary) !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.82rem !important;
    padding: 0.45rem 0.8rem !important;
    width: 100% !important;
    text-align: left !important;
    transition: all 0.15s ease !important;
    margin-bottom: 0.3rem !important;
}
.stButton > button:hover {
    border-color: var(--accent-orange) !important;
    color: var(--accent-orange) !important;
    background: var(--bg-input) !important;
}

/* ── Input ── */
.stChatInput textarea {
    background: var(--bg-input) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
    font-family: 'DM Sans', sans-serif !important;
}
.stChatInput textarea:focus {
    border-color: var(--accent-orange) !important;
    box-shadow: 0 0 0 2px var(--border-accent) !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: var(--bg-secondary) !important;
    border-right: 1px solid var(--border) !important;
}

/* ── Avertissement ── */
.warning-box {
    background: #f7931a11;
    border: 1px solid var(--border-accent);
    border-radius: 8px;
    padding: 0.7rem 0.9rem;
    font-size: 0.8rem;
    color: #f7931acc;
    line-height: 1.5;
    margin: 0.5rem 0;
}

hr { border-color: var(--border) !important; margin: 1rem 0 !important; }

/* ── Boutons MCP post-réponse ── */
.mcp-bar {
    display: flex;
    gap: 0.5rem;
    margin: 0.3rem 0 0.8rem 3rem;
    flex-wrap: wrap;
}
.mcp-panel {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin: 0.3rem 0 0.8rem 3rem;
    font-size: 0.88rem;
}
.mcp-success {
    color: var(--accent-green);
    font-weight: 600;
    margin-bottom: 0.3rem;
}
.mcp-error { color: #f87171; }
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: var(--bg-primary); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent-orange); }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ══════════════════════════════════════════════════════════════════════════════

REFUSED_MESSAGE = (
    "Je suis le CryptoEdu Assistant — spécialisé dans l'éducation aux cryptomonnaies.\n\n"
    "Je ne peux pas répondre à cette demande.\n\n"
    "Ce que je peux faire :\n"
    "- Expliquer comment fonctionnent les cryptomonnaies\n"
    "- Vous guider pour démarrer en toute sécurité\n"
    "- Présenter les données de marché à titre informatif\n"
    "- Vous informer sur les risques et les arnaques à éviter\n\n"
    "Je ne donne jamais de conseils d'investissement."
)

CASCADE_EXHAUSTED_MESSAGE = (
    "⚠️ Tous les modèles sont temporairement indisponibles (rate limit).\n\n"
    "Patientez 1-2 minutes et réessayez."
)

EXEMPLES = [
    "🚀 Par où commencer si je veux me lancer dans les cryptos ?",
    "🔐 C'est quoi une seed phrase et comment la protéger ?",
    "📈 Quel est le prix actuel du Bitcoin et de l'Ethereum ?",
    "🔄 Quelle différence entre un CEX et un DEX ?",
    "⚠️ Quels sont les principaux risques des cryptomonnaies ?",
    "⛓️ Comment fonctionne la blockchain ?",
    "💰 C'est quoi un stablecoin ?",
    "🛒 Comment effectuer mon premier achat de crypto ?",
]


# ══════════════════════════════════════════════════════════════════════════════
# GESTION DES SESSIONS MULTIPLES
# Structure dans st.session_state :
#   conversations : dict { conv_id: { "title": str, "messages": list } }
#   active_conv   : str  (conv_id de la conversation active)
#   dev_mode      : bool
#   pending_question : str | None
# ══════════════════════════════════════════════════════════════════════════════

def _new_conv_id() -> str:
    return str(uuid.uuid4())[:8]


def _create_conversation() -> str:
    """Crée une nouvelle conversation vide et la rend active. Retourne son id."""
    conv_id = _new_conv_id()
    st.session_state.conversations[conv_id] = {
        "title": "Nouvelle conversation",
        "messages": [],
    }
    st.session_state.active_conv = conv_id
    return conv_id


def _active_messages() -> list:
    """Retourne les messages de la conversation active."""
    return st.session_state.conversations[st.session_state.active_conv]["messages"]


def _active_title() -> str:
    return st.session_state.conversations[st.session_state.active_conv]["title"]


# ── Initialisation ──
if "conversations" not in st.session_state:
    st.session_state.conversations = {}
    _create_conversation()

if "active_conv" not in st.session_state:
    # Sécurité : si active_conv a disparu, on recrée
    _create_conversation()
elif st.session_state.active_conv not in st.session_state.conversations:
    _create_conversation()

if "dev_mode" not in st.session_state:
    st.session_state.dev_mode = False

if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

if "mcp_action" not in st.session_state:
    st.session_state.mcp_action = None  # (action, msg_index)

if "quiz_state" not in st.session_state:
    st.session_state.quiz_state = None  # question en cours

if "mcp_flash" not in st.session_state:
    st.session_state.mcp_flash = None  # message de succès temporaire

if "quiz_result" not in st.session_state:
    st.session_state.quiz_result = None  # résultat du quiz en cours d'affichage

if "quiz_prefs" not in st.session_state:
    st.session_state.quiz_prefs = {"category": "aléatoire", "difficulty": "aléatoire"}

if "quiz_asked_ids" not in st.session_state:
    st.session_state.quiz_asked_ids = set()  # IDs déjà posés dans cette session

if "composio_mcp_url" not in st.session_state:
    st.session_state.composio_mcp_url = None  # URL MCP Composio (cache par session)


# ══════════════════════════════════════════════════════════════════════════════
# GÉNÉRATION DE TITRE PAR LLM
# ══════════════════════════════════════════════════════════════════════════════

async def _generate_title_async(first_question: str) -> str:
    """
    Génère un titre court (4-6 mots) pour la conversation
    à partir de la première question, via le modèle rapide.
    """
    try:
        titler = Agent(
            name="Titreur",
            instructions=(
                "Tu génères un titre ultra-court (4 à 6 mots maximum) "
                "qui résume la question posée. "
                "Pas de ponctuation finale. Pas de guillemets. "
                "Commence par une majuscule. "
                "Exemples : 'Différence CEX et DEX', "
                "'Prix Bitcoin en temps réel', "
                "'Sécuriser sa seed phrase'. "
                "Réponds UNIQUEMENT avec le titre, rien d'autre."
            ),
            model=config.model_fast,
        )
        result = await Runner.run(titler, input=first_question, max_turns=1)
        title = result.final_output.strip().strip('"').strip("'")
        # Sécurité : si le titre est trop long ou vide, on tronque la question
        if not title or len(title) > 60:
            title = first_question[:45].strip() + "…"
        return title
    except Exception:
        # En cas d'erreur, on tronque simplement la question
        return first_question[:45].strip() + "…"


def generate_title(first_question: str) -> str:
    return asyncio.run(_generate_title_async(first_question))


# ══════════════════════════════════════════════════════════════════════════════
# FONCTION CHAT
# ══════════════════════════════════════════════════════════════════════════════

def _clean_response(text: str) -> str:
    """
    Nettoie les réponses du LLM avant affichage dans Streamlit.
    - Convertit les <br> et <br/> en sauts de ligne markdown
    - Supprime les balises HTML résiduelles courantes
    """
    # <br> → saut de ligne markdown
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    # Supprimer les autres balises HTML résiduelles simples
    text = re.sub(r'<(?!strong|em|b|i|a|code|pre|/strong|/em|/b|/i|/a|/code|/pre)[^>]+>', '', text)
    return text


def _build_input_with_context(query: str, history: list, max_turns: int = 6) -> str:
    """
    Enrichit la question avec les N derniers échanges comme contexte.
    Permet les questions de suivi ("et pour ça ?", "tu peux résumer ?").
    """
    recent = history[-(max_turns * 2):-1] if len(history) > 1 else []
    if not recent:
        return query

    context_lines = ["Voici les échanges précédents pour contexte :"]
    for msg in recent:
        role_label = "Utilisateur" if msg["role"] == "user" else "Assistant"
        content = msg["content"][:500] + "..." if len(msg["content"]) > 500 else msg["content"]
        context_lines.append(f"{role_label} : {content}")
    context_lines.append(f"\nNouvelle question : {query}")
    return "\n".join(context_lines)


async def _chat_async(query: str, history: list) -> tuple[str, str]:
    prompt_with_context = _build_input_with_context(query, history)
    max_attempts = 4  # Groq → OpenRouter → Groq → stop
    attempts = 0
    while attempts < max_attempts:
        attempts += 1
        try:
            result = await Runner.run(manager, input=prompt_with_context, max_turns=20)
            response = result.final_output or ""
            if not response.strip():
                switched = config.switch_to_next_model()
                if not switched:
                    return "⚠️ Tous les modèles sont indisponibles. Réessayez dans 1-2 minutes.", "cascade_exhausted"
                continue
            return _clean_response(response), config.get_current_model_info()["main_model"]

        except InputGuardrailTripwireTriggered:
            return REFUSED_MESSAGE, "guardrail"

        except (RateLimitError, NotFoundError, BadRequestError, APIStatusError,
                APIConnectionError, AuthenticationError, PermissionDeniedError):
            switched = config.switch_to_next_model()
            if not switched:
                return CASCADE_EXHAUSTED_MESSAGE, "cascade_exhausted"

        except Exception as e:
            return f"Erreur inattendue : {type(e).__name__}: {e}", "error"

    return CASCADE_EXHAUSTED_MESSAGE, "cascade_exhausted"


def chat(query: str, history: list) -> tuple[str, str]:
    result = asyncio.run(_chat_async(query, history))
    config.reset_cascade()
    return result


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:

    # ── Logo ──
    st.markdown("""
    <div style='font-family: Space Mono, monospace; font-size: 1.1rem;
                color: #f7931a; font-weight: 700; margin-bottom: 0.2rem;'>
        🪙 CryptoEdu
    </div>
    <div style='color: #6b7280; font-size: 0.78rem; margin-bottom: 0.8rem;'>
        Assistant éducatif · Débutants
    </div>
    """, unsafe_allow_html=True)

    # ── Bouton nouvelle conversation ──
    if st.button("✏️  Nouvelle conversation", key="btn_new_conv"):
        _create_conversation()
        config.reset_cascade()
        st.rerun()

    st.markdown("---")

    # ── Liste des conversations ──
    st.markdown("""
    <div style='font-size: 0.75rem; color: #6b7280; font-weight: 600;
                text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.5rem;'>
        Conversations
    </div>
    """, unsafe_allow_html=True)

    # On affiche les conversations du plus récent au plus ancien
    conv_ids = list(reversed(list(st.session_state.conversations.keys())))
    for conv_id in conv_ids:
        conv = st.session_state.conversations[conv_id]
        is_active = (conv_id == st.session_state.active_conv)
        label = f"{'💬' if is_active else '📝'}  {conv['title']}"
        btn_style = "conv-item-active" if is_active else ""

        col1, col2 = st.columns([5, 1])
        with col1:
            if st.button(label, key=f"conv_{conv_id}"):
                st.session_state.active_conv = conv_id
                config.reset_cascade()  # Repart du meilleur modèle à chaque changement de conv
                st.rerun()
        with col2:
            # Bouton suppression (sauf si c'est la seule conversation)
            if len(st.session_state.conversations) > 1:
                if st.button("🗑", key=f"del_{conv_id}", help="Supprimer"):
                    del st.session_state.conversations[conv_id]
                    if st.session_state.active_conv == conv_id:
                        # Activer la première conversation restante
                        st.session_state.active_conv = list(
                            st.session_state.conversations.keys()
                        )[-1]
                    st.rerun()

    st.markdown("---")

    # ── Avertissement ──
    st.markdown("""
    <div class='warning-box'>
        ⚠️ <strong>Avertissement</strong><br>
        Cet assistant est <strong>éducatif uniquement</strong>.
        Il ne donne aucun conseil d'investissement.
        Les cryptomonnaies sont des actifs spéculatifs à haut risque (AMF).
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Questions exemples ──
    st.markdown("""
    <div style='font-size: 0.75rem; color: #6b7280; font-weight: 600;
                text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.5rem;'>
        Questions exemples
    </div>
    """, unsafe_allow_html=True)

    for exemple in EXEMPLES:
        if st.button(exemple, key=f"btn_{exemple[:20]}"):
            st.session_state.pending_question = exemple

    st.markdown("---")

    st.markdown("---")

    # ── Connexion Google (OAuth2) ──
    if is_google_configured():
        render_google_auth_sidebar()
        st.markdown("---")

    # ── Stack technique ──
    st.markdown("""
    <div style='font-size: 0.75rem; color: #6b7280; font-weight: 600;
                text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.5rem;'>
        Stack technique
    </div>
    <div style='font-size: 0.78rem; color: #9ca3af; line-height: 1.8;'>
        🤖 openai-agents SDK<br>
        📚 LangChain + ChromaDB<br>
        🔍 BM25 + Embeddings HuggingFace<br>
        📡 CoinGecko API (gratuit)<br>
        ☁️ OpenRouter (free tier)
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Liens officiels ──
    st.markdown("""
    <div style='font-size: 0.75rem; color: #6b7280; font-weight: 600;
                text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.5rem;'>
        Ressources officielles
    </div>
    <div style='font-size: 0.78rem; line-height: 1.9;'>
        <a href='https://www.amf-france.org' target='_blank'
           style='color: #f7931a; text-decoration: none;'>🏛️ AMF — Guides crypto</a><br>
        <a href='https://www.coinbase.com/fr/learn' target='_blank'
           style='color: #f7931a; text-decoration: none;'>📖 Coinbase Learn</a><br>
        <a href='https://www.coingecko.com' target='_blank'
           style='color: #f7931a; text-decoration: none;'>📊 CoinGecko</a>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Toggle mode développeur ──
    st.session_state.dev_mode = st.checkbox(
        "🛠️ Mode développeur",
        value=st.session_state.dev_mode,
        help="Affiche le modèle LLM utilisé pour chaque réponse",
    )
    if st.session_state.dev_mode:
        info = config.get_current_model_info()
        st.markdown(f"""
        <div style='font-size: 0.72rem; color: #6b7280; margin-top: 0.5rem;
                    font-family: Space Mono, monospace; line-height: 1.7;'>
            Modèle actif :<br>
            <span style='color: #00d395;'>{info['main_model']}</span><br>
            Position : {info['main_position']}
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("""
        <div style='font-size: 0.72rem; color: #6b7280; font-weight: 600;
                    text-transform: uppercase; letter-spacing: 0.08em;'>
            Test MCP
        </div>
        """, unsafe_allow_html=True)
        if st.button("🧪 Injecter faux message", key="btn_inject_test",
                     help="Simule une réponse pour tester les boutons MCP"):
            _active_messages().append({
                "role": "user",
                "content": "[TEST] Question simulée pour tester les boutons MCP",
            })
            _active_messages().append({
                "role": "assistant",
                "content": (
                    "Ceci est une **réponse simulée** pour tester les boutons MCP "
                    "sans appel au LLM.\n\n"
                    "Testez les boutons ci-dessous :\n"
                    "- 💾 Google Docs → sauvegarde dans votre Google Drive (connexion Google requise)\n"
                    "- 🧠 Quiz → pose une question sur les cryptos\n"
                    "- 📧 Email → envoie un récapitulatif par Gmail (connexion Google requise)"
                ),
                "model": "test_inject",
            })
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ZONE PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════

# ── Header avec titre de la conversation active ──
st.markdown(f"""
<div class='crypto-header'>
    <h1>🪙 CryptoEdu Assistant</h1>
    <p>{_active_title()}</p>
</div>
""", unsafe_allow_html=True)

def _set_mcp_action(action: str, msg_index: int, response: str):
    """Callback pour les boutons MCP — met à jour session_state avant le rerun automatique."""
    st.session_state.mcp_action = (action, msg_index, response)


def _render_mcp_bar(msg_index: int, response: str):
    """
    Affiche les boutons MCP sous une réponse de l'assistant.
    - Non connecté Google : 🧠 Quiz uniquement + message d'incitation
    - Connecté Google    : 💾 Google Docs, 🧠 Quiz, 📧 Email
    """
    if st.session_state.mcp_action or st.session_state.mcp_flash or st.session_state.quiz_result:
        return

    google_connected = is_user_logged_in()

    if google_connected:
        cols = st.columns([2, 2, 2, 3])
        with cols[0]:
            st.button(
                "💾 Google Docs", key=f"note_{msg_index}",
                help="Sauvegarder dans votre Google Drive",
                on_click=_set_mcp_action, args=("note", msg_index, response),
            )
        with cols[1]:
            st.button(
                "🧠 Quiz", key=f"quiz_{msg_index}",
                help="Tester mes connaissances",
                on_click=_set_mcp_action, args=("quiz", msg_index, response),
            )
        with cols[2]:
            st.button(
                "📧 Email", key=f"email_{msg_index}",
                help="Envoyer un récapitulatif par email",
                on_click=_set_mcp_action, args=("email", msg_index, response),
            )
    else:
        cols = st.columns([2, 5])
        with cols[0]:
            st.button(
                "🧠 Quiz", key=f"quiz_{msg_index}",
                help="Tester mes connaissances",
                on_click=_set_mcp_action, args=("quiz", msg_index, response),
            )
        with cols[1]:
            st.markdown(
                "<span style='color: #6b7280; font-size: 0.78rem;'>"
                "💡 Connectez-vous à Google pour sauvegarder en Google Docs et envoyer par email."
                "</span>",
                unsafe_allow_html=True,
            )


def _handle_mcp_action():
    """
    Traite l'action MCP en attente (note, tâche ou quiz).
    Affiché sous le dernier message assistant.

    Architecture en 3 phases :
      1. Flash message (feedback du run précédent) → toast + panneau avec bouton OK
      2. Résultat quiz (correction en cours) → affiché avec boutons suite
      3. Panneau d'action (formulaire) → affiché si mcp_action défini
    """

    # ── Phase 1 : Flash message (feedback d'une action précédente) ───────
    if st.session_state.mcp_flash:
        flash = st.session_state.mcp_flash
        # Toast natif Streamlit (disparaît tout seul après quelques secondes)
        if flash.get("type") == "success":
            st.toast(flash["message"], icon="✅")
        else:
            st.toast(flash["message"], icon="❌")
        # Panneau avec bouton OK pour libérer l'espace
        st.markdown('<div class="mcp-panel">', unsafe_allow_html=True)
        if flash.get("type") == "success":
            st.markdown(
                f'<div class="mcp-success">{flash["message"]}</div>',
                unsafe_allow_html=True
            )
            if flash.get("detail"):
                st.markdown(flash["detail"])
        else:
            st.markdown(
                f'<div class="mcp-error">{flash["message"]}</div>',
                unsafe_allow_html=True
            )
        st.button("OK", key="flash_dismiss",
                  on_click=lambda: st.session_state.update(mcp_flash=None))
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # ── Phase 2 : Résultat quiz (correction affichée, en attente de suite) ─
    if st.session_state.quiz_result:
        qr = st.session_state.quiz_result
        st.markdown('<div class="mcp-panel">', unsafe_allow_html=True)
        st.markdown("**🧠 Résultat du quiz**")

        emoji = "✅" if qr["is_correct"] else "❌"
        st.markdown(f"**{emoji} {qr['result']}**")
        st.markdown(f"*{qr['explanation']}*")

        score = qr["score_global"]
        st.markdown(
            f'<div class="mcp-success">Score : {score["correct"]}/{score["total"]} ({score["pourcentage"]})</div>',
            unsafe_allow_html=True
        )

        col1, col2 = st.columns([2, 2])
        with col1:
            if st.button("🎲 Question suivante", key="quiz_next_after_result"):
                # Charger directement une nouvelle question avec les mêmes prefs
                prefs = st.session_state.quiz_prefs
                q = _get_unique_question(
                    category=prefs.get("category", "aléatoire"),
                    difficulty=prefs.get("difficulty", "aléatoire"),
                )
                st.session_state.quiz_result = None
                st.session_state.quiz_state = q
                st.session_state.mcp_action = ("quiz", 0, "")
                st.rerun()
        with col2:
            if st.button("🏁 Terminer le quiz", key="quiz_finish"):
                st.session_state.quiz_result = None
                st.session_state.quiz_state = None
                st.session_state.mcp_action = None
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
        return

    # ── Phase 3 : Panneau d'action MCP (formulaire) ─────────────────────
    if not st.session_state.mcp_action:
        return

    action, msg_index, response = st.session_state.mcp_action

    st.markdown('<div class="mcp-panel">', unsafe_allow_html=True)

    if action == "note":
        # ── Sauvegarde dans Google Docs (via Composio MCP) ──
        st.markdown("**💾 Sauvegarder dans Google Docs**")

        title = st.text_input(
            "Titre de la note",
            value="Note CryptoEdu",
            key="note_title_input"
        )
        tags = st.text_input(
            "Tags (séparés par des virgules)",
            placeholder="ex: wallet, sécurité, débutant",
            key="note_tags_input"
        )
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("💾 Google Docs", key="note_confirm"):
                user_info = get_user_info()
                user_email = user_info.get("email") if user_info else None
                if not user_email:
                    st.session_state.mcp_flash = {
                        "type": "error",
                        "message": "❌ Impossible de récupérer l'email Google.",
                    }
                else:
                    # Récupérer ou mettre en cache l'URL MCP
                    if not st.session_state.composio_mcp_url:
                        st.session_state.composio_mcp_url = get_mcp_url(user_email)
                    try:
                        result = create_google_doc_via_composio(
                            user_email=user_email,
                            title=title,
                            content=response,
                            tags=tags,
                            mcp_url=st.session_state.composio_mcp_url,
                        )
                        if result.get("success"):
                            doc_url = result.get("doc_url", "")
                            flash_msg = f'✅ Document "{title}" créé dans votre Google Drive !'
                            flash_detail = f'[Ouvrir le document]({doc_url})' if doc_url else None
                            st.session_state.mcp_flash = {
                                "type": "success",
                                "message": flash_msg,
                                "detail": flash_detail,
                            }
                        else:
                            st.session_state.mcp_flash = {
                                "type": "error",
                                "message": f'❌ {result.get("error")}',
                            }
                    except Exception as _e:
                        st.error(f"Erreur détaillée : {_e}")
                        st.code(traceback.format_exc())
                st.session_state.mcp_action = None
                st.rerun()
        with col2:
            st.button("Annuler", key="note_cancel",
                      on_click=lambda: st.session_state.update(mcp_action=None))

    elif action == "email":
        # ── Envoi du récapitulatif par Gmail (via Composio MCP) ──
        st.markdown("**📧 Envoyer un récapitulatif par email**")

        user_info = get_user_info()
        user_email = user_info.get("email", "?") if user_info else "?"

        st.markdown(
            f"<span style='color: #6b7280; font-size: 0.82rem;'>"
            f"L'email sera envoyé à <strong style='color: #00d395;'>{user_email}</strong> "
            f"et contiendra toute la conversation en cours.</span>",
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("📧 Envoyer", key="email_confirm"):
                if user_email == "?":
                    st.session_state.mcp_flash = {
                        "type": "error",
                        "message": "❌ Impossible de récupérer l'email Google.",
                    }
                else:
                    # Récupérer ou mettre en cache l'URL MCP
                    if not st.session_state.composio_mcp_url:
                        st.session_state.composio_mcp_url = get_mcp_url(user_email)
                    messages = _active_messages()
                    conv_title = _active_title()
                    result = send_gmail_via_composio(
                        user_email=user_email,
                        conversation_messages=messages,
                        conversation_title=conv_title,
                        mcp_url=st.session_state.composio_mcp_url,
                    )
                    if result.get("success"):
                        st.session_state.mcp_flash = {
                            "type": "success",
                            "message": f'📧 {result["message"]}',
                        }
                    else:
                        st.session_state.mcp_flash = {
                            "type": "error",
                            "message": f'❌ {result.get("error")}',
                        }
                st.session_state.mcp_action = None
                st.rerun()
        with col2:
            st.button("Annuler", key="email_cancel",
                      on_click=lambda: st.session_state.update(mcp_action=None))

    elif action == "quiz":
        # ── Quiz interactif ──
        st.markdown("**🧠 Tester mes connaissances**")

        if not st.session_state.quiz_state:
            # Choix de catégorie et difficulté
            col_cat, col_diff = st.columns(2)
            with col_cat:
                cat = st.selectbox(
                    "Catégorie",
                    ["aléatoire", "fondamentaux", "wallets", "exchanges",
                     "risques", "defi", "fiscalite"],
                    key="quiz_cat"
                )
            with col_diff:
                diff = st.selectbox(
                    "Difficulté",
                    ["aléatoire", "débutant", "intermédiaire", "avancé"],
                    key="quiz_diff"
                )
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("🎲 Question !", key="quiz_start"):
                    # Reset automatique du score à chaque nouvelle partie
                    from quiz.mcp_quiz import SCORES_FILE
                    SCORES_FILE.write_text(
                        json.dumps({"total": 0, "correct": 0, "history": []},
                                   ensure_ascii=False, indent=2),
                        encoding="utf-8"
                    )
                    st.session_state.quiz_asked_ids = set()
                    q = _get_unique_question(category=cat, difficulty=diff)
                    st.session_state.quiz_state = q
                    st.session_state.quiz_prefs = {"category": cat, "difficulty": diff}
                    st.rerun()
            with col2:
                st.button("Annuler", key="quiz_cancel_init",
                          on_click=lambda: st.session_state.update(mcp_action=None, quiz_state=None))
        else:
            # Question en cours — affichage et réponse
            q = st.session_state.quiz_state
            st.markdown(f"**{q['question']}**")
            for choice in q["choices"]:
                st.markdown(f"- {choice}")

            answer = st.radio(
                "Votre réponse :",
                ["A", "B", "C", "D"],
                horizontal=True,
                key="quiz_answer"
            )
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("✔️ Valider", key="quiz_validate"):
                    result = json.loads(_check_answer(
                        question_id=q["question_id"],
                        answer=answer,
                    ))
                    # Stocker le résultat pour affichage persistant
                    st.session_state.quiz_result = result
                    st.session_state.quiz_state = None
                    st.session_state.mcp_action = None
                    st.rerun()
            with col2:
                if st.button("⏭️ Autre question", key="quiz_next"):
                    # Charger directement une nouvelle question
                    prefs = st.session_state.quiz_prefs
                    q_new = _get_unique_question(
                        category=prefs.get("category", "aléatoire"),
                        difficulty=prefs.get("difficulty", "aléatoire"),
                    )
                    st.session_state.quiz_state = q_new
                    st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def _handle_query(query: str):
    """Traite une question : l'ajoute à l'historique, appelle le chat, met à jour le titre."""
    messages = _active_messages()
    is_first_message = len(messages) == 0

    # Ajout du message utilisateur
    messages.append({"role": "user", "content": query})

    # Affichage immédiat de la question
    st.markdown(
        '<div class="msg-user"><div class="msg-label-user">Vous</div></div>',
        unsafe_allow_html=True
    )
    st.markdown(query)

    # Génération du titre après le premier message (en parallèle de l'affichage)
    if is_first_message:
        title = generate_title(query)
        st.session_state.conversations[st.session_state.active_conv]["title"] = title

    # Appel au chat
    with st.spinner("Analyse en cours..."):
        response, model_used = chat(query, messages)

    # Ajout de la réponse à l'historique
    messages.append({"role": "assistant", "content": response, "model": model_used})

    # Affichage de la réponse
    st.markdown(
        '<div class="msg-assistant-header"><span class="msg-label-assistant">🪙 CryptoEdu</span></div>',
        unsafe_allow_html=True
    )
    st.markdown('<div class="msg-assistant-wrap">', unsafe_allow_html=True)
    st.markdown(response)
    if st.session_state.dev_mode:
        st.markdown(
            f'<div class="model-badge">⚡ {model_used}</div>',
            unsafe_allow_html=True
        )
    st.markdown("</div>", unsafe_allow_html=True)

    st.rerun()


# ── Affichage de l'historique de la conversation active ──
messages_list = _active_messages()
last_assistant_index = max(
    (i for i, m in enumerate(messages_list) if m["role"] == "assistant"),
    default=None
)

for i, msg in enumerate(messages_list):
    if msg["role"] == "user":
        st.markdown(
            '<div class="msg-user"><div class="msg-label-user">Vous</div></div>',
            unsafe_allow_html=True
        )
        st.markdown(msg["content"])
    else:
        st.markdown(
            '<div class="msg-assistant-header"><span class="msg-label-assistant">🪙 CryptoEdu</span></div>',
            unsafe_allow_html=True
        )
        st.markdown('<div class="msg-assistant-wrap">', unsafe_allow_html=True)
        st.markdown(msg["content"])
        if st.session_state.dev_mode and msg.get("model"):
            st.markdown(
                f'<div class="model-badge">⚡ {msg["model"]}</div>',
                unsafe_allow_html=True
            )
        st.markdown("</div>", unsafe_allow_html=True)

        # Boutons MCP uniquement sous le dernier message assistant
        if i == last_assistant_index:
            _render_mcp_bar(i, msg["content"])
            _handle_mcp_action()


# ── Traitement question en attente (boutons exemples sidebar) ──
if st.session_state.pending_question:
    query = st.session_state.pending_question
    st.session_state.pending_question = None
    _handle_query(query)

# ── Input utilisateur ──
if prompt := st.chat_input("Posez votre question sur les cryptomonnaies..."):
    _handle_query(prompt)
