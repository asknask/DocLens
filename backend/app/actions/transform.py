"""
Transform action - document transformation using LangChain.
"""
from typing import Any

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.config import get_settings
from app.models.ir_models import DocumentIR


class TransformOutput(BaseModel):
    """Structured output for transformation."""
    output: str = Field(description="The transformed document content")
    format_hint: str = Field(default="text", description="Format of the output (text, markdown, json, etc.)")
    notes: list[str] = Field(default_factory=list, description="Notes about the transformation")


def get_llm() -> ChatOpenAI:
    """Get configured ChatOpenAI model."""
    settings = get_settings()
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.1,  # Slightly higher for creative transformations
    )


async def transform_document(
    document_ir: DocumentIR,
    options: dict[str, Any] | None = None,
    output_format: str = "descriptive",
) -> dict[str, Any]:
    """
    Transform a document to a different format or structure.
    
    Args:
        document_ir: Extracted document content
        options: Transformation options (target_format, instructions)
        output_format: 'descriptive' for prose or 'json' for structured
        
    Returns:
        TransformResult as dictionary
    """
    options = options or {}
    
    # Get document text
    doc_text = document_ir.get_text_for_llm(max_chars=50000)
    
    if not doc_text.strip():
        if output_format == "json":
            return {
                "output": "",
                "format_hint": "text",
                "notes": ["Document appears to be empty or contains only images."],
            }
        else:
            return {
                "description": "# Transformation Result\n\nDocument appears to be empty or contains only images.",
            }
    
    # Get transformation parameters
    target_format = options.get("target_format", "markdown")
    custom_instructions = options.get("instructions", "")
    brevity = options.get("brevity", "")
    
    # Build transformation instruction
    format_instructions = _get_format_instructions(target_format)
    
    brevity_instruction = ""
    if brevity == "short":
        brevity_instruction = "Keep the output concise and remove any non-essential content."
    elif brevity == "detailed":
        brevity_instruction = "Preserve all details and expand abbreviations where helpful."
    
    llm = get_llm()
    
    if output_format == "json":
        # Structured JSON output (original behavior)
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a document transformation expert. Transform the document according to the specifications.

Target Format: {target_format}
{format_instructions}

{brevity_instruction}

Additional Instructions: {custom_instructions}

Guidelines:
- Preserve the essential meaning and information
- Structure the output appropriately for the target format
- Note any content that couldn't be transformed properly"""),
            ("user", """Transform this document:

---
{document_text}
---"""),
        ])
        
        structured_llm = llm.with_structured_output(TransformOutput)
        chain = prompt | structured_llm
        
        result = await chain.ainvoke({
            "document_text": doc_text,
            "target_format": target_format,
            "format_instructions": format_instructions,
            "brevity_instruction": brevity_instruction,
            "custom_instructions": custom_instructions or "None specified",
        })
        
        return result.model_dump()
    else:
        # Descriptive prose output - for transform, the output IS the description
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a document transformation expert. Transform the document according to the specifications.

Target Format: {target_format}
{format_instructions}

{brevity_instruction}

Additional Instructions: {custom_instructions}

Guidelines:
- Preserve the essential meaning and information
- Structure the output appropriately for the target format"""),
            ("user", """Transform this document:

---
{document_text}
---"""),
        ])
        
        chain = prompt | llm
        
        result = await chain.ainvoke({
            "document_text": doc_text,
            "target_format": target_format,
            "format_instructions": format_instructions,
            "brevity_instruction": brevity_instruction,
            "custom_instructions": custom_instructions or "None specified",
        })
        
        return {"description": result.content}


def _get_format_instructions(target_format: str) -> str:
    """Get specific instructions for various output formats."""
    format_map = {
        "markdown": """
Convert to clean Markdown:
- Use proper headings (# ## ###)
- Use bullet points and numbered lists
- Format tables as Markdown tables
- Preserve emphasis (bold, italic)""",
        
        "json": """
Convert to structured JSON:
- Identify logical sections and nest them
- Use arrays for lists
- Keep field names lowercase with underscores
- Include metadata if relevant""",
        
        "plain": """
Convert to plain text:
- Remove all formatting
- Use line breaks for structure
- Indent nested content
- Keep it readable""",
        
        "html": """
Convert to clean HTML:
- Use semantic elements (article, section, h1-h6)
- Apply basic styling considerations
- Include proper structure
- Keep it valid HTML5""",
        
        "summary": """
Create a structured summary:
- Executive overview first
- Key points as bullet list
- Important details highlighted
- Conclusions at the end""",
        
        "outline": """
Create a hierarchical outline:
- Main topics as top-level items
- Sub-points indented below
- Use consistent numbering or bullets
- Maximum 3 levels of nesting""",
    }
    
    return format_map.get(target_format.lower(), f"Transform to {target_format} format as appropriate.")
