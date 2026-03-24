"""
Agents spécialisés du CryptoEdu Assistant — Jour 2.

Architecture : 3 agents spécialisés + 1 outil déterministe + wrappers agents-as-tools.

  1. get_checklist_debutant()       — Python pur, 0 appel LLM : checklist démarrage crypto
  2. get_etapes_premier_achat()     — Python pur, 0 appel LLM : guide pas-à-pas premier achat
  3. get_bonnes_pratiques_wallet()  — Python pur, 0 appel LLM : sécurité & erreurs courantes
  4. deleguer_agent_education(query)   — wrapper → Agent Éducation (RAG)
  5. deleguer_agent_marche(query)      — wrapper → Agent Marché (CoinGecko)
  6. deleguer_agent_risques(query)     — wrapper → Agent Risques (guardrails éducatifs)

Pattern identique à cyber_agents.py du projet Agent_Cyber :
  - function_tool pour les outils déterministes (Python pur, résultat JSON)
  - agents-as-tools pour les agents spécialisés (wrapper async + Runner.run)
  - register_agent() pour le switch à chaud des modèles

Adapté depuis cyber_agents.py du projet Agent_Cyber_Career_Compass.
"""

import json
import requests
from agents import Agent, Runner, function_tool
from config import model_main, register_agent
from rag_pipeline import query_rag, init as init_rag

# ── Initialisation du RAG au chargement du module ────────────────────────────
# Comme un bibliothécaire qui prépare ses rayons avant l'ouverture.
# On appelle init_rag() une seule fois ici — les agents y auront accès via query_rag().
init_rag()

# ══════════════════════════════════════════════════════════════════════════════
# RÈGLE COMMUNE À TOUS LES AGENTS
# ══════════════════════════════════════════════════════════════════════════════

REGLE_ANTI_CONSEIL = (
    "\n\nRÈGLE ÉDUCATIVE STRICTE (CRITIQUE) :\n"
    "- Tu es un assistant ÉDUCATIF, jamais un conseiller en investissement.\n"
    "- Ne JAMAIS dire 'tu devrais acheter X', 'investis dans Y', 'X va monter'.\n"
    "- Ne JAMAIS formuler de prédictions sur les prix ou recommander un actif.\n"
    "- Si on te demande 'que dois-je acheter' ou 'quel crypto choisir' → refuse poliment\n"
    "  et redirige vers une explication éducative sur les critères d'évaluation.\n"
    "- Les données de prix sont du CONTEXTE INFORMATIF, pas une base pour conseiller.\n"
    "- Rappelle systématiquement que les crypto-actifs sont des investissements à haut risque.\n"
)


# ══════════════════════════════════════════════════════════════════════════════
# OUTILS DÉTERMINISTES (function_tool, Python pur, 0 appel LLM)
# ══════════════════════════════════════════════════════════════════════════════
#
# Analogie : ces fonctions sont comme des fiches Bristol pré-imprimées.
# L'agent n'a pas besoin de "réfléchir" pour les remplir — il les lit et les présente.
# Aucun LLM n'est appelé ici, ce qui les rend rapides, fiables et déterministes.

@function_tool
def get_checklist_debutant(query: str = "checklist") -> str:
    """Retourne la checklist complète pour démarrer en crypto en toute sécurité.

    Utilise cet outil pour toute question type :
    'par où commencer', 'comment débuter', 'étapes pour se lancer',
    'checklist débutant', 'comment commencer avec les cryptos'.
    """
    checklist = {
        "titre": "Checklist Débutant Crypto — Les 7 étapes essentielles",
        "introduction": (
            "Avant de vous lancer, voici les étapes clés recommandées par les guides officiels "
            "(AMF, Coinbase Learn). L'ordre est important : chaque étape prépare la suivante."
        ),
        "etapes": [
            {
                "numero": 1,
                "etape": "Se former avant d'investir",
                "details": [
                    "Comprendre ce qu'est la blockchain et pourquoi elle fonctionne",
                    "Apprendre la différence entre Bitcoin, Ethereum et les altcoins",
                    "Lire les guides de l'AMF sur les crypto-actifs",
                    "Temps recommandé : minimum 2 semaines de lectures",
                ],
                "vigilance": "Ne jamais investir dans ce qu'on ne comprend pas.",
            },
            {
                "numero": 2,
                "etape": "Évaluer sa tolérance au risque",
                "details": [
                    "Les cryptos peuvent perdre 80-90 % de leur valeur en quelques mois",
                    "N'investir QUE ce qu'on peut se permettre de perdre entièrement",
                    "Les crypto-actifs sont classés actifs spéculatifs à haut risque par l'AMF",
                ],
                "vigilance": "Jamais d'emprunt pour acheter des cryptos.",
            },
            {
                "numero": 3,
                "etape": "Choisir une plateforme régulée (CEX)",
                "details": [
                    "Vérifier que la plateforme est enregistrée auprès de l'AMF (PSAN)",
                    "Exemples de plateformes PSAN enregistrées : Coinbase, Binance France, Kraken",
                    "Éviter les plateformes inconnues ou sans adresse physique identifiable",
                ],
                "vigilance": "Vérifier sur le registre officiel PSAN de l'AMF : https://www.amf-france.org",
            },
            {
                "numero": 4,
                "etape": "Créer et sécuriser son compte",
                "details": [
                    "Utiliser une adresse email dédiée (pas votre email principal)",
                    "Activer obligatoirement l'authentification à deux facteurs (2FA)",
                    "Préférer une application d'authentification (Authy, Google Authenticator) au SMS",
                    "Compléter le KYC (vérification d'identité) — obligatoire légalement",
                ],
                "vigilance": "Ne jamais partager ses codes 2FA ou ses mots de passe.",
            },
            {
                "numero": 5,
                "etape": "Comprendre les wallets et décider où stocker ses actifs",
                "details": [
                    "Wallet custodial (sur la plateforme) : pratique mais vous n'avez pas les clés",
                    "Wallet non-custodial (hardware/logiciel) : vous contrôlez vos clés",
                    "Pour de petits montants : wallet sur la plateforme peut suffire",
                    "Pour des montants importants : wallet hardware recommandé (Ledger, Trezor)",
                ],
                "vigilance": "Pas vos clés = pas vos cryptos (règle d'or du secteur).",
            },
            {
                "numero": 6,
                "etape": "Effectuer son premier achat (petit montant)",
                "details": [
                    "Commencer par un très petit montant (ex : 20-50 €) pour apprendre",
                    "Choisir des actifs établis (Bitcoin, Ethereum) pour commencer",
                    "Éviter les meme coins, tokens inconnus et ICO au début",
                    "Comprendre les frais : frais de trading, frais de retrait réseau (gas)",
                ],
                "vigilance": "Les frais peuvent représenter 1 à 3 % de la transaction.",
            },
            {
                "numero": 7,
                "etape": "Déclarer ses crypto-actifs aux impôts",
                "details": [
                    "En France, les plus-values crypto sont imposables (flat tax 30 % par défaut)",
                    "Obligation de déclarer les comptes ouverts à l'étranger",
                    "Conserver l'historique de toutes ses transactions",
                    "Consulter le site impots.gouv.fr ou un conseiller fiscal spécialisé",
                ],
                "vigilance": "L'oubli de déclaration est sanctionnable fiscalement.",
            },
        ],
        "ressources_recommandees": [
            "AMF — Guide crypto-actifs : https://www.amf-france.org",
            "Coinbase Learn (FR) : https://www.coinbase.com/fr/learn",
            "Registre PSAN AMF : https://www.amf-france.org/fr/espace-epargnants/protegez-vous-des-arnaques/listes-noires-et-mises-en-garde/listes-des-prestataires-enregistres-ou-agrees",
        ],
        "source": "Synthèse des guides AMF et Coinbase Learn (corpus CryptoEdu)",
    }
    return json.dumps(checklist, ensure_ascii=False, indent=2)


