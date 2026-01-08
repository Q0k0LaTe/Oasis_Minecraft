"""
AI Agent for analyzing item prompts and deciding mod properties using LangChain
"""
from typing import Dict, Any, Optional

from .langchain_agents import LangChainModOrchestrator


class ModAnalyzerAgent:
    """AI Agent that analyzes prompts and generates mod specifications"""

    def __init__(self):
        self.orchestrator = LangChainModOrchestrator()

    def analyze(self, user_prompt: str, author_name: str = None, mod_name_override: str = None) -> Dict[str, Any]:
        """
        Analyze user prompt and generate mod specification using the LangChain orchestrator.
        """
        print("Analyzing prompt with LangChain orchestrator")
        return self.orchestrator.run_pipeline(
            user_prompt=user_prompt,
            author_name=author_name,
            mod_name_override=mod_name_override,
        )

