"""
Guardrails du CryptoEdu Assistant.

Adapté depuis guardrails.py du projet Agent_Cyber_Career_Compass.

Niveau de filtrage : MODÉRÉ
  → Les conseils d'investissement et prédictions de prix ne sont PAS bloqués ici.
    Ils sont gérés en interne par l'Agent Risques qui répond de façon pédagogique.
    Bloquer ces questions au guardrail priverait l'utilisateur d'une réponse utile.
  → Le guardrail bloque uniquement : hors sujet total, arnaques/manipulation,
    et contenu clairement frauduleux ou dangereux.

Architecture 3 couches (identique au projet Cyber) :
  Couche 1 : mots-clés à bloquer immédiatement (arnaques, manipulation, hors sujet flagrant)
  Couche 2 : mots-clés crypto évidents → passage immédiat sans appel LLM
  Couche 3 : LLM classifieur pour les cas ambigus (fail-safe : PASSAGE si erreur)
             Note : fail-safe inversé par rapport au projet Cyber.
             En éducation crypto, il vaut mieux laisser passer une question ambiguë
             (l'Agent Risques gèrera) que de bloquer un débutant légitime.
"""

import config
from agents import Agent, Runner, GuardrailFunctionOutput, input_guardrail

# ══════════════════════════════════════════════════════════════════════════════
# COUCHE 1 — Mots-clés à bloquer immédiatement
# ══════════════════════════════════════════════════════════════════════════════
# Analogie : le videur à l'entrée qui reconnaît les cas évidents sans réfléchir.

BLOCKED_KEYWORDS = [
    # Arnaques et manipulation de marché
    "pump and dump", "pump & dump", "rug pull", "schéma de ponzi",
    "schéma ponzi", "pyramide financière", "manipulation de cours",
    "gonfler le prix", "faire monter artificiellement",
    "comment arnaquer", "comment escroquer", "comment manipuler",
    # Contenu frauduleux
    "faux token", "faux projet", "fausse ico", "créer une arnaque",
    "comment voler", "voler des cryptos", "voler des fonds",
    "phishing crypto", "créer un faux wallet", "faux exchange",
    # Blanchiment / illégal
    "blanchir", "blanchiment", "argent sale", "financer du terrorisme",
    "contourner les sanctions", "éviter les impôts illégalement",
    "darknet", "dark web achat",
    # Hors sujet flagrant (pour éviter les abus évidents)
    "recette de cuisine", "score du match", "météo demain",
    "aide pour mes devoirs de maths", "écris moi une dissertation",
    "génère moi du code malveillant",
]

# ══════════════════════════════════════════════════════════════════════════════
# COUCHE 2 — Mots-clés crypto éducatifs évidents → passage immédiat
# ══════════════════════════════════════════════════════════════════════════════
# Analogie : la liste VIP — ces questions passent sans attendre le classifieur LLM.

CRYPTO_EDU_KEYWORDS = [
    # Concepts fondamentaux
    "blockchain", "bitcoin", "ethereum", "cryptomonnaie", "crypto-actif",
    "crypto actif", "cryptos", "crypto", "altcoin", "token", "coin",
    "satoshi", "btc", "eth", "sol", "bnb", "xrp", "ada", "doge",
    # Wallets et sécurité
    "wallet", "portefeuille", "seed phrase", "clé privée", "clé publique",
    "hardware wallet", "cold wallet", "hot wallet", "ledger", "trezor",
    "metamask", "adresse wallet", "mnémonique",
    # Plateformes et trading
    "exchange", "cex", "dex", "plateforme", "coinbase", "binance", "kraken",
    "trading", "ordre", "marché", "liquidité", "spread", "frais",
    "psan", "amf", "régulé", "réglementation",
    # DeFi et écosystème
    "defi", "finance décentralisée", "nft", "stablecoin", "staking",
    "yield farming", "liquidity pool", "smart contract", "dao",
    "layer 2", "gas", "gwei", "minage", "proof of work", "proof of stake",
    # Questions débutant
    "débutant", "commencer", "démarrer", "premier achat", "investir",
    "risque", "volatilité", "diversification", "fiscalité", "impôts",
    # Prix et marché (informatif)
    "prix", "cours", "valeur", "capitalisation", "volume", "variation",
    "hausse", "baisse", "bull", "bear", "halving", "coingecko",
]