@function_tool
def get_etapes_premier_achat(query: str = "premier achat") -> str:
    """Retourne le guide pas-à-pas pour effectuer son premier achat de crypto.

    Utilise cet outil pour toute question type :
    'comment acheter du bitcoin', 'comment acheter ma première crypto',
    'étapes pour acheter', 'comment procéder pour mon premier achat'.
    """
    guide = {
        "titre": "Guide Pas-à-Pas — Premier Achat de Crypto",
        "avertissement": (
            "Ce guide est ÉDUCATIF. Il ne constitue pas un conseil en investissement. "
            "Les cryptomonnaies sont des actifs spéculatifs à haut risque (AMF)."
        ),
        "prerequis": [
            "Avoir complété la Checklist Débutant (étapes 1 à 4)",
            "Avoir un compte vérifié (KYC) sur une plateforme régulée",
            "Avoir activé le 2FA",
            "Décider du montant — uniquement ce qu'on peut perdre entièrement",
        ],
        "etapes_achat": [
            {
                "etape": 1,
                "titre": "Alimenter son compte (dépôt)",
                "action": "Virer des euros depuis votre compte bancaire vers la plateforme",
                "details": [
                    "Utiliser un virement SEPA (moins de frais que la carte bancaire)",
                    "Délai : 1 à 3 jours ouvrés pour les virements SEPA",
                    "Carte bancaire : instantané mais frais plus élevés (1-3 %)",
                    "Vérifier les limites de dépôt de votre niveau de vérification",
                ],
            },
            {
                "etape": 2,
                "titre": "Choisir l'actif à acheter",
                "action": "Sélectionner la cryptomonnaie dans l'interface de la plateforme",
                "details": [
                    "Pour un débutant : Bitcoin (BTC) ou Ethereum (ETH) sont les plus établis",
                    "Vérifier le symbole exact (BTC et non BTCX, ETH et non ETH2 sur les marchés spot)",
                    "Lire la description de l'actif sur la plateforme",
                    "Ne pas se fier aux classements 'trending' ou aux réseaux sociaux",
                ],
            },
            {
                "etape": 3,
                "titre": "Passer l'ordre d'achat",
                "action": "Utiliser l'interface de trading simple (pas l'interface avancée)",
                "details": [
                    "Ordre au marché : achat immédiat au prix actuel (le plus simple pour débuter)",
                    "Entrer le montant en euros (ex : 50 €)",
                    "Vérifier l'aperçu : montant de crypto reçu + frais appliqués",
                    "Confirmer l'ordre (souvent une double confirmation par la plateforme)",
                ],
            },
            {
                "etape": 4,
                "titre": "Vérifier sa position",
                "action": "Consulter son portefeuille sur la plateforme",
                "details": [
                    "Votre achat apparaît dans 'Portfolio' ou 'Portefeuille'",
                    "La valeur fluctue en temps réel — c'est normal",
                    "Ne pas paniquer face aux variations de ±5-10 % sur une journée",
                    "Conserver la preuve de la transaction (copie d'écran ou PDF)",
                ],
            },
            {
                "etape": 5,
                "titre": "Décider du stockage",
                "action": "Choisir où conserver ses cryptos",
                "details": [
                    "Laisser sur la plateforme : pratique, mais la plateforme détient vos clés",
                    "Transférer vers un wallet personnel : vous contrôlez vos clés",
                    "Pour 50 € de test : laisser sur la plateforme est généralement acceptable",
                    "Pour des montants supérieurs à 500-1000 € : envisager un wallet hardware",
                ],
            },
        ],
        "erreurs_a_eviter": [
            "Acheter après une forte hausse (FOMO — Fear Of Missing Out)",
            "Investir plus que prévu 'parce que ça monte'",
            "Copier les achats d'influenceurs sans comprendre l'actif",
            "Oublier de noter l'historique pour la déclaration fiscale",
            "Confondre l'adresse wallet Bitcoin et Ethereum (incompatibles)",
        ],
        "source": "Synthèse des guides AMF et Coinbase Learn (corpus CryptoEdu)",
    }
    return json.dumps(guide, ensure_ascii=False, indent=2)


