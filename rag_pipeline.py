"""
Pipeline RAG du CryptoEdu Assistant.
Adapté depuis le RAG Cybersécurité (main.py backend).

Changements par rapport à l'original :
- Dossier PDF : ./docs_crypto/ (au lieu de ./docs_cybersec/)
- Prompt système : éducatif crypto (au lieu de cybersécurité)
- LLM : OpenRouter via LangChain OpenAI wrapper (au lieu de Gemini)
- Support des fichiers .txt en plus des .pdf
- Pas d'API FastAPI ici — le pipeline est importé par les agents
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from langchain_community.document_loaders import (
    DirectoryLoader,
    PyPDFLoader,
    TextLoader,
)
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# ── Configuration ────────────────────────────────────────────────────────────

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Le RAG utilise Groq en priorité (comme le reste de l'app), OpenRouter en fallback
if not GROQ_API_KEY and not OPENROUTER_API_KEY:
    logger.error("Aucune clé API (GROQ_API_KEY ou OPENROUTER_API_KEY) trouvée dans .env")
    sys.exit(1)

PDF_FOLDER    = "./docs_crypto/"
EMBED_MODEL   = "all-MiniLM-L6-v2"
CHUNK_SIZE    = 800
CHUNK_OVERLAP = 100
RETRIEVER_K   = 6
TOP_K         = 4

# ── Prompt système éducatif crypto ───────────────────────────────────────────

SYSTEM_PROMPT = """Tu es un assistant éducatif spécialisé dans les cryptomonnaies, conçu pour les débutants francophones.

RÈGLES STRICTES :
1. Réponds UNIQUEMENT à partir des documents fournis dans le contexte.
2. Ne complète JAMAIS avec tes connaissances générales sur les cryptomonnaies.
3. Si l'information n'est pas dans le contexte, réponds :
   "Je ne trouve pas cette information dans la documentation disponible.
    Je te recommande de consulter les guides de l'AMF ou de Coinbase Learn pour approfondir."
