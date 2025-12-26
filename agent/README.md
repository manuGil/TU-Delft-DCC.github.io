# Guia
An AI assistant for the DCC Guides.


## Installation

1. Intall `uv`:

2. Install `guia`:

   ```bash
   cd ./agent/ 
   uv pip install -e .
   ```

## Indexing Documents
The RAG system needs to index the documents before being able to answer questions based on them. To index documents, run the following command:

```bash
python ./src/guia/utils/build_index.py
```

## Configure your MCP Client

For Claude Desktop, add the following configuration to your `claude_desktop_config.json` file:

```json
{
  "mcpServers": {
    "dcc-guides": {
      "command": "/opt/homebrew/bin/uv",
      "args": [
        "--directory",
        "/Users/mgarciaalvarez/devel/dcc-guides/agent/src/guia",
        "run",
        "server.py"
      ]
    }
  }
}
```
