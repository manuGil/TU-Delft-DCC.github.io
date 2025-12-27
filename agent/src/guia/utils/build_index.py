"""One type set up"""

from pathlib import Path
from guia.parser_quarto import QuartoParser
from guia.indexer import QuartoIndexer

# Use project root for chroma_db
SCRIPT_DIR = Path(__file__).parent.resolve()
DEFAULT_CHROMA_PATH = str(SCRIPT_DIR.parent / "chroma_db")

def build_index(docs_path: str, persist_directory: str = DEFAULT_CHROMA_PATH):
    """Build the ChromaDB index from Markdown documentation"""

    # Parse all documentation files
    print("Parsing Markdown doumentation....")
    parser = QuartoParser(docs_path)
    chunks = parser.parse_all_files()

    print(f"\nFound {len(chunks)} documentation chunks")

    # Create index
    print("\nBuilding ChromaDB index...")
    indexer = QuartoIndexer(persist_directory)
    indexer.index_documents(chunks)

    # print statistics
    stats = indexer.get_stats()
    print("\nIndex built successfully")
    print(f"    Total chunks: {stats['total_chunks']}")
    print(f"    Stored in: {persist_directory}")

    return indexer


if __name__ == '__main__':
    DOCS_PATH = '/Users/mgarciaalvarez/devel/dcc-guides/docs'

    # indexer = build_index(DOCS_PATH)
    indexer = QuartoIndexer(DEFAULT_CHROMA_PATH)

    # test search
    print("\n--- Testing Search ---")
    results = indexer.search("How do I renew SSL certificates?", n_results=3)

    print("results ids\n", results['ids'])

    for i, (doc, metadata) in enumerate(zip(results['documents'][0],
                                            results['metadatas'][0])):
        print(f"\nResult {i+1}:")
        print(f"File: {metadata['file']}")
        print(f"Section: {metadata['section_header']}")
        print(f"Content preview: {doc[:200]}...")