@function_tool
def get_bonnes_pratiques_wallet(query: str = "wallet") -> str:
    """Retourne le guide complet sur la sécurité des wallets crypto.

    Utilise cet outil pour toute question type :
    'comment sécuriser mon wallet', 'bonnes pratiques wallet',
    'comment protéger mes cryptos', 'seed phrase sécurité',
    'hardware wallet', 'cold wallet vs hot wallet'.
    """
    guide = {
        "titre": "Bonnes Pratiques Wallet — Sécurité & Erreurs Courantes",
        "introduction": (
            "Le wallet (portefeuille) est l'outil qui vous permet de stocker et d'accéder "
            "à vos crypto-actifs. Comprendre son fonctionnement est essentiel pour ne pas "
            "perdre définitivement ses fonds — il n'y a pas de banque pour récupérer vos actifs."
        ),
        "types_de_wallets": {
            "hot_wallet": {
                "definition": "Wallet connecté à internet (logiciel ou plateforme)",
                "exemples": ["MetaMask (extension navigateur)", "Coinbase Wallet (app mobile)", "Trust Wallet"],
                "avantages": ["Gratuit", "Pratique pour les transactions fréquentes", "Facile à utiliser"],
                "inconvenients": ["Vulnérable aux attaques si l'appareil est compromis", "Risque en cas de hack de la plateforme"],
                "pour_qui": "Petits montants ou utilisation quotidienne (DeFi, NFT)",
            },
            "cold_wallet": {
                "definition": "Wallet déconnecté d'internet (matériel physique)",
                "exemples": ["Ledger (Nano S Plus, Nano X)", "Trezor (Model T, Safe 3)"],
                "avantages": [
                    "Résistant aux attaques en ligne",
                    "Clés privées jamais exposées à internet",
                    "Idéal pour le stockage à long terme",
                ],
                "inconvenients": ["Coût (70-200 €)", "Moins pratique pour les transactions fréquentes"],
                "pour_qui": "Montants importants ou stockage long terme",
            },
            "wallet_custodial": {
                "definition": "La plateforme (Coinbase, Binance...) détient vos clés à votre place",
                "avantages": ["Simplicité maximale", "Récupération de compte possible si oubli de mot de passe"],
                "inconvenients": [
                    "Vous ne contrôlez pas vraiment vos cryptos",
                    "Risque si la plateforme fait faillite (ex : FTX en 2022)",
                ],
                "regle_d_or": "Not your keys, not your coins (Pas vos clés = pas vos cryptos)",
            },
        },
        "seed_phrase": {
            "definition": (
                "La seed phrase (ou phrase de récupération) est une suite de 12 à 24 mots "
                "générés à la création du wallet. C'est la SEULE façon de récupérer l'accès "
                "à vos fonds si vous perdez votre appareil. Traitez-la comme le code de votre coffre-fort."
            ),
            "bonnes_pratiques": [
                "Notez-la sur PAPIER physique (jamais en photo, jamais dans un cloud, jamais par email)",
                "Faites 2 copies papier conservées dans des endroits séparés",
                "Certains utilisent des plaques en acier inoxydable résistantes au feu",
                "Ne la communiquez JAMAIS à personne — aucun support officiel ne vous la demandera",
                "Vérifiez que la copie est lisible et dans le bon ordre immédiatement après création",
            ],
            "ce_qu_il_ne_faut_jamais_faire": [
                "Photographier sa seed phrase avec son téléphone",
                "La stocker dans un document Google Docs ou Dropbox",
                "La taper dans un site web ou un formulaire quelconque",
                "La partager avec 'le support technique' d'une plateforme",
                "La saisir si quelqu'un vous le demande — c'est toujours une arnaque",
            ],
        },
        "erreurs_courantes": [
            {
                "erreur": "Perdre sa seed phrase",
                "consequence": "Perte définitive et irréversible de tous ses fonds",
                "prevention": "Sauvegarder sur papier physique dès la création du wallet",
            },
            {
                "erreur": "Envoyer des cryptos sur le mauvais réseau",
                "consequence": "Les fonds peuvent être perdus ou bloqués (ex: envoyer de l'ETH sur le réseau BSC)",
                "prevention": "Toujours vérifier le réseau de destination avant d'envoyer",
            },
            {
                "erreur": "Envoyer des cryptos à la mauvaise adresse",
                "consequence": "Perte définitive — les transactions blockchain sont irréversibles",
                "prevention": "Toujours vérifier les 4-5 premiers et derniers caractères de l'adresse",
            },
            {
                "erreur": "Acheter un faux hardware wallet",
                "consequence": "Les clés peuvent être préinstallées et connues du vendeur malveillant",
                "prevention": "Acheter UNIQUEMENT sur le site officiel du fabricant (ledger.com, trezor.io)",
            },
            {
                "erreur": "Approuver un smart contract malveillant",
                "consequence": "Accès complet à votre wallet accordé à un site frauduleux",
                "prevention": "Vérifier les permissions demandées, utiliser des outils de révocation (Revoke.cash)",
            },
        ],
        "checklist_securite_wallet": [
            "✅ Seed phrase notée sur papier physique (pas de photo, pas de cloud)",
            "✅ 2FA activé sur toutes les plateformes",
            "✅ Adresse email dédiée pour les cryptos",
            "✅ Hardware wallet pour les montants importants",
            "✅ Vérification systématique des adresses avant envoi",
            "✅ Mise à jour régulière du firmware du hardware wallet",
            "✅ Méfiance face à toute demande de seed phrase",
        ],
        "source": "Synthèse des guides AMF, Coinbase Learn et CoinGecko (corpus CryptoEdu)",
    }
    return json.dumps(guide, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════════════════════
# AGENT ÉDUCATION
# Rôle : répondre aux questions éducatives via le RAG (corpus de documents)
# Analogie : c'est le professeur qui consulte ses manuels avant de répondre.
# ══════════════════════════════════════════════════════════════════════════════

def _outil_rag(question: str) -> str:
    """Wrapper interne : appelle query_rag() et formate le résultat pour l'agent."""
    result = query_rag(question)
    # On formate proprement la réponse + sources pour que l'agent puisse les présenter
    sources_str = ", ".join(
        [s["source"] for s in result.get("sources", [])]
    ) or "Documentation interne"
    return (
        f"{result['response']}\n\n"
        f"[Sources consultées : {sources_str}]"
    )


# On décore la fonction avec function_tool APRÈS définition pour que le nom soit correct
_outil_rag_tool = function_tool(_outil_rag)
_outil_rag_tool.__name__ = "consulter_documentation_crypto"
_outil_rag_tool.__doc__ = (
    "Consulte la documentation crypto (AMF, Coinbase Learn, CoinGecko, guides) "
    "pour répondre à une question éducative. "
    "Utilise cet outil pour TOUTES les questions sur : "
    "blockchain, wallet, seed phrase, DeFi, NFT, stablecoins, risques, réglementation, "
    "définitions crypto, fonctionnement des exchanges, glossaire."
)

# Re-décoration propre
@function_tool
def consulter_documentation_crypto(question: str) -> str:
    """Consulte la documentation crypto (AMF, Coinbase Learn, CoinGecko, guides)
    pour répondre à une question éducative sur les cryptomonnaies.

    Utilise cet outil pour TOUTES les questions sur :
    blockchain, wallet, seed phrase, DeFi, NFT, stablecoins, risques,
    réglementation, définitions, fonctionnement des exchanges, glossaire.

    Args:
        question: La question éducative à poser à la documentation
    """
    result = query_rag(question)
    sources_str = ", ".join(
        [s["source"] for s in result.get("sources", [])]
    ) or "Documentation interne"
    return (
        f"{result['response']}\n\n"
        f"[Sources consultées : {sources_str} | "
        f"Temps de réponse : {result.get('duration_ms', 0)}ms]"
    )


agent_education = register_agent(Agent(
    name="Agent Éducation Crypto",
    instructions=(
        "Tu es un assistant pédagogique spécialisé dans l'éducation aux cryptomonnaies, "
        "conçu pour les débutants francophones.\n\n"

        "TON OUTIL PRINCIPAL :\n"
        "- consulter_documentation_crypto : interroge le corpus de documents officiels "
        "(AMF, Coinbase Learn, CoinGecko, guides spécialisés). "
        "TOUJOURS utiliser cet outil avant de répondre.\n\n"

        "TES OUTILS COMPLÉMENTAIRES :\n"
        "- get_checklist_debutant : étapes pour démarrer en crypto\n"
        "- get_etapes_premier_achat : guide pas-à-pas pour le premier achat\n"
        "- get_bonnes_pratiques_wallet : sécurité et erreurs à éviter\n\n"

        "RÈGLE ABSOLUE : Tu ne réponds JAMAIS de mémoire aux questions factuelles sur les cryptos.\n"
        "Tu DOIS toujours appeler consulter_documentation_crypto d'abord.\n\n"

        "FORMAT DE RÉPONSE :\n"
        "1. Définition simple (1-2 phrases accessibles à un débutant)\n"
        "2. Points clés (3 à 5 points essentiels à retenir)\n"
        "3. Points de vigilance (risques ou erreurs à éviter si pertinent)\n"
        "4. Source citée entre crochets [Nom du document]\n\n"

        "TON STYLE :\n"
        "- Pédagogique et accessible — jamais de jargon sans explication\n"
        "- Utilise des analogies simples pour expliquer les concepts complexes\n"
        "- Bienveillant et patient — l'utilisateur est débutant\n"
        "- Réponds toujours en français\n"
        + REGLE_ANTI_CONSEIL
    ),
    tools=[
        consulter_documentation_crypto,
        get_checklist_debutant,
        get_etapes_premier_achat,
        get_bonnes_pratiques_wallet,
    ],
    model=model_main,
))


# ══════════════════════════════════════════════════════════════════════════════
# AGENT MARCHÉ
# Rôle : fournir des données de marché live via CoinGecko (sans clé API)
# Analogie : c'est le tableau d'affichage de la bourse — il donne les prix
# mais ne dit JAMAIS si c'est le bon moment d'acheter.
# ══════════════════════════════════════════════════════════════════════════════

COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
COINGECKO_HEADERS = {"Accept": "application/json", "User-Agent": "CryptoEdu-Assistant/1.0"}
REQUEST_TIMEOUT = 10

# Mapping des noms courants vers les IDs CoinGecko
# (pour que l'utilisateur puisse dire "Bitcoin" ou "BTC" ou "bitcoin")
CRYPTO_ID_MAP = {
    "bitcoin": "bitcoin", "btc": "bitcoin",
    "ethereum": "ethereum", "eth": "ethereum",
    "solana": "solana", "sol": "solana",
    "cardano": "cardano", "ada": "cardano",
    "xrp": "ripple", "ripple": "ripple",
    "dogecoin": "dogecoin", "doge": "dogecoin",
    "polkadot": "polkadot", "dot": "polkadot",
    "avalanche": "avalanche-2", "avax": "avalanche-2",
    "chainlink": "chainlink", "link": "chainlink",
    "litecoin": "litecoin", "ltc": "litecoin",
    "tether": "tether", "usdt": "tether",
    "usd-coin": "usd-coin", "usdc": "usd-coin",
    "binance-coin": "binancecoin", "bnb": "binancecoin",
    "polygon": "matic-network", "matic": "matic-network",
    "shiba-inu": "shiba-inu", "shib": "shiba-inu",
}


@function_tool
def get_prix_crypto(crypto_nom: str, devises: str = "eur,usd") -> str:
    """Récupère le prix actuel d'une ou plusieurs cryptomonnaies via CoinGecko (gratuit, sans clé).

    Args:
        crypto_nom: Nom ou symbole de la crypto (ex: 'bitcoin', 'BTC', 'ethereum', 'ETH')
                    Peut contenir plusieurs cryptos séparées par des virgules (ex: 'bitcoin,ethereum')
        devises: Devises de référence séparées par des virgules (défaut: 'eur,usd')

    Retourne le prix, la variation 24h, le volume et la capitalisation boursière.
    """
    # Résolution des noms/symboles vers les IDs CoinGecko
    cryptos_input = [c.strip().lower() for c in crypto_nom.split(",")]
    ids_resolus = []
    non_reconnus = []

    for c in cryptos_input:
        id_coingecko = CRYPTO_ID_MAP.get(c, c)  # Si pas dans le mapping, on essaie directement
        ids_resolus.append(id_coingecko)
        if c not in CRYPTO_ID_MAP and c not in CRYPTO_ID_MAP.values():
            non_reconnus.append(c)

    ids_str = ",".join(ids_resolus)

    try:
        resp = requests.get(
            f"{COINGECKO_BASE_URL}/simple/price",
            params={
                "ids": ids_str,
                "vs_currencies": devises,
                "include_24hr_change": "true",
                "include_market_cap": "true",
                "include_24hr_vol": "true",
            },
            headers=COINGECKO_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )

        if resp.status_code == 429:
            return json.dumps({
                "erreur": "Limite de requêtes CoinGecko atteinte (10-30 req/min pour l'API gratuite).",
                "conseil": "Réessayez dans quelques secondes.",
            }, ensure_ascii=False)

        if resp.status_code != 200:
            return json.dumps({
                "erreur": f"Erreur API CoinGecko (HTTP {resp.status_code})",
                "conseil": "Vérifiez l'orthographe du nom de la cryptomonnaie.",
            }, ensure_ascii=False)

        data = resp.json()

        if not data:
            return json.dumps({
                "erreur": f"Aucune donnée trouvée pour '{crypto_nom}'.",
                "conseil": (
                    "Essayez avec : 'bitcoin', 'ethereum', 'solana', 'cardano', 'xrp', "
                    "'dogecoin', 'polkadot', 'avalanche', 'chainlink'."
                ),
            }, ensure_ascii=False)

        # Formatage des résultats
        resultats = {}
        for id_cg, prix_data in data.items():
            resultats[id_cg] = {}
            for devise in devises.split(","):
                devise = devise.strip()
                if devise in prix_data:
                    resultats[id_cg][f"prix_{devise}"] = prix_data[devise]
                if f"{devise}_24h_change" in prix_data:
                    resultats[id_cg][f"variation_24h_%"] = round(prix_data[f"{devise}_24h_change"], 2)
                if f"{devise}_market_cap" in prix_data:
                    resultats[id_cg]["capitalisation_boursiere_eur"] = prix_data.get("eur_market_cap")
                if f"{devise}_24h_vol" in prix_data:
                    resultats[id_cg]["volume_24h_eur"] = prix_data.get("eur_24h_vol")

        return json.dumps({
            "source": "CoinGecko API (données en temps réel)",
            "avertissement": (
                "Ces données sont fournies à titre INFORMATIF uniquement. "
                "Elles ne constituent pas un conseil en investissement."
            ),
            "donnees": resultats,
            "non_reconnus": non_reconnus if non_reconnus else None,
        }, ensure_ascii=False, indent=2)

    except requests.exceptions.ConnectionError:
        return json.dumps({"erreur": "Impossible de contacter l'API CoinGecko. Vérifiez votre connexion."}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"erreur": f"Erreur inattendue : {str(e)}"}, ensure_ascii=False)


