# Vizard MCP Server

AI video clipping and publishing MCP server powered by Vizard.ai.

Compatible with:

- Hermes Agent
- Claude Desktop
- LobeHub
- Cursor
- OpenClaw
- Cline

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
- create_clips_advanced
- create_clips_and_wait
- wait_for_project_completion
- query_project
- edit_short_video
- publish_video
- generate_social_caption
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
