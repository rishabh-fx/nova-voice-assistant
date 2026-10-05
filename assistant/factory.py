"""Wires the pieces together: cloud LLM client + tools + agent."""
from .agent import Agent, make_client
from .tools import ToolRegistry


def build_agent(settings, timezone="UTC", client=None):
    client = client or make_client(settings.check())
    tools = ToolRegistry(timezone=timezone, tavily_api_key=settings.tavily_api_key)
    return Agent(client, settings.chat_model, tools)
