"""
Serveur MCP — Notes (Markdown local)
Jour 5 : CryptoEdu Assistant

Permet de sauvegarder des réponses de l'assistant sous forme de notes Markdown.
Les notes sont stockées dans le dossier notes_crypto/ à la racine du projet.

Outils exposés :
  - save_note(title, content, tags)  : crée une note Markdown
  - list_notes()                     : liste toutes les notes existantes
  - get_note(filename)               : lit le contenu d'une note
  - delete_note(filename)            : supprime une note

Lancement standalone : python mcp_notes.py
Utilisé par : app.py (branché post-réponse)
"""

import json
import os
from datetime import datetime
from pathlib import Path
from agents import function_tool

# ── Dossier de stockage des notes ────────────────────────────────────────────
NOTES_DIR = Path("./notes_crypto")
NOTES_DIR.mkdir(exist_ok=True)


def _slug(title: str) -> str:
    """Convertit un titre en nom de fichier safe."""
    import re
    slug = title.lower().strip()
    slug = re.sub(r"[àáâãäå]", "a", slug)
    slug = re.sub(r"[èéêë]", "e", slug)
    slug = re.sub(r"[ìíîï]", "i", slug)
    slug = re.sub(r"[òóôõö]", "o", slug)
    slug = re.sub(r"[ùúûü]", "u", slug)
    slug = re.sub(r"[ç]", "c", slug)
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug)
    return slug[:50]


# ══════════════════════════════════════════════════════════════════════════════
# OUTILS MCP
# ══════════════════════════════════════════════════════════════════════════════

def _save_note(title: str, content: str, tags: str = "") -> str:
    """Sauvegarde une note en Markdown dans le dossier notes_crypto/.

    Args:
        title   : Titre de la note (ex: 'Différence CEX et DEX')
        content : Contenu de la note (peut inclure du markdown)
        tags    : Tags séparés par des virgules (ex: 'wallet, sécurité, débutant')

    Returns:
        Confirmation avec le chemin du fichier créé.
    """
    timestamp = datetime.now()
    date_str = timestamp.strftime("%Y-%m-%d")
    time_str = timestamp.strftime("%H:%M")
    filename = f"{date_str}_{_slug(title)}.md"
    filepath = NOTES_DIR / filename

    # Formatage des tags
    tags_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    tags_md = " ".join(f"#{tag}" for tag in tags_list) if tags_list else ""

    # Construction du fichier Markdown
    note_content = f"""# {title}

> 📅 {date_str} à {time_str} | {tags_md}
> 🤖 Généré par CryptoEdu Assistant

---

{content}

---
*Note sauvegardée depuis CryptoEdu Assistant*
"""

    try:
        filepath.write_text(note_content, encoding="utf-8")
        return json.dumps({
            "success": True,
            "message": f"Note '{title}' sauvegardée avec succès.",
            "filename": filename,
            "path": str(filepath),
            "tags": tags_list,
            "date": date_str,
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Erreur lors de la sauvegarde : {str(e)}",
        }, ensure_ascii=False)


def _list_notes() -> str:
    """Liste toutes les notes sauvegardées dans notes_crypto/.

    Returns:
        Liste des notes avec titre, date et taille.
    """
    try:
        notes = []
        for filepath in sorted(NOTES_DIR.glob("*.md"), reverse=True):
            content = filepath.read_text(encoding="utf-8")
            # Extraire le titre (première ligne H1)
            lines = content.split("\n")
            title = lines[0].replace("# ", "").strip() if lines else filepath.stem
            size_kb = round(filepath.stat().st_size / 1024, 1)
            notes.append({
                "filename": filepath.name,
                "title": title,
                "size_kb": size_kb,
                "modified": datetime.fromtimestamp(
                    filepath.stat().st_mtime
                ).strftime("%Y-%m-%d %H:%M"),
            })

        if not notes:
            return json.dumps({
                "notes": [],
                "count": 0,
                "message": "Aucune note sauvegardée pour l'instant.",
            }, ensure_ascii=False)

        return json.dumps({
            "notes": notes,
            "count": len(notes),
            "dossier": str(NOTES_DIR.absolute()),
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def _get_note(filename: str) -> str:
    """Lit le contenu d'une note sauvegardée.

    Args:
        filename : Nom du fichier (ex: '2025-03-23_difference-cex-et-dex.md')

    Returns:
        Contenu complet de la note en Markdown.
    """
    filepath = NOTES_DIR / filename
    if not filepath.exists():
        return json.dumps({
            "success": False,
            "error": f"Note '{filename}' introuvable.",
            "hint": "Utilisez list_notes() pour voir les notes disponibles.",
        }, ensure_ascii=False)

    try:
        content = filepath.read_text(encoding="utf-8")
        return json.dumps({
            "success": True,
            "filename": filename,
            "content": content,
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def _delete_note(filename: str) -> str:
    """Supprime une note sauvegardée.

    Args:
        filename : Nom du fichier à supprimer

    Returns:
        Confirmation de suppression.
    """
    filepath = NOTES_DIR / filename
    if not filepath.exists():
        return json.dumps({
            "success": False,
            "error": f"Note '{filename}' introuvable.",
        }, ensure_ascii=False)

    try:
        filepath.unlink()
        return json.dumps({
            "success": True,
            "message": f"Note '{filename}' supprimée.",
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# ── Wrapping function_tool
save_note   = function_tool(_save_note)
list_notes  = function_tool(_list_notes)
get_note    = function_tool(_get_note)
delete_note = function_tool(_delete_note)

# ── Export des outils pour import dans app.py ─────────────────────────────────
NOTES_TOOLS = [save_note, list_notes, get_note, delete_note]


# ── Test standalone ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Test MCP Notes ===\n")

    print("1. Sauvegarde d'une note...")
    result = json.loads(_save_note(
        title="Différence CEX et DEX",
        content="## CEX (Exchange Centralisé)\nUne plateforme gère vos fonds.\n\n## DEX (Exchange Décentralisé)\nVous gardez le contrôle de vos clés.",
        tags="exchange, débutant, wallet",
    ))
    print(f"   → {result.get('message', result.get('error'))}")
    filename = result.get("filename", "")

    print("\n2. Liste des notes...")
    notes_list = json.loads(_list_notes())
    print(f"   → {notes_list.get('count', 0)} note(s) trouvée(s)")

    if filename:
        print(f"\n3. Lecture de la note '{filename}'...")
        note = json.loads(_get_note(filename=filename))
        print(f"   → {len(note.get('content', ''))} caractères")

    print("\n✅ Tests MCP Notes terminés.")
    print(f"   Dossier : {NOTES_DIR.absolute()}")
