"""
Serveur MCP — Quiz crypto (FastMCP)

Vrai serveur MCP exposant les outils quiz via le protocole MCP standard.
Compatible avec tout client MCP (Claude Desktop, openai-agents MCPServerStdio, etc.)

Outils exposés :
  - get_question(category, difficulty)  → question aléatoire
  - check_answer(question_id, answer)   → correction + explication
  - get_score()                         → score global et historique
  - list_categories()                   → catégories disponibles

Lancement standalone :
  python quiz/mcp_quiz_server.py

Connexion depuis openai-agents :
  MCPServerStdio(params={"command": "python", "args": ["quiz/mcp_quiz_server.py"]})
"""

from fastmcp import FastMCP

# Import du code métier depuis mcp_quiz.py (inchangé)
try:
    from quiz.mcp_quiz import _get_question, _check_answer, _get_score, _list_categories
except ImportError:
    from mcp_quiz import _get_question, _check_answer, _get_score, _list_categories

# ── Serveur MCP ───────────────────────────────────────────────────────────────

mcp = FastMCP(
    name="quiz-crypto",
    instructions=(
        "Serveur de quiz éducatif sur les cryptomonnaies. "
        "Propose 40 questions réparties en 6 catégories et 3 niveaux de difficulté. "
        "Utilise get_question() pour démarrer, check_answer() pour valider, "
        "get_score() pour le bilan."
    ),
)


@mcp.tool()
def get_question(
    category: str = "aléatoire",
    difficulty: str = "aléatoire",
) -> str:
    """Retourne une question de quiz aléatoire pour tester ses connaissances crypto.

    Args:
        category: Catégorie — 'fondamentaux', 'wallets', 'exchanges', 'risques',
                  'defi', 'fiscalite', ou 'aléatoire'
        difficulty: Difficulté — 'débutant', 'intermédiaire', 'avancé', ou 'aléatoire'

    Returns:
        JSON avec question_id, question, choix A/B/C/D (sans la bonne réponse).
    """
    return _get_question(category=category, difficulty=difficulty)


@mcp.tool()
def check_answer(question_id: str, answer: str) -> str:
    """Vérifie la réponse à une question de quiz et fournit l'explication pédagogique.

    Args:
        question_id: ID de la question retourné par get_question (ex: 'q001')
        answer: Votre réponse — 'A', 'B', 'C' ou 'D'

    Returns:
        JSON avec is_correct, correction, explication et score global mis à jour.
    """
    return _check_answer(question_id=question_id, answer=answer)


@mcp.tool()
def get_score() -> str:
    """Affiche le score global et l'historique des 5 dernières questions.

    Returns:
        JSON avec score (correct/total/pourcentage/niveau) et historique récent.
    """
    return _get_score()


@mcp.tool()
def list_categories() -> str:
    """Liste les catégories de quiz disponibles avec le nombre de questions par niveau.

    Returns:
        JSON avec catégories, nombre de questions et niveaux disponibles.
    """
    return _list_categories()


# ── Point d'entrée standalone ─────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