4. Cite la source de chaque information entre crochets [1], [2], etc.
5. Utilise un ton pédagogique et accessible — explique les termes techniques.
6. Structure tes réponses : définition simple, points clés, points de vigilance.
7. Tu es éducatif, JAMAIS prescriptif : ne donne AUCUN conseil d'investissement.
8. Si on te demande "que dois-je acheter" ou "quel token investir", refuse poliment
   et redirige vers une explication éducative."""


# ── État global du pipeline ──────────────────────────────────────────────────

class RAGState:
    vectorstore = None
    hybrid_retriever = None
    llm = None
    rag_prompt = None
    documents: list = []
    doc_count: int = 0
    ready: bool = False

state = RAGState()


# ── Construction du pipeline ─────────────────────────────────────────────────

def build_pipeline(doc_folder: str = PDF_FOLDER):
    """Charge les documents, crée les embeddings, configure le retriever hybride."""
    doc_path = Path(doc_folder)
    doc_path.mkdir(parents=True, exist_ok=True)

    # Charger les PDFs
    pdfs = list(doc_path.glob("**/*.pdf"))
    txts = list(doc_path.glob("**/*.txt"))

    if not pdfs and not txts:
        logger.warning("Aucun document trouvé — pipeline en attente.")
        state.ready = False
        state.doc_count = 0
        return

    all_docs = []

    # Charger les PDFs
    if pdfs:
        logger.info(f"Chargement de {len(pdfs)} PDF(s)…")
        pdf_loader = DirectoryLoader(
            doc_folder, glob="**/*.pdf", loader_cls=PyPDFLoader
        )
        all_docs.extend(pdf_loader.load())

    # Charger les fichiers texte
    if txts:
        logger.info(f"Chargement de {len(txts)} fichier(s) texte…")
        for txt_path in txts:
            try:
                txt_loader = TextLoader(str(txt_path), encoding="utf-8")
                all_docs.extend(txt_loader.load())
            except Exception as e:
                logger.warning(f"Erreur chargement {txt_path.name}: {e}")

    logger.info(f"Total : {len(all_docs)} documents chargés")

    # Découpage en chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n##", "\n", " ", ""],
        keep_separator=True,
    )
    documents = splitter.split_documents(all_docs)
    for i, doc in enumerate(documents):
        doc.metadata["chunk_id"] = i

    logger.info(f"Découpage : {len(documents)} chunks créés")

    # Embeddings
    embedding_model = HuggingFaceEmbeddings(model_name=EMBED_MODEL)

    if state.vectorstore:
        try:
            state.vectorstore.delete_collection()
        except Exception:
            pass

    # Base vectorielle ChromaDB
    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embedding_model,
        collection_name="rag_cryptoedu",
        collection_metadata={"hnsw:space": "cosine"},
    )

    # Retriever hybride (BM25 + sémantique, 50/50)
    semantic_retriever = vectorstore.as_retriever(
        search_kwargs={"k": RETRIEVER_K}
    )
    bm25_retriever = BM25Retriever.from_documents(documents, k=RETRIEVER_K)
    hybrid_retriever = EnsembleRetriever(
        retrievers=[semantic_retriever, bm25_retriever],
        weights=[0.5, 0.5],
    )

    # LLM via Groq (prioritaire) ou OpenRouter (fallback)
    # Groq offre un meilleur débit et un tool-calling plus fiable.
    # OpenRouter/free consommait le quota sur des modèles aléatoires
    # et provoquait des 429 en cascade — ne plus l'utiliser ici.
    if GROQ_API_KEY:
        llm = ChatOpenAI(
            model="moonshotai/kimi-k2-instruct",
            openai_api_key=GROQ_API_KEY,
            openai_api_base="https://api.groq.com/openai/v1",
            temperature=0.2,
            max_tokens=800,
        )
        logger.info("LLM RAG : Groq (kimi-k2-instruct)")
    else:
        llm = ChatOpenAI(
            model="meta-llama/llama-3.3-70b-instruct:free",
            openai_api_key=OPENROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.2,
            max_tokens=800,
            default_headers={
                "HTTP-Referer": "https://cryptoedu-assistant.streamlit.app",
                "X-Title": "CryptoEdu Assistant",
            },
        )
        logger.info("LLM RAG : OpenRouter (llama-3.3-70b — fallback, pas de clé Groq)")

    # Prompt RAG
    rag_prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human",
         "Contexte :\n---\n{context}\n---\n\n"
         "Question : {question}\n\n"
         "Réponse (en français, ton pédagogique) :"),
    ])

    # Mise à jour de l'état global
    state.vectorstore = vectorstore
    state.hybrid_retriever = hybrid_retriever
    state.llm = llm
    state.rag_prompt = rag_prompt
    state.documents = documents
    state.doc_count = len(pdfs) + len(txts)
    state.ready = True
    logger.info(
        f"Pipeline RAG prêt — {state.doc_count} document(s), "
        f"{len(documents)} chunks."
    )


# ── Fonction de requête ──────────────────────────────────────────────────────

def query_rag(question: str, top_k: int = TOP_K) -> dict:
    """
    Interroge le RAG et retourne la réponse + les sources.

    Returns:
        dict avec clés : response, sources, duration_ms
    """
    if not state.ready:
        return {
            "response": "Le pipeline RAG n'est pas encore initialisé. "
                        "Vérifiez que le dossier docs_crypto/ contient des documents.",
            "sources": [],
            "duration_ms": 0,
        }

    start = time.time()

    # Récupération des documents pertinents
    retrieved_docs = state.hybrid_retriever.invoke(question)[:top_k]

    # Formatage du contexte
    context = "\n\n".join(
        f"[{i+1}] {doc.page_content}"
        for i, doc in enumerate(retrieved_docs)
    )

    # Génération de la réponse
    prompt_value = state.rag_prompt.invoke({
        "context": context,
        "question": question,
    })
    response_text = state.llm.invoke(prompt_value).content

    duration_ms = int((time.time() - start) * 1000)

    # Extraction des sources
    sources = []
    for doc in retrieved_docs:
        source_name = Path(doc.metadata.get("source", "Inconnu")).name
        sources.append({
            "content": doc.page_content[:200] + "…",
            "source": source_name,
            "page": doc.metadata.get("page"),
            "chunk_id": doc.metadata.get("chunk_id"),
        })

    return {
        "response": response_text,
        "sources": sources,
        "duration_ms": duration_ms,
    }


# ── Initialisation au chargement du module ───────────────────────────────────

def init():
    """Initialise le pipeline RAG. Appelé une seule fois au démarrage."""
    if not state.ready:
        build_pipeline()


# Pour test direct
if __name__ == "__main__":
    print("Initialisation du pipeline RAG…")
    init()

    if state.ready:
        print(f"\n✅ Pipeline prêt : {state.doc_count} documents, "
              f"{len(state.documents)} chunks\n")

        # Questions de test
        test_questions = [
            "Qu'est-ce qu'un wallet ?",
            "C'est quoi une seed phrase ?",
            "Quels sont les risques des crypto-actifs ?",
        ]

        for q in test_questions:
            print(f"─── Question : {q}")
            result = query_rag(q)
            print(f"Réponse ({result['duration_ms']}ms) :")
            print(result["response"][:500])
            print(f"Sources : {[s['source'] for s in result['sources']]}")
            print()
    else:
        print("❌ Pipeline non prêt — vérifiez le dossier docs_crypto/")
