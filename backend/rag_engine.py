import os
from typing import List, Generator
from dotenv import load_dotenv

# AI & Vector DB
# Updated to new LangChain imports
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# Reranking (FlashRank is local and works fine)
from flashrank import Ranker, RerankRequest

# Load API Keys
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

class RAGEngine:
    def __init__(self):
        # 1. Initialize Gemini (Text + Vision)
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0,
            google_api_key=GOOGLE_API_KEY
        )
        
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=GOOGLE_API_KEY
        )

        # 2. Initialize Vector DB (Chroma)
        self.vector_db = Chroma(
            persist_directory="./data/chroma_db",
            embedding_function=self.embeddings
        )
        
        # 3. Initialize Reranker (FlashRank)
        self.reranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir="./data/flashrank")

        # LANGFUSE DISABLED FOR PHASE 3
        # We will re-enable this in Phase 5
        self.langfuse_handler = None 

    def ingest_document(self, docs: List[Document]):
        """
        Takes processed documents (text+image captions) and saves them to ChromaDB.
        """
        print(f"🧠 Embedding {len(docs)} pages into Vector Store...")
        self.vector_db.add_documents(docs)
        print("✅ Ingestion Complete.")

    def _rerank_results(self, query: str, initial_docs: List[Document], top_n: int = 3) -> List[Document]:
        """
        The Quality Filter.
        Takes top 10 'fuzzy' matches and uses FlashRank to pick the best 3.
        """
        passages = [
            {"id": str(i), "text": doc.page_content, "meta": doc.metadata} 
            for i, doc in enumerate(initial_docs)
        ]
        
        rerank_request = RerankRequest(query=query, passages=passages)
        results = self.reranker.rerank(rerank_request)
        
        sorted_results = sorted(results, key=lambda x: x['score'], reverse=True)[:top_n]
        
        final_docs = []
        for res in sorted_results:
            doc = Document(page_content=res['text'], metadata=res['meta'])
            final_docs.append(doc)
            
        return final_docs

    def stream_answer(self, query: str) -> Generator[str, None, None]:
        """
        Generates the answer token-by-token.
        """
        # Step 1: Broad Retrieval
        retriever = self.vector_db.as_retriever(search_kwargs={"k": 10})
        initial_docs = retriever.invoke(query)
        
        # Step 2: Reranking
        context_docs = self._rerank_results(query, initial_docs, top_n=3)
        
        # Prepare Context
        context_text = "\n\n".join(
            [f"[Page {d.metadata.get('page', '?')}] {d.page_content}" for d in context_docs]
        )

        # Step 3: The Prompt
        template = """
        You are an expert technical assistant. Use the context below to answer the user's question.
        
        RULES:
        1. If the answer involves a diagram/image, mention it explicitly (e.g., "As seen in the diagram on Page 5...").
        2. ALWAYS cite the page number like [Page X] at the end of the sentence.
        3. If the context does not contain the answer, say "Data Not Found." Do not guess.

        CONTEXT:
        {context}

        QUESTION: 
        {question}

        ANSWER:
        """
        prompt = PromptTemplate.from_template(template)
        
        # Step 4: Streaming Generation
        chain = prompt | self.llm | StrOutputParser()
        
        # Callbacks removed for now
        for chunk in chain.stream(
            {"context": context_text, "question": query},
            config={} 
        ):
            yield chunk

# --- Quick Test ---
if __name__ == "__main__":
    engine = RAGEngine()
    print("✅ System Initialized. Reranker & VectorDB ready (Langfuse Skipped).")