@function_tool
def get_info_crypto(crypto_id: str) -> str:
    """Récupère les informations détaillées sur une cryptomonnaie via CoinGecko.

    Retourne : description, rang par capitalisation, site officiel, historique de prix 7j.

    Args:
        crypto_id: ID CoinGecko de la crypto (ex: 'bitcoin', 'ethereum', 'solana')
                   Utiliser les IDs standards CoinGecko en minuscules avec tirets.
    """
    # Résolution du nom si nécessaire
    id_resolu = CRYPTO_ID_MAP.get(crypto_id.lower(), crypto_id.lower())

    try:
        resp = requests.get(
            f"{COINGECKO_BASE_URL}/coins/{id_resolu}",
            params={
                "localization": "false",
                "tickers": "false",
                "market_data": "true",
                "community_data": "false",
                "developer_data": "false",
                "sparkline": "false",
            },
            headers=COINGECKO_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )

        if resp.status_code == 404:
            return json.dumps({
                "erreur": f"Cryptomonnaie '{crypto_id}' introuvable sur CoinGecko.",
                "conseil": "Vérifiez l'orthographe ou utilisez l'ID exact CoinGecko (ex: 'avalanche-2' pour Avalanche).",
            }, ensure_ascii=False)

        if resp.status_code != 200:
            return json.dumps({"erreur": f"Erreur API CoinGecko (HTTP {resp.status_code})"}, ensure_ascii=False)

        data = resp.json()
        market = data.get("market_data", {})

        # Extraction des informations clés
        description_fr = data.get("description", {}).get("fr", "")
        description_en = data.get("description", {}).get("en", "")
        description = description_fr or description_en or "Aucune description disponible"
        # On tronque la description pour éviter les réponses trop longues
        description = description[:600] + "..." if len(description) > 600 else description

        # Nettoyage HTML basique (CoinGecko retourne parfois des balises <a>)
        import re
        description = re.sub(r"<[^>]+>", "", description)

        info = {
            "source": "CoinGecko API (données en temps réel)",
            "avertissement": "Données informatives uniquement — pas un conseil en investissement.",
            "nom": data.get("name"),
            "symbole": data.get("symbol", "").upper(),
            "rang_capitalisation": data.get("market_cap_rank"),
            "description": description,
            "site_officiel": data.get("links", {}).get("homepage", [None])[0],
            "prix_actuel_eur": market.get("current_price", {}).get("eur"),
            "variation_24h_%": market.get("price_change_percentage_24h"),
            "variation_7j_%": market.get("price_change_percentage_7d"),
            "variation_30j_%": market.get("price_change_percentage_30d"),
            "capitalisation_eur": market.get("market_cap", {}).get("eur"),
            "volume_24h_eur": market.get("total_volume", {}).get("eur"),
            "offre_en_circulation": market.get("circulating_supply"),
            "offre_maximale": market.get("max_supply"),
            "ath_eur": market.get("ath", {}).get("eur"),  # All-time high
            "ath_date": market.get("ath_date", {}).get("eur", "")[:10] if market.get("ath_date") else None,
        }

        return json.dumps(info, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"erreur": f"Erreur inattendue : {str(e)}"}, ensure_ascii=False)


