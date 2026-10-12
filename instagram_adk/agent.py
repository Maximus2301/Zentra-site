"""Single-agent entrypoint for ADK Web UI (adk web)."""
from .workflow import build_instagram_workflow

# The root_agent exported here is loaded by ADK CLI and Web UI
root_agent = build_instagram_workflow()