def _is_blocked(text: str) -> bool:
    """Retourne True si le texte contient des mots-clés à bloquer."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in BLOCKED_KEYWORDS)


def _is_obviously_crypto_edu(text: str) -> bool:
    """Retourne True si le texte contient des mots-clés crypto éducatifs évidents."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in CRYPTO_EDU_KEYWORDS)


# ══════════════════════════════════════════════════════════════════════════════
# GUARDRAIL PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

@input_guardrail
async def crypto_edu_guardrail(ctx, agent, input):
    """
    Filtre les demandes hors périmètre du CryptoEdu Assistant.

    Couche 1 : mots-clés bloquants → blocage immédiat (arnaques, manipulation, hors sujet)
    Couche 2 : mots-clés crypto éducatifs → passage immédiat (sans appel LLM)
    Couche 3 : LLM classifieur pour les cas ambigus
               Fail-safe : PASSAGE (≠ projet Cyber qui bloque)
               Justification : un faux négatif (laisser passer) est moins grave
               qu'un faux positif (bloquer un débutant légitime).
               L'Agent Risques gère les questions maladroites en interne.
    """
    input_str = str(input)

    # ── Couche 1 : Blocage immédiat ──────────────────────────────────────────
    if _is_blocked(input_str):
        return GuardrailFunctionOutput(
            output_info={"classification": "contenu_bloque", "layer": 1},
            tripwire_triggered=True,
        )

    # ── Couche 2 : Passage immédiat ──────────────────────────────────────────
    if _is_obviously_crypto_edu(input_str):
        return GuardrailFunctionOutput(
            output_info={"classification": "crypto_educatif (keywords)", "layer": 2},
            tripwire_triggered=False,
        )

    # ── Couche 3 : LLM classifieur pour les cas ambigus ─────────────────────
    try:
        # Accès dynamique via config.model_fast pour bénéficier du switch à chaud
        classifier = Agent(
            name="Classifieur CryptoEdu",
            instructions=(
                "Tu détermines si une question concerne les cryptomonnaies, "
                "la blockchain, la finance décentralisée, ou l'éducation financière.\n\n"
                "AUTORISÉ (réponds 'crypto_educatif') :\n"
                "- Toute question sur les cryptomonnaies, même maladroitement formulée\n"
                "- Questions sur les risques, la sécurité, la réglementation\n"
                "- Demandes de conseils d'investissement (l'agent interne gèrera le refus)\n"
                "- Prédictions de prix (l'agent interne gèrera le refus)\n"
                "- Questions générales sur la finance ou l'économie avec un lien possible au crypto\n"
                "- Salutations, questions de clarification, messages courts ambigus\n\n"
                "REFUSÉ (réponds 'hors_sujet') :\n"
                "- Questions totalement sans rapport avec les cryptos ou la finance "
                "(cuisine, sport, divertissement, devoirs scolaires...)\n"
                "- Demandes de création d'arnaques, manipulation de marché, blanchiment\n"
                "- Contenu illégal ou frauduleux explicite\n\n"
                "En cas de doute → réponds 'crypto_educatif'.\n"
                "Réponds UNIQUEMENT par 'crypto_educatif' ou 'hors_sujet'. Rien d'autre."
            ),
            model=config.model_fast,
        )

        result = await Runner.run(classifier, input=input_str, max_turns=1)
        classification = result.final_output.strip().lower()

        if "crypto_educatif" in classification:
            is_in_scope = True
        elif "hors_sujet" in classification:
            is_in_scope = False
        else:
            # Réponse inattendue → PASSAGE (fail-safe modéré, ≠ projet Cyber)
            is_in_scope = True

        return GuardrailFunctionOutput(
            output_info={"classification": classification, "layer": 3},
            tripwire_triggered=not is_in_scope,
        )

    except Exception:
        # Si le LLM classifieur échoue → PASSAGE par sécurité (fail-safe modéré)
        # L'Agent Risques en interne gèrera les cas problématiques.
        return GuardrailFunctionOutput(
            output_info={"classification": "erreur_llm_failsafe_passage", "layer": 3},
            tripwire_triggered=False,
        )
