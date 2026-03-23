"""
Serveur MCP — Quiz (JSON local)
Jour 5 : CryptoEdu Assistant

Permet de tester ses connaissances crypto via des quiz.
Les questions sont stockées dans quiz_crypto.json (corpus statique extensible).
Les scores sont sauvegardés dans quiz_scores.json.

Outils exposés :
  - get_question(category, difficulty) : retourne une question aléatoire
  - check_answer(question_id, answer)  : vérifie une réponse et explique
  - get_score()                        : affiche le score et la progression
  - list_categories()                  : liste les catégories disponibles

Lancement standalone : python mcp_quiz.py
Utilisé par : app.py (branché post-réponse)
"""

import json
import random
from datetime import datetime
from pathlib import Path
from agents import function_tool

# ── Fichiers de stockage ──────────────────────────────────────────────────────
QUIZ_FILE   = Path("./quiz_crypto.json")
SCORES_FILE = Path("./quiz_scores.json")

# ══════════════════════════════════════════════════════════════════════════════
# CORPUS DE QUESTIONS (statique, extensible)
# ══════════════════════════════════════════════════════════════════════════════

QUESTIONS = [
    # ── Fondamentaux ──
    {
        "id": "q001",
        "category": "fondamentaux",
        "difficulty": "débutant",
        "question": "Qu'est-ce qu'une blockchain ?",
        "choices": [
            "A. Une banque en ligne spécialisée dans les cryptos",
            "B. Un registre décentralisé et immuable de transactions",
            "C. Un logiciel de minage de Bitcoin",
            "D. Une carte bancaire crypto",
        ],
        "answer": "B",
        "explanation": (
            "Une blockchain est un registre distribué (partagé entre de nombreux ordinateurs) "
            "qui enregistre les transactions de façon immuable — impossible à modifier après coup. "
            "Chaque bloc de données est lié au précédent, formant une chaîne (d'où le nom)."
        ),
    },
    {
        "id": "q002",
        "category": "fondamentaux",
        "difficulty": "débutant",
        "question": "Quelle est la différence principale entre Bitcoin et Ethereum ?",
        "choices": [
            "A. Bitcoin est plus récent qu'Ethereum",
            "B. Ethereum permet des smart contracts, Bitcoin non",
            "C. Bitcoin est décentralisé, Ethereum est centralisé",
            "D. Il n'y a aucune différence",
        ],
        "answer": "B",
        "explanation": (
            "Bitcoin a été créé pour être une monnaie numérique peer-to-peer. "
            "Ethereum va plus loin : il permet d'exécuter des smart contracts "
            "(programmes automatiques) et de créer des applications décentralisées (DApps). "
            "C'est cette flexibilité qui a permis l'essor de la DeFi et des NFT sur Ethereum."
        ),
    },
    {
        "id": "q003",
        "category": "fondamentaux",
        "difficulty": "intermédiaire",
        "question": "Que signifie 'Proof of Work' (PoW) ?",
        "choices": [
            "A. Un système où les validateurs doivent immobiliser des cryptos",
            "B. Un mécanisme de consensus où les mineurs résolvent des problèmes mathématiques",
            "C. Un certificat de conformité pour les exchanges",
            "D. Un protocole de sécurité pour les wallets",
        ],
        "answer": "B",
        "explanation": (
            "Le Proof of Work (utilisé par Bitcoin) est un mécanisme de consensus "
            "où les mineurs rivalisent pour résoudre des calculs mathématiques complexes. "
            "Le premier à trouver la solution valide le bloc et reçoit une récompense. "
            "Ce processus consomme beaucoup d'énergie, contrairement au Proof of Stake."
        ),
    },
    # ── Wallets & Sécurité ──
    {
        "id": "q004",
        "category": "wallets",
        "difficulty": "débutant",
        "question": "Qu'est-ce qu'une seed phrase ?",
        "choices": [
            "A. Le mot de passe de votre compte sur un exchange",
            "B. Une suite de 12 à 24 mots permettant de récupérer un wallet",
            "C. Un code envoyé par SMS pour le 2FA",
            "D. L'adresse publique de votre wallet",
        ],
        "answer": "B",
        "explanation": (
            "La seed phrase (ou phrase mnémonique) est une suite de 12 à 24 mots générés "
            "à la création d'un wallet non-custodial. Elle permet de restaurer l'accès "
            "à tous vos fonds si vous perdez votre appareil. "
            "RÈGLE D'OR : ne la partagez jamais et conservez-la sur papier physique."
        ),
    },
    {
        "id": "q005",
        "category": "wallets",
        "difficulty": "débutant",
        "question": "Que signifie l'expression 'Not your keys, not your coins' ?",
        "choices": [
            "A. Il faut toujours chiffrer ses fichiers de sauvegarde",
            "B. Si vous ne détenez pas vos clés privées, vous ne contrôlez pas vraiment vos cryptos",
            "C. Les clés USB sont le meilleur moyen de stocker des cryptos",
            "D. Il faut avoir plusieurs wallets différents",
        ],
        "answer": "B",
        "explanation": (
            "Cette expression signifie que si vos cryptos sont sur un exchange (wallet custodial), "
            "c'est la plateforme qui détient les clés privées — pas vous. "
            "En cas de faillite (ex: FTX en 2022), vous pouvez perdre vos fonds. "
            "Un wallet non-custodial (hardware wallet) vous donne le contrôle réel."
        ),
    },
    {
        "id": "q006",
        "category": "wallets",
        "difficulty": "intermédiaire",
        "question": "Quelle est la différence entre un hot wallet et un cold wallet ?",
        "choices": [
            "A. Le hot wallet est plus sécurisé car il est chiffré",
            "B. Le cold wallet est connecté à internet, le hot wallet non",
            "C. Le hot wallet est connecté à internet, le cold wallet est hors ligne",
            "D. Il n'y a aucune différence de sécurité",
        ],
        "answer": "C",
        "explanation": (
            "Un hot wallet (chaud) est connecté à internet : pratique pour les transactions "
            "fréquentes, mais plus exposé aux piratages. "
            "Un cold wallet (froid) est hors ligne : un hardware wallet comme Ledger ou Trezor "
            "qui signe les transactions sans exposer les clés privées à internet. "
            "Recommandé pour stocker de grandes quantités."
        ),
    },
    # ── Exchanges ──
    {
        "id": "q007",
        "category": "exchanges",
        "difficulty": "débutant",
        "question": "Qu'est-ce qu'un CEX (Centralized Exchange) ?",
        "choices": [
            "A. Un exchange décentralisé fonctionnant avec des smart contracts",
            "B. Une plateforme d'échange gérée par une entreprise centralisée",
            "C. Un protocole de minage de cryptomonnaies",
            "D. Un wallet hardware certifié",
        ],
        "answer": "B",
        "explanation": (
            "Un CEX est une plateforme d'échange gérée par une entreprise (Coinbase, Binance, Kraken). "
            "Elle agit comme intermédiaire : vous lui confiez vos fonds. "
            "Avantages : simple, liquide, support client. "
            "Risque : si la plateforme fait faillite, vous pouvez perdre vos fonds."
        ),
    },
    {
        "id": "q008",
        "category": "exchanges",
        "difficulty": "intermédiaire",
        "question": "Qu'est-ce que le KYC dans le contexte des exchanges crypto ?",
        "choices": [
            "A. Un type de wallet sécurisé",
            "B. La vérification d'identité obligatoire sur les plateformes régulées",
            "C. Un protocole de chiffrement des transactions",
            "D. Une taxe sur les gains en cryptomonnaies",
        ],
        "answer": "B",
        "explanation": (
            "KYC signifie 'Know Your Customer' (Connaître son client). "
            "Les plateformes régulées (PSAN en France) sont obligées de vérifier l'identité "
            "de leurs utilisateurs pour lutter contre le blanchiment d'argent et le financement du terrorisme. "
            "Vous devrez fournir une pièce d'identité et parfois un justificatif de domicile."
        ),
    },
    # ── Risques & Réglementation ──
    {
        "id": "q009",
        "category": "risques",
        "difficulty": "débutant",
        "question": "Selon l'AMF, comment sont classés les crypto-actifs ?",
        "choices": [
            "A. Investissements sûrs recommandés pour les débutants",
            "B. Actifs spéculatifs à haut risque",
            "C. Équivalents aux obligations d'État",
            "D. Monnaies légales reconnues par la BCE",
        ],
        "answer": "B",
        "explanation": (
            "L'AMF (Autorité des Marchés Financiers) classe les crypto-actifs comme "
            "des investissements spéculatifs à haut risque. "
            "Les prix peuvent fluctuer de ±80-90 % en quelques mois. "
            "L'AMF recommande de n'investir que ce qu'on peut se permettre de perdre entièrement."
        ),
    },
    {
        "id": "q010",
        "category": "risques",
        "difficulty": "intermédiaire",
        "question": "Qu'est-ce qu'un 'rug pull' dans l'univers crypto ?",
        "choices": [
            "A. Une technique de minage avancée",
            "B. Une arnaque où les créateurs d'un projet abandonnent en emportant les fonds",
            "C. Un mécanisme de stabilisation des stablecoins",
            "D. Un type de wallet hardware",
        ],
        "answer": "B",
        "explanation": (
            "Un rug pull (littéralement 'tirer le tapis') est une arnaque où les développeurs "
            "d'un projet crypto créent un token, attirent des investisseurs, puis disparaissent "
            "avec tous les fonds. C'est l'une des arnaques les plus courantes dans la DeFi. "
            "Protection : vérifier l'équipe, l'audit du code, la liquidité verrouillée."
        ),
    },
    # ── DeFi & Écosystème ──
    {
        "id": "q011",
        "category": "defi",
        "difficulty": "intermédiaire",
        "question": "Qu'est-ce qu'un stablecoin ?",
        "choices": [
            "A. Une cryptomonnaie dont le prix est indexé sur une valeur stable (ex: dollar)",
            "B. Un Bitcoin stocké de façon sécurisée",
            "C. Un token qui ne peut pas être échangé",
            "D. Une cryptomonnaie émise par une banque centrale",
        ],
        "answer": "A",
        "explanation": (
            "Un stablecoin est une cryptomonnaie conçue pour maintenir une valeur stable, "
            "généralement indexée sur une monnaie fiat (USDT, USDC → 1 dollar) "
            "ou sur d'autres actifs. Ils permettent de rester dans l'écosystème crypto "
            "sans être exposé à la volatilité du Bitcoin ou de l'Ethereum."
        ),
    },
    {
        "id": "q012",
        "category": "defi",
        "difficulty": "avancé",
        "question": "Qu'est-ce qu'un smart contract ?",
        "choices": [
            "A. Un contrat légal entre deux parties pour acheter des cryptos",
            "B. Un programme auto-exécutant déployé sur une blockchain",
            "C. Un wallet sécurisé avec signature multiple",
            "D. Un accord entre miners pour valider les blocs",
        ],
        "answer": "B",
        "explanation": (
            "Un smart contract est un programme informatique déployé sur une blockchain "
            "(principalement Ethereum) qui s'exécute automatiquement quand des conditions "
            "prédéfinies sont remplies — sans intermédiaire. "
            "Exemple : un DEX utilise des smart contracts pour échanger des tokens "
            "de façon automatique et transparente."
        ),
    },
    # ── Fiscalité ──
    {
        "id": "q013",
        "category": "fiscalite",
        "difficulty": "débutant",
        "question": "En France, les plus-values sur crypto-actifs sont-elles imposables ?",
        "choices": [
            "A. Non, les cryptos ne sont pas encore régulées fiscalement",
            "B. Oui, elles sont soumises à la flat-tax de 30 % par défaut",
            "C. Oui, mais seulement au-delà de 10 000 € de gains",
            "D. Non, si vous gardez vos cryptos plus d'un an",
        ],
        "answer": "B",
        "explanation": (
            "En France, les plus-values sur cession de crypto-actifs sont imposables. "
            "Par défaut, elles sont soumises au Prélèvement Forfaitaire Unique (PFU) "
            "ou flat-tax de 30 % (12,8 % d'impôt + 17,2 % de prélèvements sociaux). "
            "Il est obligatoire de déclarer ses comptes ouverts à l'étranger "
            "et de conserver l'historique de toutes ses transactions."
        ),
    },
]