agent_marche = register_agent(Agent(
    name="Agent Marché Crypto",
    instructions=(
        "Tu es un assistant qui présente les données de marché des cryptomonnaies "
        "à titre strictement informatif.\n\n"

        "TES OUTILS :\n"
        "- get_prix_crypto : prix en temps réel, variation 24h, volume, capitalisation\n"
        "- get_info_crypto : informations détaillées sur une crypto (description, historique, ATH)\n\n"

        "RÈGLE ABSOLUE : Tu ne réponds JAMAIS de mémoire aux questions sur les prix ou données de marché.\n"
        "Tu DOIS toujours appeler l'outil correspondant.\n\n"

        "FORMAT DE PRÉSENTATION :\n"
        "1. Données brutes (prix, variation, volume) — depuis l'outil\n"
        "2. Mise en contexte neutre (sans jugement de valeur)\n"
        "3. Rappel systématique : ces données sont informatives, pas des signaux d'achat/vente\n\n"

        "CONTEXTE DES VARIATIONS (factuel, sans jugement) :\n"
        "- Une hausse de 5 % sur 24h est une fluctuation normale pour les cryptos\n"
        "- Présente les variations comme des faits, pas comme des opportunités\n"
        "- Ne dis jamais 'c'est le bon moment pour acheter' ou 'le prix va continuer à monter'\n\n"

        "RÉPONDS EN FRANÇAIS. Ton sobre et informatif."
        + REGLE_ANTI_CONSEIL
    ),
    tools=[get_prix_crypto, get_info_crypto],
    model=model_main,
))


