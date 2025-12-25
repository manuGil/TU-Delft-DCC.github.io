"""
MCP server for an AI agent that helps users to find information 
on the DCC guides.
"""

import asyncio
import os
import signal
import sys
from fastmcp import FastMCP
from indexer import QuartoIndexer
import json

# initialize indexer
indexer = QuartoIndexer(persist_directory="/Users/mgarciaalvarez/devel/dcc-guides/chroma_db")

mcp = FastMCP("agent", "An AI agent that helps users to find information on the DCC guides.")


@mcp.tool()
def search_documentation(query:str, n_results: int = 5):
    """
    Search the DCC guides documentation for relevant information

    Params
    -------
        query: the search query
        n_resutls: number of results to return (default: 5)

    Returns
    -------
        JSON string with the search results including file, title, section, content and relevance score 
    """

    results = indexer.search(query, n_results=n_results)

    # format results for Claude
    formatted_results =[]
    for doc, metadata, distance in zip(
        results['documents'][0],
        results['metadatas'][0],
        results['distances'][0]
    ):
        formatted_results.append({
            "file": metadata['file'],
            "title": metadata['title'],
            'section': metadata['section_header'],
            'contnet': doc,
            'relevance_score': round(1- distance, 3)
        })
    
    return json.dumps(formatted_results, indent=2)

@mcp.tool()
def get_documentation_stats() -> str:
    """
    Get statistics about the indexed documentation
    
    Returns
    -------
        JSON string with collection statistics
    """

    stats = indexer.get_stats()
    return json.dumps(stats, indent=2)

@mcp.tool
def search_by_file(filename: str, query: str = '', n_results: int =3) -> str:
    """
    Search within a specific documentation file

    Params
    ------
        filename: the filename to search within (e.g. "installation.md")
        query: optional search query within that file
        n_results: number of results to return

    Returns
    -------
        JSON string with the search results from the specified file
    """

    filter_metadata = {"file": filename}

    if query:
        results = indexer.search(query, n_results=n_results, filter_metadata=filter_metadata)
    else:
        # if no query, just retur sections from that file
        results = indexer.collection.get(
            where=filter_metadata,
            limit=n_results
        )

    formatted_results = []
    docs = results.get('documents', [[]])[0] if 'documents' in results else results.get('documents', [])
    metas = results.get('metadatas', [[]])[0] if 'metadatas' in results else results.get('metadatas', [])

    for doc, metadata, in zip(docs, metas):
        formatted_results.append({
            'file': metadata['file'],
            'title': metadata['title'],
            'section': metadata['section_header'],
            'content': doc
        })    

    return json.dumps(formatted_results, indent=2)

async def run_server():
    """Run the MCP server with proper signal handling."""
    loop = asyncio.get_running_loop()
    
    def handle_signal():
        print("\nShutting down DCC guides agent MCP server...", file=sys.stderr)
        # Force exit to avoid blocking on stdin
        os._exit(0)

    # Add signal handlers for graceful shutdown
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)

    print("Started the DCC guides agent MCP server...", file=sys.stderr)
    print("Press Ctrl+C to stop the server", file=sys.stderr)

    await mcp.run_stdio_async()


def main():
    # asyncio.run(run_server())
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()

