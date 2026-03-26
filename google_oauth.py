"""
Google OAuth2 — Module d'authentification et services Google.
CryptoEdu Assistant — Intégration Gmail + Google Docs.

Analogie : ce module est le « badge d'accès » de l'utilisateur.
Sans badge → l'assistant travaille en local (notes Markdown, tâches JSON).
Avec badge → l'assistant peut agir au nom de l'utilisateur dans Google
             (envoyer un email, créer un Google Doc dans son Drive).

Architecture :
  1. OAuth2 via streamlit-oauth (composant tiers)
     → Donne un vrai access_token (≠ st.login() natif qui ne donne que l'identité)
  2. Gmail API : envoi d'emails formatés HTML au nom de l'utilisateur
  3. Google Docs API : création de documents dans le Drive de l'utilisateur

Secrets requis (dans .env local ou Streamlit Cloud secrets) :
  GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
  GOOGLE_CLIENT_SECRET=GOCSPX-xxx
"""

import os
import json
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import streamlit as st
import requests

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION OAUTH2 GOOGLE
# ══════════════════════════════════════════════════════════════════════════════

# Endpoints Google OAuth2
GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"

# Scopes nécessaires pour Gmail + Google Docs + identité
# Analogie : ce sont les « permissions » que l'utilisateur accorde,
# comme les cases à cocher quand on installe une app sur son téléphone.
GOOGLE_SCOPES = " ".join([
    "openid",                                          # Identité de base
    "https://www.googleapis.com/auth/userinfo.email",  # Email de l'utilisateur
    "https://www.googleapis.com/auth/userinfo.profile",# Nom et photo
    "https://www.googleapis.com/auth/gmail.send",      # Envoyer des emails
    "https://www.googleapis.com/auth/documents",       # Créer/modifier des Docs
    "https://www.googleapis.com/auth/drive.file",      # Accès aux fichiers créés par l'app
])


def _get_secret(key: str) -> str | None:
    """Récupère un secret depuis l'environnement ou les secrets Streamlit."""
    val = os.environ.get(key)
    if val:
        return val
    try:
        return st.secrets.get(key, None)
    except Exception:
        return None


def get_google_client_id() -> str | None:
    return _get_secret("GOOGLE_CLIENT_ID")


def get_google_client_secret() -> str | None:
    return _get_secret("GOOGLE_CLIENT_SECRET")


def is_google_configured() -> bool:
    """Retourne True si les credentials Google OAuth sont configurés."""
    return bool(get_google_client_id() and get_google_client_secret())


def get_redirect_uri() -> str:
    """
    Détermine l'URI de redirection OAuth en fonction de l'environnement.
    - Local : http://localhost:8501
    - Streamlit Cloud : URL de l'app déployée
    """
    # Sur Streamlit Cloud, la variable STREAMLIT_SHARING_MODE est définie
    # On peut aussi utiliser l'URL dans les secrets
    cloud_url = _get_secret("GOOGLE_REDIRECT_URI")
    if cloud_url:
        return cloud_url
    # Fallback : localhost pour le dev local
    return "http://localhost:8501"


# ══════════════════════════════════════════════════════════════════════════════
# COMPOSANT OAUTH2 (streamlit-oauth)
# ══════════════════════════════════════════════════════════════════════════════

def get_oauth2_component():
    """
    Crée et retourne l'instance OAuth2Component de streamlit-oauth.
    Retourne None si les credentials ne sont pas configurés ou si la lib manque.
    """
    if not is_google_configured():
        return None

    try:
        from streamlit_oauth import OAuth2Component
    except ImportError:
        st.warning(
            "📦 La librairie `streamlit-oauth` n'est pas installée.\n"
            "Ajoutez `streamlit-oauth` à votre `requirements.txt`."
        )
        return None

    return OAuth2Component(
        client_id=get_google_client_id(),
        client_secret=get_google_client_secret(),
        authorize_endpoint=GOOGLE_AUTHORIZE_URL,
        token_endpoint=GOOGLE_TOKEN_URL,
        refresh_token_endpoint=GOOGLE_TOKEN_URL,
        revoke_token_endpoint=GOOGLE_REVOKE_URL,
    )


# ══════════════════════════════════════════════════════════════════════════════
# GESTION DU TOKEN ET DE L'UTILISATEUR
# ══════════════════════════════════════════════════════════════════════════════

def is_user_logged_in() -> bool:
    """Vérifie si l'utilisateur a un token Google valide en session."""
    return "google_token" in st.session_state and st.session_state.google_token is not None


