"""
Serveur MCP — Tasks (JSON local)
Jour 5 : CryptoEdu Assistant

Permet de créer et gérer des tâches d'apprentissage à partir des conseils
reçus dans l'assistant. Les tâches sont stockées dans tasks_crypto.json.

Outils exposés :
  - add_task(title, description, priority, category) : ajoute une tâche
  - list_tasks(filter_done)                          : liste les tâches
  - complete_task(task_id)                           : marque comme fait
  - delete_task(task_id)                             : supprime une tâche

Lancement standalone : python mcp_tasks.py
Utilisé par : app.py (branché post-réponse)
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from agents import function_tool

# ── Fichier de stockage des tâches ───────────────────────────────────────────
TASKS_FILE = Path("./tasks_crypto.json")


def _load_tasks() -> list:
    """Charge les tâches depuis le fichier JSON."""
    if not TASKS_FILE.exists():
        return []
    try:
        return json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_tasks(tasks: list) -> bool:
    """Sauvegarde les tâches dans le fichier JSON."""
    try:
        TASKS_FILE.write_text(
            json.dumps(tasks, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        return True
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════════
# OUTILS MCP
# ══════════════════════════════════════════════════════════════════════════════

def _add_task(
    title: str,
    description: str = "",
    priority: str = "normale",
    category: str = "apprentissage",
) -> str:
    """Ajoute une tâche d'apprentissage crypto à la liste des tâches.

    Args:
        title       : Titre court de la tâche (ex: 'Lire le guide AMF sur les wallets')
        description : Description détaillée ou lien vers la ressource
        priority    : Priorité de la tâche — 'haute', 'normale', ou 'basse'
        category    : Catégorie — 'apprentissage', 'sécurité', 'achat', 'fiscalité', 'autre'

    Returns:
        Confirmation avec l'ID de la tâche créée.
    """
    tasks = _load_tasks()

    # Validation de la priorité
    valid_priorities = ["haute", "normale", "basse"]
    if priority not in valid_priorities:
        priority = "normale"

    # Validation de la catégorie
    valid_categories = ["apprentissage", "sécurité", "achat", "fiscalité", "autre"]
    if category not in valid_categories:
        category = "autre"

    task = {
        "id": str(uuid.uuid4())[:8],
        "title": title,
        "description": description,
        "priority": priority,
        "category": category,
        "done": False,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "completed_at": None,
    }

    tasks.append(task)

    if _save_tasks(tasks):
        return json.dumps({
            "success": True,
            "message": f"Tâche '{title}' ajoutée avec succès.",
            "task_id": task["id"],
            "task": task,
        }, ensure_ascii=False)
    else:
        return json.dumps({
            "success": False,
            "error": "Erreur lors de la sauvegarde de la tâche.",
        }, ensure_ascii=False)


def _list_tasks(filter_done: str = "toutes") -> str:
    """Liste les tâches d'apprentissage crypto.

    Args:
        filter_done : Filtre — 'toutes', 'a_faire' (non faites), 'faites'

    Returns:
        Liste des tâches avec leur statut, priorité et catégorie.
    """
    tasks = _load_tasks()

    if not tasks:
        return json.dumps({
            "tasks": [],
            "count": 0,
            "message": "Aucune tâche enregistrée pour l'instant.",
        }, ensure_ascii=False)

    # Filtrage
    if filter_done == "a_faire":
        filtered = [t for t in tasks if not t["done"]]
    elif filter_done == "faites":
        filtered = [t for t in tasks if t["done"]]
    else:
        filtered = tasks

    # Tri : priorité haute en premier, puis par date
    priority_order = {"haute": 0, "normale": 1, "basse": 2}
    filtered_sorted = sorted(
        filtered,
        key=lambda t: (t["done"], priority_order.get(t["priority"], 1), t["created_at"])
    )

    # Statistiques
    total = len(tasks)
    done = sum(1 for t in tasks if t["done"])
    a_faire = total - done

    return json.dumps({
        "tasks": filtered_sorted,
        "stats": {
            "total": total,
            "faites": done,
            "a_faire": a_faire,
            "progression": f"{round(done/total*100)}%" if total > 0 else "0%",
        },
        "filtre_applique": filter_done,
    }, ensure_ascii=False, indent=2)


def _complete_task(task_id: str) -> str:
    """Marque une tâche comme complétée.

    Args:
        task_id : ID de la tâche (8 caractères, visible dans list_tasks)

    Returns:
        Confirmation de complétion.
    """
    tasks = _load_tasks()
    task_found = None

    for task in tasks:
        if task["id"] == task_id:
            task_found = task
            if task["done"]:
                return json.dumps({
                    "success": False,
                    "message": f"La tâche '{task['title']}' est déjà marquée comme faite.",
                }, ensure_ascii=False)
            task["done"] = True
            task["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            break

    if not task_found:
        return json.dumps({
            "success": False,
            "error": f"Tâche '{task_id}' introuvable.",
            "hint": "Utilisez list_tasks() pour voir les IDs disponibles.",
        }, ensure_ascii=False)

    if _save_tasks(tasks):
        return json.dumps({
            "success": True,
            "message": f"✅ Tâche '{task_found['title']}' marquée comme complétée !",
            "task_id": task_id,
            "completed_at": task_found["completed_at"],
        }, ensure_ascii=False)
    else:
        return json.dumps({"error": "Erreur lors de la sauvegarde."}, ensure_ascii=False)


def _delete_task(task_id: str) -> str:
    """Supprime une tâche de la liste.

    Args:
        task_id : ID de la tâche à supprimer

    Returns:
        Confirmation de suppression.
    """
    tasks = _load_tasks()
    original_count = len(tasks)
    task_title = ""

    for task in tasks:
        if task["id"] == task_id:
            task_title = task["title"]
            break

    tasks_filtered = [t for t in tasks if t["id"] != task_id]

    if len(tasks_filtered) == original_count:
        return json.dumps({
            "success": False,
            "error": f"Tâche '{task_id}' introuvable.",
        }, ensure_ascii=False)

    if _save_tasks(tasks_filtered):
        return json.dumps({
            "success": True,
            "message": f"Tâche '{task_title}' supprimée.",
        }, ensure_ascii=False)
    else:
        return json.dumps({"error": "Erreur lors de la suppression."}, ensure_ascii=False)


# ── Wrapping function_tool
add_task      = function_tool(_add_task)
list_tasks    = function_tool(_list_tasks)
complete_task = function_tool(_complete_task)
delete_task   = function_tool(_delete_task)

# ── Export des outils pour import dans app.py ─────────────────────────────────
TASKS_TOOLS = [add_task, list_tasks, complete_task, delete_task]


# ── Test standalone ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Test MCP Tasks ===\n")

    print("1. Ajout de tâches...")
    r1 = json.loads(_add_task(
        title="Lire le guide AMF sur les crypto-actifs",
        description="https://www.amf-france.org — Section crypto-actifs",
        priority="haute",
        category="apprentissage",
    ))
    print(f"   → {r1.get('message', r1.get('error'))} [ID: {r1.get('task_id')}]")

    r2 = json.loads(_add_task(
        title="Activer le 2FA sur ma plateforme",
        description="Utiliser Authy ou Google Authenticator",
        priority="haute",
        category="sécurité",
    ))
    print(f"   → {r2.get('message', r2.get('error'))} [ID: {r2.get('task_id')}]")

    r3 = json.loads(_add_task(
        title="Déclarer mes comptes crypto aux impôts",
        priority="normale",
        category="fiscalité",
    ))
    print(f"   → {r3.get('message', r3.get('error'))} [ID: {r3.get('task_id')}]")

    print("\n2. Liste des tâches à faire...")
    tasks = json.loads(_list_tasks(filter_done="a_faire"))
    stats = tasks.get("stats", {})
    print(f"   → {stats.get('a_faire')} tâche(s) à faire / {stats.get('total')} total")

    if r1.get("task_id"):
        print(f"\n3. Complétion de la tâche {r1['task_id']}...")
        result = json.loads(_complete_task(task_id=r1["task_id"]))
        print(f"   → {result.get('message', result.get('error'))}")

    print("\n✅ Tests MCP Tasks terminés.")
    print(f"   Fichier : {TASKS_FILE.absolute()}")
