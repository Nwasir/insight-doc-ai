import os
from typing import List, Generator
from dotenv import load_dotenv

# AI & Vector DB
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings 
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Observability (The "Eyes")
from langfuse.langchain import CallbackHandler

# Reranking
from sentence_transformers import CrossEncoder

# Load API Keys
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Langfuse Credentials (ensure these are in your .env)
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

class RAGEngine:
    def __init__(self):
        # 1. Initialize Gemini
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash", 
            temperature=0,
            google_api_key=GOOGLE_API_KEY
        )
        
        # 2. Initialize Local Embeddings (CPU)
        print("📥 Loading Local Embedding Model (all-MiniLM-L6-v2)...")
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

        # 3. Initialize Vector DB (Chroma)
        self.vector_db = Chroma(
            persist_directory="./data/chroma_db",
            embedding_function=self.embeddings
        )

        # 4. Initialize Reranker (Cross-Encoder)
        print("🚀 Initializing Cross-Encoder (Reranker)...")
        self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

        # 5. Initialize Langfuse Handler (The "Eyes")
        # We only init if keys are present to prevent crashes
        self.enable_observability = bool(LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY)
        if self.enable_observability:
            print("👀 Langfuse Observability Enabled.")
        else:
            print("⚠️ Langfuse keys not found. Observability disabled.")

    def ingest_document(self, docs: List[Document]):
        """
        Takes processed documents and saves them to ChromaDB.
        """
        batch_size = 10 
        total_docs = len(docs)
        
        print(f"🧠 Starting Local Ingestion for {total_docs} pages...")

        for i in range(0, total_docs, batch_size):
            batch = docs[i : i + batch_size]
            print(f"   - Embedding batch {i//batch_size + 1} (Local CPU)...")
            self.vector_db.add_documents(batch)
                
        print("✅ Ingestion Complete.")

    def stream_answer(self, query: str) -> Generator[str, None, None]:
        # --- PHASE 1: BROAD RETRIEVAL ---
        try:
            retriever = self.vector_db.as_retriever(search_kwargs={"k": 25})
            broad_docs = retriever.invoke(query)
        except Exception as e:
            yield f"⚠️ Retrieval Error: {str(e)}"
            return
        
        # --- PHASE 2: RERANKING ---
        try:
            pairs = [[query, doc.page_content] for doc in broad_docs]
            scores = self.reranker.predict(pairs)
            
            ranked_docs = []
            for i, doc in enumerate(broad_docs):
                ranked_docs.append({"doc": doc, "score": scores[i]})
            
            ranked_docs.sort(key=lambda x: x["score"], reverse=True)
            top_results = [item["doc"] for item in ranked_docs[:5]]
            
        except Exception as e:
            print(f"⚠️ Reranking Warning: {e}")
            top_results = broad_docs[:5]

        # Prepare Context
        context_text = "\n\n".join(
            [f"[Page {d.metadata.get('page', '?')}] {d.page_content}" for d in top_results]
        )

        # --- PHASE 3: GENERATION (Gemini) ---
        template = """
        You are InsightDoc, an expert technical assistant. Use the context below to answer.
        
        RULES:
        1. ALWAYS cite the page number like [Page X] at the end of the sentence.
        2. If the context contains a visual description (e.g., "[Visual Diagram...]"), use that information to describe diagrams or charts. 

[Image of Technical Diagram]

        3. If the context does not contain the answer, say "Data Not Found."

        CONTEXT:
        {context}

        QUESTION: 
        {question}

        ANSWER:
        """
        prompt = PromptTemplate.from_template(template)
        
        chain = prompt | self.llm | StrOutputParser()
        
        # Configure Callbacks (Langfuse)
        run_config = {}
        if self.enable_observability:
            langfuse_handler = CallbackHandler()            
            
            run_config["callbacks"] = [langfuse_handler]
        
        try:
            # We pass 'run_config' to enable tracing
            for chunk in chain.stream({"context": context_text, "question": query}, config=run_config):
                yield chunk
        except Exception as e:
            yield f"⚠️ Generator Error: {str(e)}"