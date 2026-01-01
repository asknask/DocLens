"""
Summarize action - generates document summaries using LangChain.
"""
from typing import Any

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.config import get_settings
from app.models.ir_models import DocumentIR
from app.models.api_models import SummarizeResult


class SummaryOutput(BaseModel):
    """Structured output for summarization."""
    title: str = Field(description="A concise, informative title for the document")
    summary: str = Field(description="A 2-3 sentence summary of the main content")
    bullets: list[str] = Field(description="3-7 key bullet points from the document")
    key_findings: list[str] = Field(description="Critical findings or main conclusions")
    risks: list[str] = Field(default_factory=list, description="Any risks, warnings, or concerns mentioned")


def get_llm() -> ChatOpenAI:
    """Get configured ChatOpenAI model."""
    settings = get_settings()
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )


async def summarize_document(
    document_ir: DocumentIR,
    options: dict[str, Any] | None = None,
    output_format: str = "descriptive",
) -> dict[str, Any]:
    """
    Summarize a document using LangChain with OpenAI.
    
    Args:
        document_ir: Extracted document content
        options: Optional configuration (brevity, focus, max_bullets, language)
        output_format: 'descriptive' for prose or 'json' for structured
        
    Returns:
        SummarizeResult as dictionary
    """
    options = options or {}
    
    # Get document text
    doc_text = document_ir.get_text_for_llm(max_chars=50000)
    
    if not doc_text.strip():
        if output_format == "json":
            return {
                "title": document_ir.metadata.filename,
                "summary": "Document appears to be empty or contains only images.",
                "bullets": [],
                "key_findings": [],
                "risks": [],
            }
        else:
            return {
                "description": f"# {document_ir.metadata.filename}\n\nDocument appears to be empty or contains only images.",
            }
    
    # Build dynamic parts of prompt based on options
    brevity_instruction = ""
    if options.get("brevity") == "short":
        brevity_instruction = "Keep the summary very brief and concise. Use 3-4 bullet points maximum."
    elif options.get("brevity") == "detailed":
        brevity_instruction = "Provide a comprehensive and detailed summary with 6-8 bullet points."
    
    focus_instruction = ""
    if options.get("focus"):
        focus_instruction = f"Focus particularly on: {options['focus']}"
    
    language_instruction = ""
    if options.get("language"):
        language_instruction = f"Respond in {options['language']}."
    
    max_bullets = options.get("max_bullets", 7)
    
    llm = get_llm()
    
    if output_format == "json":
        # Structured JSON output
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert document analyst. Analyze the provided document and generate a structured summary.

{brevity_instruction}
{focus_instruction}
{language_instruction}

Guidelines:
- Title should capture the document's main purpose or topic
- Summary should be 2-3 sentences covering the essential content
- Bullet points should be {max_bullets} or fewer key points
- Key findings are the most important conclusions or facts
- Risks include any warnings, concerns, or potential issues mentioned"""),
            ("user", """Please summarize this document:

---
{document_text}
---"""),
        ])
        
        structured_llm = llm.with_structured_output(SummaryOutput)
        chain = prompt | structured_llm
        
        result = await chain.ainvoke({
            "document_text": doc_text,
            "brevity_instruction": brevity_instruction,
            "focus_instruction": focus_instruction,
            "language_instruction": language_instruction,
            "max_bullets": max_bullets,
        })
        
        return result.model_dump()
    else:
        # Descriptive prose output
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert document analyst. Analyze the provided document and write a clear, readable summary in prose format.

{brevity_instruction}
{focus_instruction}
{language_instruction}

Write your response as a well-structured document with:
1. A clear title for the document
2. A concise executive summary paragraph
3. Key points as a bulleted list (use markdown bullet points)
4. Important findings or conclusions
5. Any risks or concerns if applicable

Use markdown formatting for headers, bullets, and emphasis."""),
            ("user", """Please summarize this document:

---
{document_text}
---"""),
        ])
        
        chain = prompt | llm
        
        result = await chain.ainvoke({
            "document_text": doc_text,
            "brevity_instruction": brevity_instruction,
            "focus_instruction": focus_instruction,
            "language_instruction": language_instruction,
        })
        
        return {"description": result.content}

