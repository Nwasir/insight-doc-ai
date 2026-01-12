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

# Load API Keys
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

class RAGEngine:
    def __init__(self):
        # 1. Initialize Gemini (Production Mode)
        # Using Gemini 2.0 Flash for high speed and massive context window.
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
        # Step 1: Retrieval
        # We retrieve 100 chunks to ensure we capture the actual content 
        # even if the PDF has a long Table of Contents or Index.
        try:
            retriever = self.vector_db.as_retriever(search_kwargs={"k": 100})
            context_docs = retriever.invoke(query)
        except Exception as e:
            yield f"⚠️ Retrieval Error: {str(e)}"
            return
        
        # Step 2: Prepare Context
        context_text = "\n\n".join(
            [f"[Page {d.metadata.get('page', '?')}] {d.page_content}" for d in context_docs]
        )

        # Step 3: The Prompt
        template = """
        You are an expert technical assistant. Use the context below to answer the user's question.
        
        RULES:
        1. ALWAYS cite the page number like [Page X] at the end of the sentence.
        2. If the context does not contain the answer, say "Data Not Found."

        CONTEXT:
        {context}

        QUESTION: 
        {question}

        ANSWER:
        """
        prompt = PromptTemplate.from_template(template)
        
        # Step 4: Streaming Generation
        chain = prompt | self.llm | StrOutputParser()
        
        try:
            for chunk in chain.stream({"context": context_text, "question": query}):
                yield chunk
        except Exception as e:
            yield f"⚠️ Generator Error: {str(e)}"