def get_access_token() -> str | None:
    """Récupère l'access_token Google depuis la session."""
    if not is_user_logged_in():
        return None
    token_data = st.session_state.google_token
    # Le token de streamlit-oauth est un dict avec clé "token"
    # qui contient lui-même "access_token"
    if isinstance(token_data, dict):
        inner = token_data.get("token", token_data)
        return inner.get("access_token")
    return None


def get_user_info() -> dict | None:
    """
    Récupère les infos de l'utilisateur connecté (nom, email, photo).
    Utilise l'endpoint userinfo de Google avec l'access_token.
    """
    token = get_access_token()
    if not token:
        return None

    # Vérifier le cache en session pour éviter un appel API à chaque rerun
    if "google_user_info" in st.session_state and st.session_state.google_user_info:
        return st.session_state.google_user_info

    try:
        resp = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        if resp.status_code == 200:
            user_info = resp.json()
            st.session_state.google_user_info = user_info
            return user_info
    except Exception:
        pass

    return None


def logout_google():
    """Déconnecte l'utilisateur Google (supprime le token de la session)."""
    for key in ["google_token", "google_user_info"]:
        if key in st.session_state:
            del st.session_state[key]


# ══════════════════════════════════════════════════════════════════════════════
# GMAIL — Envoi d'emails
# ══════════════════════════════════════════════════════════════════════════════

def _build_email_html(conversation_messages: list, app_name: str = "CryptoEdu Assistant") -> str:
    """
    Construit le corps HTML de l'email récapitulatif.
    Style cohérent avec le dark mode de l'app (mais lisible en email).
    """
    html_parts = []

    # Header
    html_parts.append(f"""
    <div style="font-family: 'Segoe UI', Tahoma, sans-serif; max-width: 700px; margin: 0 auto;">
        <div style="background: #1a1d27; padding: 20px 25px; border-radius: 10px 10px 0 0;
                    border-bottom: 3px solid #f7931a;">
            <h1 style="color: #f7931a; margin: 0; font-size: 20px;">🪙 {app_name}</h1>
            <p style="color: #9ca3af; margin: 5px 0 0 0; font-size: 13px;">
                Récapitulatif de votre conversation
            </p>
        </div>
        <div style="background: #13161e; padding: 20px 25px; border-radius: 0 0 10px 10px;">
    """)

    # Messages
    for msg in conversation_messages:
        if msg["role"] == "user":
            html_parts.append(f"""
            <div style="background: #1a1d27; border-left: 3px solid #f7931a;
                        border-radius: 0 8px 8px 8px; padding: 12px 16px;
                        margin: 10px 30px 10px 0;">
                <div style="color: #f7931a; font-size: 11px; font-weight: bold;
                            text-transform: uppercase; margin-bottom: 6px;">Vous</div>
                <div style="color: #e8eaf0; font-size: 14px; line-height: 1.5;">
                    {_escape_html(msg["content"])}
                </div>
            </div>
            """)
        else:
            content = msg["content"]
            # Conversion markdown basique → HTML
            content = _markdown_to_simple_html(content)
            html_parts.append(f"""
            <div style="background: #0d0f14; border-left: 3px solid #00d395;
                        border-radius: 8px 8px 8px 0; padding: 12px 16px;
                        margin: 10px 0 10px 30px;">
                <div style="color: #00d395; font-size: 11px; font-weight: bold;
                            text-transform: uppercase; margin-bottom: 6px;">🪙 CryptoEdu</div>
                <div style="color: #e8eaf0; font-size: 14px; line-height: 1.6;">
                    {content}
                </div>
            </div>
            """)

    # Footer
    html_parts.append("""
            <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #2a2d3a;">
                <p style="color: #6b7280; font-size: 12px; margin: 0;">
                    ⚠️ Cet assistant est éducatif uniquement. Il ne donne aucun conseil d'investissement.<br>
                    Les cryptomonnaies sont des actifs spéculatifs à haut risque (AMF).
                </p>
            </div>
        </div>
    </div>
    """)

    return "".join(html_parts)