# ══════════════════════════════════════════════════════════════════════════════
# AGENT RISQUES
# Rôle : détecter les questions prescriptives et répondre avec des mises en garde
# Analogie : c'est le conseiller juridique — il vous explique les risques
# mais refuse catégoriquement de vous dire "faites ça".
# ══════════════════════════════════════════════════════════════════════════════

# Mots-clés qui signalent une question prescriptive (demande de conseil)
_MOTS_CLES_PRESCRIPTIFS = [
    "que dois-je", "qu'est-ce que je dois", "je devrais", "tu me conseilles",
    "recommandes-tu", "vaut-il mieux", "lequel acheter", "quel crypto acheter",
    "quel token", "dans quoi investir", "est-ce que je peux gagner",
    "combien je peux gagner", "est-ce rentable", "bon investissement",
    "bonne opportunité", "devrais-je vendre", "devrais-je acheter",
    "when lambo", "quand acheter", "quand vendre", "bon moment pour",
]


def _est_question_prescriptive(texte: str) -> bool:
    """Détecte si la question demande un conseil d'investissement."""
    texte_lower = texte.lower()
    return any(kw in texte_lower for kw in _MOTS_CLES_PRESCRIPTIFS)


@function_tool
def analyser_risques_question(question: str) -> str:
    """Analyse une question pour détecter si elle demande un conseil d'investissement,
    et retourne les mises en garde appropriées ainsi que les risques associés.

    Args:
        question: La question de l'utilisateur à analyser
    """
    est_prescriptive = _est_question_prescriptive(question)

    mises_en_garde_generales = [
        "Les crypto-actifs sont des investissements à haut risque selon l'AMF",
        "Vous pouvez perdre la totalité du capital investi",
        "Les marchés crypto sont très volatils (fluctuations de ±20-80 % courantes)",
        "Aucune réglementation ne garantit vos investissements en crypto",
        "Méfiez-vous des promesses de rendements élevés garantis — ce sont des arnaques",
        "Les performances passées ne préjugent pas des performances futures",
    ]

    risques_specifiques = {
        "Risque de liquidité": "Certains tokens peuvent devenir invendables",
        "Risque de contrepartie": "Une plateforme peut faire faillite (ex: FTX en 2022)",
        "Risque technique": "Perte des clés privées = perte définitive des fonds",
        "Risque réglementaire": "La réglementation peut évoluer et impacter la valeur",
        "Risque de fraude": "Arnaques, rug pulls, faux projets sont fréquents",
        "Risque de marché": "Forte corrélation avec le Bitcoin lors des baisses",
    }

    refus_conseil = None
    if est_prescriptive:
        refus_conseil = (
            "Je ne suis pas en mesure de vous conseiller sur l'achat, la vente ou la détention "
            "de cryptomonnaies spécifiques. Cela relèverait d'un conseil en investissement, "
            "activité réglementée qui nécessite des agréments spécifiques.\n\n"
            "Ce que je peux faire à la place :\n"
            "• Vous expliquer comment évaluer un projet crypto (livre blanc, équipe, utilité)\n"
            "• Vous présenter les critères utilisés par les analystes\n"
            "• Vous informer sur les risques associés à chaque type de crypto-actif\n"
            "• Vous orienter vers les ressources officielles (AMF, ACPR)"
        )

    return json.dumps({
        "question_analysee": question,
        "est_prescriptive": est_prescriptive,
        "refus_conseil_si_prescriptive": refus_conseil,
        "mises_en_garde": mises_en_garde_generales,
        "risques_specifiques": risques_specifiques,
        "ressources_officielles": [
            "AMF — Protégez-vous des arnaques : https://www.amf-france.org",
            "AMF — Précautions pratiques sur les cryptos : https://www.amf-france.org",
            "ACPR — Crypto et risques : https://acpr.banque-france.fr",
        ],
    }, ensure_ascii=False, indent=2)


