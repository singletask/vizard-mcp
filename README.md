# Vizard MCP Server

AI video clipping and publishing MCP server powered by Vizard.ai.

Compatible with:

- Hermes
- Claude Desktop
- LobeHub
- Cursor

---

# Features

- Long video → AI clips
- Auto polling
- Viral score ranking
- AI caption generation
- Social publishing
- Workflow automation

## Tools

- create_clips
- create_clips_and_wait
- query_project
- publish_video
- generate_caption
- viral_pipeline

## LobeHub

Add the MCP server:

```json
{
  "mcpServers": {
    "vizard": {
      "command": "python",
      "args": ["server.py"]
    }
  }
}
```

## Run

```bash
pip install -r requirements.txt
python server.py