def _escape_html(text: str) -> str:
    """Échappe les caractères HTML dans le texte utilisateur."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def _markdown_to_simple_html(text: str) -> str:
    """
    Conversion markdown minimale → HTML pour les emails.
    Gère : **bold**, *italic*, `code`, liens, listes à puces, headers.
    """
    import re

    # Échapper le HTML d'abord
    text = _escape_html(text)

    # Headers (## → <strong>)
    text = re.sub(r'^#{1,3}\s+(.+)$', r'<strong>\1</strong>', text, flags=re.MULTILINE)

    # Bold (**text**)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)

    # Italic (*text*)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)

    # Inline code (`code`)
    text = re.sub(r'`(.+?)`',
                  r'<code style="background:#2a2d3a; padding:1px 5px; border-radius:3px; '
                  r'font-size:13px; color:#f7931a;">\1</code>', text)

    # Listes à puces (- item)
    text = re.sub(r'^[\-\*]\s+(.+)$', r'• \1', text, flags=re.MULTILINE)

    # Sauts de ligne → <br>
    text = text.replace("\n\n", "<br><br>").replace("\n", "<br>")

    return text


def send_gmail_recap(
    conversation_messages: list,
    conversation_title: str = "Conversation CryptoEdu",
) -> dict:
    """
    Envoie un email récapitulatif de la conversation à l'utilisateur connecté.

    Analogie : comme un serveur qui vous apporte l'addition récapitulative
    de tout ce que vous avez commandé pendant le repas.

    Returns:
        dict avec clés : success (bool), message (str), error (str optionnel)
    """
    token = get_access_token()
    if not token:
        return {"success": False, "error": "Non connecté à Google."}

    user_info = get_user_info()
    if not user_info or "email" not in user_info:
        return {"success": False, "error": "Impossible de récupérer votre email."}

    user_email = user_info["email"]

    # Construction de l'email
    msg = MIMEMultipart("alternative")
    msg["To"] = user_email
    msg["From"] = user_email  # Gmail envoie depuis l'adresse de l'utilisateur
    msg["Subject"] = f"🪙 {conversation_title} — CryptoEdu Assistant"

    # Corps HTML
    html_body = _build_email_html(conversation_messages)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    # Encodage du message pour l'API Gmail
    raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    # Envoi via l'API Gmail
    try:
        resp = requests.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"raw": raw_message},
            timeout=15,
        )

        if resp.status_code == 200:
            return {
                "success": True,
                "message": f"Email envoyé à {user_email} !",
            }
        else:
            error_detail = resp.json().get("error", {}).get("message", resp.text[:200])
            return {
                "success": False,
                "error": f"Erreur Gmail ({resp.status_code}) : {error_detail}",
            }
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Timeout — Gmail n'a pas répondu."}
    except Exception as e:
        return {"success": False, "error": f"Erreur inattendue : {str(e)}"}


# ══════════════════════════════════════════════════════════════════════════════
# GOOGLE DOCS — Création de documents
# ══════════════════════════════════════════════════════════════════════════════

def create_google_doc(
    title: str,
    content: str,
    tags: str = "",
) -> dict:
    """
    Crée un Google Doc dans le Drive de l'utilisateur avec le contenu fourni.

    Analogie : comme un assistant qui écrit une note dans votre carnet personnel
    (ici, votre Google Drive) au lieu de sur un post-it local.

    Args:
        title   : Titre du document
        content : Contenu en texte (sera converti en paragraphes)
        tags    : Tags optionnels (ajoutés en bas du doc)

    Returns:
        dict avec clés : success (bool), message (str), doc_url (str optionnel)
    """
    token = get_access_token()
    if not token:
        return {"success": False, "error": "Non connecté à Google."}

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # Étape 1 : Créer un document vide via Google Docs API
    try:
        create_resp = requests.post(
            "https://docs.googleapis.com/v1/documents",
            headers=headers,
            json={"title": f"🪙 {title} — CryptoEdu"},
            timeout=15,
        )

        if create_resp.status_code != 200:
            error_detail = create_resp.json().get("error", {}).get("message", create_resp.text[:200])
            return {
                "success": False,
                "error": f"Erreur création Doc ({create_resp.status_code}) : {error_detail}",
            }

        doc_data = create_resp.json()
        doc_id = doc_data["documentId"]
        doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"

    except requests.exceptions.Timeout:
        return {"success": False, "error": "Timeout — Google Docs n'a pas répondu."}
    except Exception as e:
        return {"success": False, "error": f"Erreur création : {str(e)}"}

    # Étape 2 : Insérer le contenu via batchUpdate
    # On construit le texte complet puis on l'insère d'un coup
    from datetime import datetime
    now = datetime.now()
    date_str = now.strftime("%d/%m/%Y à %H:%M")

    tags_line = ""
    if tags:
        tags_list = [t.strip() for t in tags.split(",") if t.strip()]
        tags_line = "\nTags : " + ", ".join(f"#{tag}" for tag in tags_list) + "\n"

    full_text = (
        f"{title}\n\n"
        f"📅 {date_str} | 🤖 Généré par CryptoEdu Assistant\n"
        f"{tags_line}"
        "─" * 50 + "\n\n"
        f"{content}\n\n"
        "─" * 50 + "\n"
        "Note sauvegardée depuis CryptoEdu Assistant\n"
        "⚠️ Contenu éducatif uniquement — aucun conseil d'investissement.\n"
    )

    # L'API Google Docs insère du texte à un index (1 = début du document)
    requests_body = [
        {
            "insertText": {
                "location": {"index": 1},
                "text": full_text,
            }
        }
    ]

    try:
        update_resp = requests.post(
            f"https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate",
            headers=headers,
            json={"requests": requests_body},
            timeout=15,
        )

        if update_resp.status_code == 200:
            return {
                "success": True,
                "message": f"Document créé dans votre Google Drive !",
                "doc_url": doc_url,
                "doc_id": doc_id,
            }
        else:
            # Le doc a été créé mais le contenu n'a pas pu être inséré
            return {
                "success": True,
                "message": f"Document créé (contenu partiel) dans votre Drive.",
                "doc_url": doc_url,
                "doc_id": doc_id,
                "warning": "Le contenu n'a pas pu être entièrement inséré.",
            }

    except Exception as e:
        return {
            "success": True,
            "message": "Document créé dans votre Drive (contenu vide).",
            "doc_url": doc_url,
            "doc_id": doc_id,
            "warning": f"Erreur insertion contenu : {str(e)}",
        }


# ══════════════════════════════════════════════════════════════════════════════
# WIDGET SIDEBAR — Rendu du bloc connexion Google
# ══════════════════════════════════════════════════════════════════════════════

def render_google_auth_sidebar():
    """
    Affiche le bloc de connexion/déconnexion Google dans la sidebar.
    Gère tout le flux OAuth2 : bouton → autorisation → stockage du token.

    Retourne True si l'utilisateur est connecté, False sinon.
    """
    if not is_google_configured():
        # Pas de credentials → on ne montre rien
        return False

    st.markdown("""
    <div style='font-size: 0.75rem; color: #6b7280; font-weight: 600;
                text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.5rem;'>
        Compte Google
    </div>
    """, unsafe_allow_html=True)

    if is_user_logged_in():
        # ── Utilisateur connecté : afficher son profil ──
        user_info = get_user_info()
        if user_info:
            name = user_info.get("name", "Utilisateur")
            email = user_info.get("email", "")
            picture = user_info.get("picture", "")

            if picture:
                st.markdown(f"""
                <div style='display: flex; align-items: center; gap: 10px; margin-bottom: 8px;'>
                    <img src='{picture}' style='width: 32px; height: 32px; border-radius: 50%;
                         border: 2px solid #00d395;' />
                    <div>
                        <div style='color: #e8eaf0; font-size: 0.85rem; font-weight: 500;'>
                            {name}
                        </div>
                        <div style='color: #6b7280; font-size: 0.72rem;'>{email}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(
                    f"<span style='color: #00d395; font-size: 0.85rem;'>✅ {name}</span><br>"
                    f"<span style='color: #6b7280; font-size: 0.72rem;'>{email}</span>",
                    unsafe_allow_html=True
                )

        if st.button("🚪 Déconnexion Google", key="btn_google_logout"):
            logout_google()
            st.rerun()

        return True

    else:
        # ── Utilisateur non connecté : bouton OAuth ──
        oauth2 = get_oauth2_component()
        if not oauth2:
            return False

        redirect_uri = get_redirect_uri()

        result = oauth2.authorize_button(
            name="Se connecter avec Google",
            redirect_uri=redirect_uri,
            scope=GOOGLE_SCOPES,
            key="google_oauth_button",
            use_container_width=True,
            pkce="S256",
            extras_params={"access_type": "offline", "prompt": "consent"},
        )

        if result and "token" in result:
            st.session_state.google_token = result
            st.rerun()

        st.markdown(
            "<span style='color: #6b7280; font-size: 0.72rem;'>"
            "Connectez-vous pour envoyer des emails et sauvegarder dans Google Docs."
            "</span>",
            unsafe_allow_html=True
        )

        return False
