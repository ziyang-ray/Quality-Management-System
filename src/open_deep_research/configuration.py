"""Configuration management for the Open Deep Research system."""

import os
from enum import Enum
from typing import Any, List, Optional

from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field


class SearchAPI(Enum):
    """Enumeration of available search API providers."""
    
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    TAVILY = "tavily"
    NONE = "none"

class MCPConfig(BaseModel):
    """Configuration for Model Context Protocol (MCP) servers."""
    
    url: Optional[str] = Field(
        default=None,
        optional=True,
    )
    """The URL of the MCP server"""
    tools: Optional[List[str]] = Field(
        default=None,
        optional=True,
    )
    """The tools to make available to the LLM"""
    auth_required: Optional[bool] = Field(
        default=False,
        optional=True,
    )
    """Whether the MCP server requires authentication"""

class Configuration(BaseModel):
    """Main configuration class for the Deep Research agent."""
    
    # General Configuration
    assistant_name: str = Field(
        default="Siemens Healthineers Compliance Assistant",
        metadata={
            "x_oap_ui_config": {
                "type": "text",
                "default": "Siemens Healthineers Compliance Assistant",
                "description": "Display name and role identity for the assistant"
            }
        }
    )
    organization_name: str = Field(
        default="Siemens Healthineers",
        metadata={
            "x_oap_ui_config": {
                "type": "text",
                "default": "Siemens Healthineers",
                "description": "Organization name used in prompts and compliance reports"
            }
        }
    )
    business_region: str = Field(
        default="Unspecified",
        metadata={
            "x_oap_ui_config": {
                "type": "text",
                "default": "Unspecified",
                "description": "Business region or country context for compliance analysis"
            }
        }
    )
    compliance_scope: str = Field(
        default=(
            "medical technology compliance, healthcare compliance, internal policies, "
            "privacy, quality, anti-corruption, procurement, marketing, and interactions "
            "with healthcare professionals"
        ),
        metadata={
            "x_oap_ui_config": {
                "type": "text",
                "description": "Compliance domains the assistant should prioritize"
            }
        }
    )
    external_search_allowed: bool = Field(
        default=False,
        metadata={
            "x_oap_ui_config": {
                "type": "boolean",
                "default": False,
                "description": "Whether the assistant may use external web search. Keep disabled for confidential internal work."
            }
        }
    )
    max_structured_output_retries: int = Field(
        default=3,
        metadata={
            "x_oap_ui_config": {
                "type": "number",
                "default": 3,
                "min": 1,
                "max": 10,
                "description": "Maximum number of retries for structured output calls from models"
            }
        }
    )
    allow_clarification: bool = Field(
        default=True,
        metadata={
            "x_oap_ui_config": {
                "type": "boolean",
                "default": True,
                "description": "Whether to allow the researcher to ask the user clarifying questions before starting research"
            }
        }
    )
    max_concurrent_research_units: int = Field(
        default=5,
        metadata={
            "x_oap_ui_config": {
                "type": "slider",
                "default": 5,
                "min": 1,
                "max": 20,
                "step": 1,
                "description": "Maximum number of research units to run concurrently. This will allow the researcher to use multiple sub-agents to conduct research. Note: with more concurrency, you may run into rate limits."
            }
        }
    )
    # Research Configuration
    search_api: SearchAPI = Field(
        default=SearchAPI.NONE,
        metadata={
            "x_oap_ui_config": {
                "type": "select",
                "default": "none",
                "description": "External search API to use only when external_search_allowed is enabled. NOTE: Make sure your Researcher Model supports the selected search API.",
                "options": [
                    {"label": "None", "value": SearchAPI.NONE.value},
                    {"label": "Tavily", "value": SearchAPI.TAVILY.value},
                    {"label": "OpenAI Native Web Search", "value": SearchAPI.OPENAI.value},
                    {"label": "Anthropic Native Web Search", "value": SearchAPI.ANTHROPIC.value}
                ]
            }
        }
    )
    max_researcher_iterations: int = Field(
        default=6,
        metadata={
            "x_oap_ui_config": {
                "type": "slider",
                "default": 6,
                "min": 1,
                "max": 10,
                "step": 1,
                "description": "Maximum number of research iterations for the Research Supervisor. This is the number of times the Research Supervisor will reflect on the research and ask follow-up questions."
            }
        }
    )
    max_react_tool_calls: int = Field(
        default=10,
        metadata={
            "x_oap_ui_config": {
                "type": "slider",
                "default": 10,
                "min": 1,
                "max": 30,
                "step": 1,
                "description": "Maximum number of tool calling iterations to make in a single researcher step."
            }
        }
    )
    internal_knowledge_base_path: Optional[str] = Field(
        default=None,
        optional=True,
        metadata={
            "x_oap_ui_config": {
                "type": "text",
                "description": "Local folder path containing internal compliance documents for retrieval"
            }
        }
    )
    internal_search_file_globs: str = Field(
        default="*.md,*.txt,*.pdf",
        metadata={
            "x_oap_ui_config": {
                "type": "text",
                "default": "*.md,*.txt,*.pdf",
                "description": "Comma-separated file patterns to include in internal document search"
            }
        }
    )
    internal_search_max_results: int = Field(
        default=5,
        metadata={
            "x_oap_ui_config": {
                "type": "number",
                "default": 5,
                "min": 1,
                "max": 20,
                "description": "Maximum number of internal document chunks returned per search"
            }
        }
    )
    internal_search_chunk_chars: int = Field(
        default=3500,
        metadata={
            "x_oap_ui_config": {
                "type": "number",
                "default": 3500,
                "min": 1000,
                "max": 12000,
                "description": "Approximate character size for internal document chunks"
            }
        }
    )
    # Model Configuration
    summarization_model: str = Field(
        default="openai:gpt-4.1-mini",
        metadata={
            "x_oap_ui_config": {
                "type": "text",
                "default": "openai:gpt-4.1-mini",
                "description": "Model for summarizing research results from Tavily search results"
            }
        }
    )
    summarization_model_max_tokens: int = Field(
        default=8192,
        metadata={
            "x_oap_ui_config": {
                "type": "number",
                "default": 8192,
                "description": "Maximum output tokens for summarization model"
            }
        }
    )
    max_content_length: int = Field(
        default=50000,
        metadata={
            "x_oap_ui_config": {
                "type": "number",
                "default": 50000,
                "min": 1000,
                "max": 200000,
                "description": "Maximum character length for webpage content before summarization"
            }
        }
    )
    research_model: str = Field(
        default="openai:gpt-4.1",
        metadata={
            "x_oap_ui_config": {
                "type": "text",
                "default": "openai:gpt-4.1",
                "description": "Model for conducting research. NOTE: Make sure your Researcher Model supports the selected search API."
            }
        }
    )
    research_model_max_tokens: int = Field(
        default=10000,
        metadata={
            "x_oap_ui_config": {
                "type": "number",
                "default": 10000,
                "description": "Maximum output tokens for research model"
            }
        }
    )
    compression_model: str = Field(
        default="openai:gpt-4.1",
        metadata={
            "x_oap_ui_config": {
                "type": "text",
                "default": "openai:gpt-4.1",
                "description": "Model for compressing research findings from sub-agents. NOTE: Make sure your Compression Model supports the selected search API."
            }
        }
    )
    compression_model_max_tokens: int = Field(
        default=8192,
        metadata={
            "x_oap_ui_config": {
                "type": "number",
                "default": 8192,
                "description": "Maximum output tokens for compression model"
            }
        }
    )
    final_report_model: str = Field(
        default="openai:gpt-4.1",
        metadata={
            "x_oap_ui_config": {
                "type": "text",
                "default": "openai:gpt-4.1",
                "description": "Model for writing the final report from all research findings"
            }
        }
    )
    final_report_model_max_tokens: int = Field(
        default=10000,
        metadata={
            "x_oap_ui_config": {
                "type": "number",
                "default": 10000,
                "description": "Maximum output tokens for final report model"
            }
        }
    )
    # MCP server configuration
    mcp_config: Optional[MCPConfig] = Field(
        default=None,
        optional=True,
        metadata={
            "x_oap_ui_config": {
                "type": "mcp",
                "description": "MCP server configuration"
            }
        }
    )
    mcp_prompt: Optional[str] = Field(
        default=None,
        optional=True,
        metadata={
            "x_oap_ui_config": {
                "type": "text",
                "description": "Any additional instructions to pass along to the Agent regarding the MCP tools that are available to it."
            }
        }
    )
    # Compliance review configuration
    official_docs_path: str = Field(
        default="./data/official_docs",
        metadata={
            "x_oap_ui_config": {
                "type": "text",
                "default": "./data/official_docs",
                "description": "Path containing official standards and regulations for compliance review"
            }
        }
    )
    internal_docs_path: str = Field(
        default="./data/internal_docs",
        metadata={
            "x_oap_ui_config": {
                "type": "text",
                "default": "./data/internal_docs",
                "description": "Path containing internal QMS documents for compliance review"
            }
        }
    )
    compliance_index_path: str = Field(
        default="data/compliance_index",
        metadata={
            "x_oap_ui_config": {
                "type": "text",
                "default": "data/compliance_index",
                "description": "Local JSONL index directory for compliance evidence retrieval"
            }
        }
    )
    evidence_required: bool = Field(
        default=True,
        metadata={
            "x_oap_ui_config": {
                "type": "boolean",
                "default": True,
                "description": "Require cited internal evidence before classifying an item as compliant"
            }
        }
    )
    knowledge_graph_dir: Optional[str] = Field(
        default="data/compliance_graph",
        optional=True,
        metadata={
            "x_oap_ui_config": {
                "type": "text",
                "default": "data/compliance_graph",
                "description": "Directory containing compliance knowledge graph (nodes.jsonl, edges.jsonl)"
            }
        }
    )
    skills_dir: Optional[str] = Field(
        default="data/skills",
        optional=True,
        metadata={
            "x_oap_ui_config": {
                "type": "text",
                "default": "data/skills",
                "description": "Directory containing department skill packs (*.skill.yaml)"
            }
        }
    )
    memory_dir: Optional[str] = Field(
        default="data/review_memory",
        optional=True,
        metadata={
            "x_oap_ui_config": {
                "type": "text",
                "default": "data/review_memory",
                "description": "Directory for storing review memory and human feedback"
            }
        }
    )
    include_draft_skills: bool = Field(
        default=False,
        metadata={
            "x_oap_ui_config": {
                "type": "boolean",
                "default": False,
                "description": "Whether to include draft skills in formal reviews (for testing only)"
            }
        }
    )


    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """Create a Configuration instance from a RunnableConfig."""
        configurable = config.get("configurable", {}) if config else {}
        field_names = list(cls.model_fields.keys())
        values: dict[str, Any] = {
            field_name: os.environ.get(field_name.upper(), configurable.get(field_name))
            for field_name in field_names
        }
        return cls(**{k: v for k, v in values.items() if v is not None})

    class Config:
        """Pydantic configuration."""
        
        arbitrary_types_allowed = True
