import os
from dotenv import dotenv_values
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec
from langchain_core.documents import Document

class TextVectorStore:
    def __init__(self):
        # Explicitly read the .env file from the same directory as the script
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        config = dotenv_values(env_path)
        
        # Get API keys directly from the config
        openai_api_key = config.get("OPENAI_API_KEY")
        pinecone_api_key = config.get("PINECONE_API_KEY")
        
        # Verify keys are loaded
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in .env file")
        if not pinecone_api_key:
            raise ValueError("PINECONE_API_KEY not found in .env file")
        
        # Initialize OpenAI embeddings
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=openai_api_key
        )
        
        # Initialize Pinecone
        self.pc = Pinecone(api_key=pinecone_api_key)
        self.index_name = "medsync"
        
        # Create index if it doesn't exist
        if self.index_name not in self.pc.list_indexes().names():
            self.pc.create_index(
                name=self.index_name,
                dimension=1536,  # OpenAI embedding dimension
                metric='cosine',
                spec=ServerlessSpec(
                    cloud='aws',
                    region='us-east-1'
                )
            )
        
        # Initialize vector store
        self.vector_store = PineconeVectorStore(
            self.pc.Index(self.index_name),
            self.embeddings,
            "text"
        )
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )

    def process_text(self, text, metadata=None):
        """Process a text string and store its vectors
        
        Args:
            text (str): The text content to process
            metadata (dict): Optional metadata dictionary that can include:
                - title: Title of the article
                - link: URL or link to the article
                - source: Source of the content
                - Any other relevant metadata
        """
        try:
            # Ensure metadata is a dictionary
            metadata = metadata or {}
            
            # Create a Document object with enhanced metadata
            doc = Document(
                page_content=text,
                metadata={
                    "title": metadata.get("title", "Untitled"),
                    "link": metadata.get("link", ""),
                    "source": metadata.get("source", ""),
                    "timestamp": metadata.get("timestamp", ""),
                    **metadata  # Include any additional metadata fields
                }
            )
            
            # Split into chunks
            chunks = self.text_splitter.split_documents([doc])
            
            # Add document chunks to vector store
            self.vector_store.add_documents(chunks)
            
            print(f"Successfully processed text chunk with title: {metadata.get('title', 'Untitled')}")
            return True
            
        except Exception as e:
            print(f"Error processing text: {str(e)}")
            return False

    def query(self, query_text, k=3):
        """Search the vector store"""
        return self.vector_store.similarity_search(query_text, k=k)

def main():
    # Initialize the Text Vector Store
    text_store = TextVectorStore()
    
    # Example usage with enhanced metadata
    sample_text = """
    Machine learning is a subset of artificial intelligence that focuses on developing 
    systems that can learn from and make decisions based on data. It enables computers 
    to improve their performance on a specific task through experience.
    """
    
    # Process text with enhanced metadata
    text_store.process_text(
        text=sample_text,
        metadata={
            "title": "Introduction to Machine Learning",
            "link": "https://example.com/intro-to-ml",
            "source": "AI Learning Platform",
            "timestamp": "2024-02-20",
            "author": "John Doe",
            "category": "AI/ML"
        }
    )
    
    # Example query
    results = text_store.query("What is machine learning?")
    for doc in results:
        print("\nResult:", doc.page_content)
        print("Title:", doc.metadata.get("title"))
        print("Link:", doc.metadata.get("link"))
        print("Source:", doc.metadata.get("source"))
        print("Author:", doc.metadata.get("author"))

if __name__ == "__main__":
    main()