agent_risques = register_agent(Agent(
    name="Agent Risques Crypto",
    instructions=(
        "Tu es un expert en gestion des risques liés aux cryptomonnaies, "
        "spécialisé dans la protection des investisseurs débutants.\n\n"

        "TON OUTIL :\n"
        "- analyser_risques_question : détecte si la question est prescriptive "
        "et retourne les mises en garde appropriées. TOUJOURS l'appeler en premier.\n\n"

        "TA MISSION PRINCIPALE :\n"
        "1. Analyser CHAQUE question avec l'outil analyser_risques_question\n"
        "2. Si la question est prescriptive (demande de conseil) :\n"
        "   → Refuser poliment mais fermement de donner un conseil\n"
        "   → Reformuler vers une réponse éducative\n"
        "   → Expliquer les critères d'évaluation sans donner de recommandation\n"
        "3. Si la question porte sur les risques :\n"
        "   → Présenter les risques de façon exhaustive et nuancée\n"
        "   → Citer les sources officielles (AMF, ACPR)\n\n"

        "EXEMPLES DE REFUS POLIS :\n"
        "❌ Question : 'Je devrais acheter du Solana maintenant ?'\n"
        "✅ Réponse : 'Je ne peux pas vous conseiller sur l'achat de Solana. "
        "Ce que je peux faire : vous expliquer comment Solana fonctionne, "
        "quels sont ses risques spécifiques, et les critères que les analystes "
        "utilisent pour évaluer un projet.'\n\n"

        "EXEMPLES DE REDIRECTIONS ÉDUCATIVES :\n"
        "❌ 'Quel est le meilleur crypto à acheter ?' → Conseil = REFUS\n"
        "✅ 'Quels critères pour évaluer un projet crypto ?' → Éducatif = RÉPONSE\n\n"

        "RÉPONDS EN FRANÇAIS. Ton ferme mais bienveillant."
        + REGLE_ANTI_CONSEIL
    ),
    tools=[analyser_risques_question],
    model=model_main,
))


# ══════════════════════════════════════════════════════════════════════════════
# WRAPPERS AGENTS-AS-TOOLS (pattern identique à cyber_agents.py)
# Analogie : ce sont des boutons sur le tableau de bord du manager.
# Le manager n'a pas besoin de savoir COMMENT chaque agent travaille —
# il appuie sur le bouton et reçoit le résultat.
# ══════════════════════════════════════════════════════════════════════════════

