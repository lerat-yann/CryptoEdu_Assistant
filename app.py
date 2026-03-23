"""
CryptoEdu Assistant — Interface Streamlit
Jour 4 : interface web dark mode avec historique, exemples cliquables et sidebar.

Lancement : streamlit run app.py
"""

import asyncio
import html as html_lib
import streamlit as st
from agents import Runner
from agents.exceptions import InputGuardrailTripwireTriggered
from openai import RateLimitError, NotFoundError, BadRequestError, APIStatusError
import config
from crypto_manager import manager

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

/* ── Variables ── */
:root {
    --bg-primary:    #0d0f14;
    --bg-secondary:  #13161e;
    --bg-card:       #1a1d27;
    --bg-input:      #1e2130;
    --accent-orange: #f7931a;
    --accent-yellow: #ffd700;
    --accent-green:  #00d395;
    --text-primary:  #e8eaf0;
    --text-muted:    #6b7280;
    --border:        #2a2d3a;
    --border-accent: #f7931a44;
}

/* ── Base ── */
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

/* ── Messages chat ── */
.msg-user {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent-orange);
    border-radius: 0 12px 12px 12px;
    padding: 0.4rem 1.1rem 0.1rem 1.1rem;
    margin: 0.8rem 3rem 0rem 0;
    font-size: 0.95rem;
    color: var(--text-primary);
}
.msg-assistant-header {
    margin: 0.8rem 0 0 3rem;
}
.msg-assistant-wrap {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent-green);
    border-radius: 12px 12px 12px 0;
    padding: 0.4rem 1.1rem 0.1rem 1.1rem;
    margin: 0.2rem 0 0.5rem 3rem;
    font-size: 0.95rem;
    line-height: 1.65;
    color: var(--text-primary);
}
.msg-label-user {
    font-family: 'Space Mono', monospace;
    font-size: 0.7rem;
    color: var(--accent-orange);
    font-weight: 700;
    margin-bottom: 0.1rem;
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

/* ── Badges modèle (debug) ── */
.model-badge {
    display: inline-block;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 0.15rem 0.6rem;
    font-family: 'Space Mono', monospace;
    font-size: 0.65rem;
    color: var(--text-muted);
    margin-top: 0.5rem;
}

/* ── Boutons exemples ── */
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
.stTextInput > div > div > input,
.stChatInput textarea {
    background: var(--bg-input) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
    font-family: 'DM Sans', sans-serif !important;
}
.stChatInput textarea:focus,
.stTextInput > div > div > input:focus {
    border-color: var(--accent-orange) !important;
    box-shadow: 0 0 0 2px var(--border-accent) !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: var(--bg-secondary) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] .stMarkdown {
    color: var(--text-primary) !important;
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

/* ── Divider ── */
hr {
    border-color: var(--border) !important;
    margin: 1rem 0 !important;
}

/* ── Spinner ── */
.stSpinner > div {
    border-top-color: var(--accent-orange) !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: var(--bg-primary); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent-orange); }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MESSAGES CONSTANTS
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
    "Patientez 1-2 minutes et réessayez.\n"
    "Le free tier OpenRouter est limité à ~20 req/min par modèle."
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
# INITIALISATION SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════

if "messages" not in st.session_state:
    st.session_state.messages = []

if "dev_mode" not in st.session_state:
    st.session_state.dev_mode = False

if "pending_question" not in st.session_state:
    st.session_state.pending_question = None


# ══════════════════════════════════════════════════════════════════════════════
# FONCTION CHAT ASYNCHRONE
# ══════════════════════════════════════════════════════════════════════════════

def _build_input_with_context(query: str, history: list, max_turns: int = 3) -> str:
    """
    Construit le prompt en incluant les N derniers échanges comme contexte.

    Analogie : comme donner à quelqu'un un résumé de la conversation
    avant de lui poser une nouvelle question — il peut ainsi comprendre
    les références comme "ce que tu m'as proposé" ou "et pour ça ?".

    Args:
        query     : la nouvelle question de l'utilisateur
        history   : st.session_state.messages (liste de dicts role/content)
        max_turns : nombre de paires question/réponse à inclure (défaut : 3)
    """
    # On prend les N derniers échanges (en excluant le message actuel
    # qui vient d'être ajouté à l'historique)
    recent = history[-(max_turns * 2):-1] if len(history) > 1 else []

    if not recent:
        return query  # Première question : pas de contexte

    context_lines = ["Voici les échanges précédents pour contexte :"]
    for msg in recent:
        role_label = "Utilisateur" if msg["role"] == "user" else "Assistant"
        # On tronque les longues réponses pour économiser les tokens
        content = msg["content"][:500] + "..." if len(msg["content"]) > 500 else msg["content"]
        context_lines.append(f"{role_label} : {content}")

    context_lines.append(f"\nNouvelle question : {query}")
    return "\n".join(context_lines)


async def _chat_async(query: str, history: list) -> tuple[str, str]:
    """
    Envoie la question (avec contexte) et retourne (réponse, modèle_utilisé).
    Gère automatiquement la cascade sur erreur 429/404/400/402.
    """
    # Construction du prompt enrichi avec le contexte des échanges précédents
    prompt_with_context = _build_input_with_context(query, history)

    while True:
        try:
            result = await Runner.run(manager, input=prompt_with_context, max_turns=20)
            response = result.final_output or ""
            if not response.strip():
                # Réponse vide = modèle sans tool calling → switch
                switched = config.switch_to_next_model()
                if not switched:
                    return ("⚠️ Tous les modèles sont indisponibles. Réessayez dans 1-2 minutes.", "cascade_exhausted")
                continue
            model_used = config.get_current_model_info()["main_model"]
            return response, model_used

        except InputGuardrailTripwireTriggered:
            return REFUSED_MESSAGE, "guardrail"

        except (RateLimitError, NotFoundError, BadRequestError, APIStatusError) as e:
            # 429 rate limit, 404 modèle absent, 400 format invalide, 402 spend limit
            switched = config.switch_to_next_model()
            if not switched:
                return CASCADE_EXHAUSTED_MESSAGE, "cascade_exhausted"

        except Exception as e:
            return f"Erreur inattendue : {type(e).__name__}: {e}", "error"


def chat(query: str, history: list) -> tuple[str, str]:
    """Wrapper synchrone pour Streamlit."""
    result = asyncio.run(_chat_async(query, history))
    config.reset_cascade()
    return result


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("""
    <div style='font-family: Space Mono, monospace; font-size: 1.1rem;
                color: #f7931a; font-weight: 700; margin-bottom: 0.2rem;'>
        🪙 CryptoEdu
    </div>
    <div style='color: #6b7280; font-size: 0.78rem; margin-bottom: 1rem;'>
        Assistant éducatif · Débutants
    </div>
    """, unsafe_allow_html=True)

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

    # ── Bouton reset conversation ──
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑️ Effacer la conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ZONE PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════

# ── Header ──
st.markdown("""
<div class='crypto-header'>
    <h1>🪙 CryptoEdu Assistant</h1>
    <p>Posez vos questions sur les cryptomonnaies — réponses éducatives basées sur des sources officielles</p>
</div>
""", unsafe_allow_html=True)

# ── Historique des messages ──
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f"""
        <div class='msg-user'>
            <div class='msg-label-user'>Vous</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(msg["content"])
    else:
        st.markdown(f"""
        <div class='msg-assistant-header'>
            <span class='msg-label-assistant'>🪙 CryptoEdu</span>
        </div>
        """, unsafe_allow_html=True)
        with st.container():
            st.markdown(
                f'<div class="msg-assistant-wrap">',
                unsafe_allow_html=True
            )
            st.markdown(msg["content"])
            if st.session_state.dev_mode and msg.get("model"):
                st.markdown(
                    f'<div class="model-badge">⚡ {msg["model"]}</div>',
                    unsafe_allow_html=True
                )
            st.markdown("</div>", unsafe_allow_html=True)

# ── Traitement question en attente (boutons sidebar) ──
if st.session_state.pending_question:
    query = st.session_state.pending_question
    st.session_state.pending_question = None

    st.session_state.messages.append({"role": "user", "content": query})

    st.markdown('<div class="msg-user"><div class="msg-label-user">Vous</div></div>', unsafe_allow_html=True)
    st.markdown(query)

    with st.spinner("Analyse en cours..."):
        response, model_used = chat(query, st.session_state.messages)

    st.session_state.messages.append({
        "role": "assistant",
        "content": response,
        "model": model_used,
    })
    st.rerun()

# ── Input utilisateur ──
if prompt := st.chat_input("Posez votre question sur les cryptomonnaies..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    st.markdown('<div class="msg-user"><div class="msg-label-user">Vous</div></div>', unsafe_allow_html=True)
    st.markdown(prompt)

    with st.spinner("Analyse en cours..."):
        response, model_used = chat(prompt, st.session_state.messages)

    st.session_state.messages.append({
        "role": "assistant",
        "content": response,
        "model": model_used,
    })
    st.rerun()
