"""
Composio REST API — Gmail + Google Docs
CryptoEdu Assistant

Appels HTTP directs à l'API REST Composio.
Plus simple et plus fiable que l'approche MCPServerStreamableHttp + Agent
(qui souffrait de conflits de boucle asyncio et d'agents qui ne démarraient jamais).

Architecture :
  _get_connected_account_id(user_email, app)
    → GET /api/v1/connectedAccounts?user_uuid={email}
    → retourne le connectedAccountId actif pour l'app demandée

  _execute_action(action_id, connected_account_id, input_data)
    → POST /api/v2/actions/{action_id}/execute

  create_google_doc_via_composio(email, title, content, tags)
    → GOOGLEDOCS_CREATE_DOCUMENT

  send_gmail_via_composio(email, messages, title)
    → GMAIL_SEND_EMAIL
"""

import os
import re
import requests

_BASE_URL = "https://backend.composio.dev/api"


def is_composio_configured() -> bool:
    """Retourne True si COMPOSIO_API_KEY est définie dans l'environnement."""
    return bool(os.environ.get("COMPOSIO_API_KEY"))


def _headers() -> dict:
    return {
        "x-api-key": os.environ.get("COMPOSIO_API_KEY", ""),
        "Content-Type": "application/json",
    }


def _get_connected_account_id(user_email: str, app: str | list[str]) -> str:
    """
    Retourne le connectedAccountId actif pour l'app et l'utilisateur donnés.

    Args:
        user_email : Email de l'utilisateur (= user_uuid dans Composio)
        app        : Nom(s) de l'app Composio — str ou liste de variantes à tester
                     (ex: ["googledocs", "google_docs", "google docs"])

    Raises:
        RuntimeError si aucun compte connecté actif n'est trouvé.
    """
    app_names = [app] if isinstance(app, str) else app
    app_names_lower = {name.lower() for name in app_names}
    # Essai v1 avec user_uuid, puis entityId si vide, puis sans filtre
    for params in [
        {"user_uuid": user_email},
        {"entityId": user_email},
        {},
    ]:
        resp = requests.get(
            f"{_BASE_URL}/v1/connectedAccounts",
            params=params,
            headers=_headers(),
            timeout=10,
        )
        print(f"[Composio] GET connectedAccounts params={params} → {resp.status_code}")
        for item in resp.json().get("items", []):
            print({
                "appName": item.get("appName"),
                "appUniqueId": item.get("appUniqueId"),
                "status": item.get("status"),
                "entityId": item.get("entityId"),
            })
        resp.raise_for_status()
        items = resp.json().get("items", [])
        if items:
            break  # on a des résultats, on s'arrête

    # Debug : affiche tous les comptes retournés
    print(f"[Composio] {len(items)} compte(s) trouvé(s) pour {user_email} :")
    for item in items:
        print(f"  appName={item.get('appName')!r}  status={item.get('status')!r}  id={item.get('id')!r}")

    for item in items:
        if item.get("appName", "").lower() in app_names_lower and item.get("status") == "ACTIVE":
            return item["id"]
    raise RuntimeError(
        f"Aucun compte {app_names} connecté et actif pour {user_email}. "
        f"Comptes disponibles : {[item.get('appName') for item in items]}"
    )


def _execute_action(action_id: str, connected_account_id: str, input_data: dict) -> dict:
    """
    Exécute une action Composio via l'API REST et retourne le JSON de réponse.
    """
    resp = requests.post(
        f"{_BASE_URL}/v2/actions/{action_id}/execute",
        headers=_headers(),
        json={"connectedAccountId": connected_account_id, "input": input_data},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def get_mcp_url(user_email: str) -> str:
    """
    Stub de compatibilité — conservé pour app.py qui l'importe et le met en cache.
    L'approche REST ne nécessite plus d'URL MCP Composio.
    """
    return "direct-rest-api"


# ── Google Docs ───────────────────────────────────────────────────────────────

def create_google_doc_via_composio(
    user_email: str,
    title: str,
    content: str,
    tags: str = "",
    mcp_url: str | None = None,  # ignoré — compatibilité app.py
) -> dict:
    """
    Crée un Google Doc dans le Drive de l'utilisateur via l'API REST Composio.

    Args:
        user_email : Email Google de l'utilisateur (= user_uuid Composio)
        title      : Titre du document
        content    : Contenu de la réponse à sauvegarder
        tags       : Tags optionnels (affichés en pied de document)
        mcp_url    : Ignoré (ancien paramètre MCP, conservé pour compatibilité)

    Returns:
        {"success": True, "doc_url": "https://...", "message": "..."}
        ou {"success": False, "error": "..."}
    """
    try:
        account_id = _get_connected_account_id(
            user_email,
            ["googledocs", "google_docs", "google docs", "googledrive", "googledoc"],
        )
        tags_line = f"\n\nTags : {tags}" if tags else ""
        result = _execute_action(
            "GOOGLEDOCS_CREATE_DOCUMENT",
            account_id,
            {"title": title, "text": f"{content}{tags_line}"},
        )

        # Extraction de l'URL dans la réponse Composio
        response_data = result.get("response", {}).get("data", {})
        doc_url = response_data.get("documentUrl") or response_data.get("webViewLink")
        if not doc_url:
            # Fallback : chercher une URL docs.google.com dans le JSON brut
            match = re.search(r"https://docs\.google\.com/document/d/[^\s)\"']+", str(result))
            doc_url = match.group(0) if match else None

        return {"success": True, "doc_url": doc_url, "message": str(result)}

    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Gmail ─────────────────────────────────────────────────────────────────────

def send_gmail_via_composio(
    user_email: str,
    conversation_messages: list,
    conversation_title: str,
    mcp_url: str | None = None,  # ignoré — compatibilité app.py
) -> dict:
    """
    Envoie un récapitulatif de la conversation par Gmail via l'API REST Composio.

    Args:
        user_email             : Email destinataire (= l'utilisateur connecté)
        conversation_messages  : Liste de dicts {"role": "user"|"assistant", "content": str}
        conversation_title     : Titre de la conversation (utilisé comme sujet)
        mcp_url                : Ignoré (ancien paramètre MCP, conservé pour compatibilité)

    Returns:
        {"success": True, "message": "Email envoyé à ..."}
        ou {"success": False, "error": "..."}
    """
    try:
        account_id = _get_connected_account_id(user_email, "gmail")

        lines = []
        for msg in conversation_messages:
            role = "Vous" if msg["role"] == "user" else "CryptoEdu Assistant"
            excerpt = msg["content"][:600]
            if len(msg["content"]) > 600:
                excerpt += "…"
            lines.append(f"{role} :\n{excerpt}")

        body = "\n\n---\n\n".join(lines)
        subject = f"CryptoEdu — {conversation_title}"

        _execute_action(
            "GMAIL_SEND_EMAIL",
            account_id,
            {
                "recipient_email": user_email,
                "subject": subject,
                "body": body,
            },
        )
        return {"success": True, "message": f"Email envoyé à {user_email}"}

    except Exception as e:
        return {"success": False, "error": str(e)}