# Sauvegarde du corpus si le fichier n'existe pas
if not QUIZ_FILE.exists():
    QUIZ_FILE.write_text(
        json.dumps(QUESTIONS, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def _load_questions() -> list:
    try:
        return json.loads(QUIZ_FILE.read_text(encoding="utf-8"))
    except Exception:
        return QUESTIONS


def _load_scores() -> dict:
    if not SCORES_FILE.exists():
        return {"total": 0, "correct": 0, "history": []}
    try:
        return json.loads(SCORES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"total": 0, "correct": 0, "history": []}


def _save_scores(scores: dict):
    SCORES_FILE.write_text(
        json.dumps(scores, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


# ══════════════════════════════════════════════════════════════════════════════
# OUTILS MCP
# ══════════════════════════════════════════════════════════════════════════════

def _get_question(category: str = "aléatoire", difficulty: str = "aléatoire") -> str:
    """Retourne une question de quiz aléatoire pour tester ses connaissances crypto.

    Args:
        category   : Catégorie — 'fondamentaux', 'wallets', 'exchanges', 'risques',
                     'defi', 'fiscalite', ou 'aléatoire'
        difficulty : Difficulté — 'débutant', 'intermédiaire', 'avancé', ou 'aléatoire'

    Returns:
        Une question avec ses choix de réponse (sans la bonne réponse).
    """
    questions = _load_questions()

    # Filtrage par catégorie
    if category != "aléatoire":
        filtered = [q for q in questions if q["category"] == category]
        if not filtered:
            filtered = questions
    else:
        filtered = questions

    # Filtrage par difficulté
    if difficulty != "aléatoire":
        filtered_diff = [q for q in filtered if q["difficulty"] == difficulty]
        if filtered_diff:
            filtered = filtered_diff

    if not filtered:
        return json.dumps({
            "error": "Aucune question trouvée pour ces critères.",
        }, ensure_ascii=False)

    question = random.choice(filtered)

    return json.dumps({
        "question_id": question["id"],
        "category": question["category"],
        "difficulty": question["difficulty"],
        "question": question["question"],
        "choices": question["choices"],
        "instruction": "Répondez avec check_answer(question_id, answer) en indiquant A, B, C ou D.",
    }, ensure_ascii=False, indent=2)


def _check_answer(question_id: str, answer: str) -> str:
    """Vérifie la réponse à une question de quiz et fournit l'explication.

    Args:
        question_id : ID de la question (ex: 'q001')
        answer      : Votre réponse — 'A', 'B', 'C' ou 'D'

    Returns:
        Correction détaillée avec explication pédagogique.
    """
    questions = _load_questions()
    question = next((q for q in questions if q["id"] == question_id), None)

    if not question:
        return json.dumps({
            "error": f"Question '{question_id}' introuvable.",
        }, ensure_ascii=False)

    answer_clean = answer.strip().upper()
    is_correct = (answer_clean == question["answer"])

    # Mise à jour du score
    scores = _load_scores()
    scores["total"] += 1
    if is_correct:
        scores["correct"] += 1
    scores["history"].append({
        "question_id": question_id,
        "question": question["question"][:60] + "...",
        "user_answer": answer_clean,
        "correct_answer": question["answer"],
        "is_correct": is_correct,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    _save_scores(scores)

    # Score global
    pct = round(scores["correct"] / scores["total"] * 100) if scores["total"] > 0 else 0

    return json.dumps({
        "is_correct": is_correct,
        "result": "✅ Bonne réponse !" if is_correct else "❌ Mauvaise réponse.",
        "your_answer": answer_clean,
        "correct_answer": question["answer"],
        "explanation": question["explanation"],
        "score_global": {
            "correct": scores["correct"],
            "total": scores["total"],
            "pourcentage": f"{pct}%",
        },
    }, ensure_ascii=False, indent=2)


def _get_score() -> str:
    """Affiche le score global et l'historique récent des quiz.

    Returns:
        Score, progression et dernières questions répondues.
    """
    scores = _load_scores()

    if scores["total"] == 0:
        return json.dumps({
            "message": "Aucun quiz effectué pour l'instant. Utilisez get_question() pour commencer !",
            "score": {"correct": 0, "total": 0, "pourcentage": "0%"},
        }, ensure_ascii=False)

    pct = round(scores["correct"] / scores["total"] * 100)

    # Niveau en fonction du score
    if pct >= 80:
        niveau = "🏆 Expert — Excellentes connaissances !"
    elif pct >= 60:
        niveau = "📈 Intermédiaire — Continuez à apprendre !"
    elif pct >= 40:
        niveau = "📚 Débutant confirmé — Encore quelques efforts !"
    else:
        niveau = "🌱 Débutant — Lisez les guides et retentez !"

    return json.dumps({
        "score": {
            "correct": scores["correct"],
            "total": scores["total"],
            "pourcentage": f"{pct}%",
            "niveau": niveau,
        },
        "dernières_questions": scores["history"][-5:],
    }, ensure_ascii=False, indent=2)


def _list_categories() -> str:
    """Liste les catégories de quiz disponibles avec le nombre de questions par catégorie.

    Returns:
        Catégories disponibles et niveaux de difficulté.
    """
    questions = _load_questions()
    categories = {}
    for q in questions:
        cat = q["category"]
        if cat not in categories:
            categories[cat] = {"total": 0, "difficulties": set()}
        categories[cat]["total"] += 1
        categories[cat]["difficulties"].add(q["difficulty"])

    result = {}
    for cat, data in categories.items():
        result[cat] = {
            "questions": data["total"],
            "niveaux": sorted(list(data["difficulties"])),
        }

    return json.dumps({
        "categories": result,
        "total_questions": len(questions),
        "instruction": "Utilisez get_question(category='nom_categorie') pour commencer.",
    }, ensure_ascii=False, indent=2)


# ── Wrapping function_tool
get_question    = function_tool(_get_question)
check_answer    = function_tool(_check_answer)
get_score       = function_tool(_get_score)
list_categories = function_tool(_list_categories)

# ── Export des outils pour import dans app.py ─────────────────────────────────
QUIZ_TOOLS = [get_question, check_answer, get_score, list_categories]


# ── Test standalone ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Test MCP Quiz ===\n")

    print("1. Catégories disponibles...")
    cats = json.loads(_list_categories())
    print(f"   → {cats['total_questions']} questions dans {len(cats['categories'])} catégories")
    for cat, data in cats["categories"].items():
        print(f"      - {cat} : {data['questions']} question(s)")

    print("\n2. Question aléatoire débutant...")
    q = json.loads(_get_question(category="aléatoire", difficulty="débutant"))
    print(f"   → [{q['category']}] {q['question']}")
    for choice in q["choices"]:
        print(f"      {choice}")

    print("\n3. Réponse à la question...")
    result = json.loads(_check_answer(question_id=q["question_id"], answer="B"))
    print(f"   → {result['result']}")
    print(f"   → Score : {result['score_global']['correct']}/{result['score_global']['total']}")

    print("\n4. Score global...")
    score = json.loads(_get_score())
    print(f"   → {score['score']['pourcentage']} — {score['score']['niveau']}")

    print("\n✅ Tests MCP Quiz terminés.")
