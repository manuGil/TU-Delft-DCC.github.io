"""
Indexer for DCC guides parsed from Markdown files.
"""

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict

class QuartoIndexer:
    def __init__(self, persist_directory: str = './chroma_db'):
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings = Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        ) 

        # Initialize embeding model
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name= "guides_docs",
            metadata={"description": "Markdown documentation chunks"}
        )
    
    def create_embedding_text(self, chunk: Dict) -> str:
        """Create text for embedding that includes context"""
        parts = []

        if chunk.get('title'):
            parts.append(f"Document: {chunk['title']}")

        if chunk.get('section_header'):
            parts.append(f"Section: {chunk['section_header']}")

        parts.append(chunk['content'])

        return '\n'.join(parts)
    
    def index_documents(self, chunks: List[Dict], batch_size: int =100):
        """Index document chunks into ChromaDB"""

        print(f"Indenxing {len(chunks)} chunks....")

        # Process in batches
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]

            # Prepare data for ChromaDB
            ids = [chunk['chunk_id'] for chunk in batch]
            documents = [chunk['content'] for chunk in batch]

            # Create embedding text (includes context)
            embedding_text = [self.create_embedding_text(chunk) for chunk in batch]
            embeddings = self.embedder.encode(embedding_text).tolist()

            # Prepare metadata (ChromaDB requires flat dictionaries)
            _metadata=[]
            for chunk in batch:
                metadata = {
                    'chunk_id': chunk['chunk_id'],  # Include chunk_id for evaluation matching
                    'file': chunk['title'],
                    'title': chunk['title'],
                    'section_header': chunk['section_header'],
                    'section_level': chunk['section_level']
                }

                # Add addional metadata from frontmatter
                if chunk.get('metatdata'):
                    for key, value in chunk['metadata'].items():
                        if isinstance(value, (str, int, float, bool)):
                            metadata[f'meta_{key}'] = value
                
                _metadata.append(metadata)

            # add to collection
            self.collection.add(
                ids=ids, 
                embeddings=embeddings,
                documents=documents,
                metadatas=_metadata

            )

            print(f"Indexed batch {i//batch_size + 1}/{(len(chunks)-1)//batch_size + 1}")

        print(f"Successfully indexed {len(chunks)} chunks")
    
    def search(self, query: str, n_results: int = 5,
               filter_metadata: Dict = None) -> Dict:
        """Search the documentation"""

        #generate query embedding
        query_embedding = self.embedder.encode(query).tolist()

        # Search with optional metadata filtering
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_metadata # e.g. {"file": "installation.md"}
        )

        return results
    
    def get_stats(self):
        """Get collection statistics"""
        count= self.collection.count()
        return {
            'total_chunks': count, 
            'collection_name': self.collection.name
        }