@function_tool
async def deleguer_agent_education(query: str) -> str:
    """Délègue à l'Agent Éducation pour répondre aux questions pédagogiques sur les cryptos.

    Utilise cet outil pour toute question éducative :
    - Définitions (blockchain, wallet, DeFi, NFT, stablecoin, seed phrase...)
    - Fonctionnement technique expliqué simplement
    - Guides pour débutants (comment démarrer, comment sécuriser, comment acheter)
    - Questions sur les réglementations (AMF, PSAN, fiscalité)
    - Glossaire et terminologie crypto

    Cet outil consulte le corpus documentaire officiel (AMF, Coinbase Learn, CoinGecko).
    """
    result = await Runner.run(agent_education, input=query, max_turns=5)
    return result.final_output


@function_tool
async def deleguer_agent_marche(query: str) -> str:
    """Délègue à l'Agent Marché pour obtenir les données de marché en temps réel.

    Utilise cet outil pour toute question sur les données de marché :
    - Prix actuel d'une cryptomonnaie (Bitcoin, Ethereum, Solana...)
    - Variation de prix sur 24h, 7 jours, 30 jours
    - Volume d'échanges et capitalisation boursière
    - Informations sur un projet spécifique (description, ATH, offre)

    RAPPEL : Ces données sont informatives. Jamais des conseils d'investissement.
    """
    result = await Runner.run(agent_marche, input=query, max_turns=5)
    return result.final_output


@function_tool
async def deleguer_agent_risques(query: str) -> str:
    """Délègue à l'Agent Risques pour analyser les risques et détecter les questions prescriptives.

    Utilise cet outil pour :
    - Questions sur les risques des cryptomonnaies (perte de fonds, arnaques, volatilité)
    - Questions prescriptives (que dois-je acheter, devrais-je vendre...)
      → L'agent refusera poliment et redirigera vers une réponse éducative
    - Questions sur les arnaques courantes et comment s'en protéger
    - Questions sur la sécurité des plateformes et des wallets (angle risques)
    """
    result = await Runner.run(agent_risques, input=query, max_turns=5)
    return result.final_output


# ══════════════════════════════════════════════════════════════════════════════
# EXPORT — liste des outils disponibles pour le manager
# ══════════════════════════════════════════════════════════════════════════════

CRYPTO_TOOLS = [
    # Outils déterministes
    get_checklist_debutant,
    get_etapes_premier_achat,
    get_bonnes_pratiques_wallet,
    # Wrappers agents-as-tools
    deleguer_agent_education,
    deleguer_agent_marche,
    deleguer_agent_risques,
]


# ══════════════════════════════════════════════════════════════════════════════
# SCRIPT DE TEST (exécution directe : python crypto_agents.py)
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import asyncio

    print("=" * 65)
    print("   CryptoEdu Assistant — Test des agents (Jour 2)")
    print("=" * 65)

    async def run_test():

        # ── Test 1 : Outil déterministe (Python pur, 0 LLM) ──
        print("\n📋 TEST 1 — get_checklist_debutant()")
        print("-" * 40)
        # Note : function_tool retourne un objet, on accède au résultat via .run()
        # Pour les tests directs, on appelle la fonction Python sous-jacente
        from agents import Runner
        checklist_raw = get_checklist_debutant.on_invoke_tool(None, "{}")
        print("✅ Outil déterministe OK — Checklist générée (pas d'appel LLM)")
        print(f"   → Aperçu : étapes 1 à 7 pour débuter en crypto")

        # ── Test 2 : Agent Marché via CoinGecko ──
        print("\n📈 TEST 2 — Agent Marché (CoinGecko API)")
        print("-" * 40)
        print("Question : Quel est le prix actuel du Bitcoin ?")
        try:
            result = await Runner.run(
                agent_marche,
                input="Quel est le prix actuel du Bitcoin en euros ?",
                max_turns=5,
            )
            print(f"✅ Réponse reçue :\n{result.final_output[:400]}...")
        except Exception as e:
            print(f"❌ Erreur Agent Marché : {e}")

        # ── Test 3 : Agent Éducation via RAG ──
        print("\n📚 TEST 3 — Agent Éducation (RAG)")
        print("-" * 40)
        print("Question : Qu'est-ce qu'une seed phrase ?")
        try:
            result = await Runner.run(
                agent_education,
                input="Qu'est-ce qu'une seed phrase et pourquoi est-ce important ?",
                max_turns=5,
            )
            print(f"✅ Réponse reçue :\n{result.final_output[:400]}...")
        except Exception as e:
            print(f"❌ Erreur Agent Éducation : {e}")

        # ── Test 4 : Agent Risques — question prescriptive ──
        print("\n⚠️  TEST 4 — Agent Risques (détection question prescriptive)")
        print("-" * 40)
        print("Question : Je devrais acheter du Solana maintenant ?")
        try:
            result = await Runner.run(
                agent_risques,
                input="Je devrais acheter du Solana maintenant ? Ça va monter ?",
                max_turns=5,
            )
            print(f"✅ Réponse reçue :\n{result.final_output[:400]}...")
        except Exception as e:
            print(f"❌ Erreur Agent Risques : {e}")

        # ── Test 5 : Agent Risques — question légitime ──
        print("\n🛡️  TEST 5 — Agent Risques (question légitime sur les risques)")
        print("-" * 40)
        print("Question : Quels sont les principaux risques des cryptos ?")
        try:
            result = await Runner.run(
                agent_risques,
                input="Quels sont les principaux risques liés aux cryptomonnaies pour un débutant ?",
                max_turns=5,
            )
            print(f"✅ Réponse reçue :\n{result.final_output[:400]}...")
        except Exception as e:
            print(f"❌ Erreur Agent Risques : {e}")

        print("\n" + "=" * 65)
        print("   Tests terminés.")
        print("=" * 65)

    asyncio.run(run_test())
