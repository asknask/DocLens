"""
Classify action - document classification using LangChain.
"""
from typing import Any

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.config import get_settings
from app.models.ir_models import DocumentIR


# Default classification labels
DEFAULT_LABELS = [
    "invoice",
    "contract", 
    "resume",
    "report",
    "presentation",
    "letter",
    "form",
    "receipt",
    "statement",
    "other",
]


class ClassificationOutput(BaseModel):
    """Structured output for classification."""
    label: str = Field(description="The classification label that best matches the document")
    confidence: float = Field(ge=0, le=1, description="Confidence score from 0 to 1")
    reasons: list[str] = Field(description="Reasons supporting this classification")
    secondary_label: str | None = Field(default=None, description="Second most likely label if applicable")


def get_llm() -> ChatOpenAI:
    """Get configured ChatOpenAI model."""
    settings = get_settings()
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )


async def classify_document(
    document_ir: DocumentIR,
    options: dict[str, Any] | None = None,
    output_format: str = "descriptive",
) -> dict[str, Any]:
    """
    Classify a document using LangChain with OpenAI.
    
    Args:
        document_ir: Extracted document content
        options: Optional configuration (custom_labels)
        output_format: 'descriptive' for prose or 'json' for structured
        
    Returns:
        ClassifyResult as dictionary
    """
    options = options or {}
    
    # Get document text
    doc_text = document_ir.get_text_for_llm(max_chars=30000)
    
    if not doc_text.strip():
        # Try to classify based on metadata alone
        result = _classify_by_metadata(document_ir)
        if output_format == "json":
            return result
        else:
            return {
                "description": f"# Document Classification\n\n**Classification:** {result['label']}\n**Confidence:** {result['confidence']:.0%}\n\n## Reasoning\n- {result['reasons'][0]}",
            }
    
    # Get labels to use
    labels = options.get("custom_labels", DEFAULT_LABELS)
    labels_str = ", ".join(labels)
    
    llm = get_llm()
    
    if output_format == "json":
        # Structured JSON output (original behavior)
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert document classifier. Analyze the document and classify it into one of the following categories:

Categories: {labels}

Guidelines:
- Choose the single best matching category
- Provide a confidence score (0.0 to 1.0) based on how well it matches
- List 2-4 specific reasons for your classification
- If document could fit multiple categories, mention the secondary option"""),
            ("user", """Classify this document:

Filename: {filename}
Content:
---
{document_text}
---"""),
        ])
        
        structured_llm = llm.with_structured_output(ClassificationOutput)
        chain = prompt | structured_llm
        
        result = await chain.ainvoke({
            "document_text": doc_text,
            "filename": document_ir.metadata.filename,
            "labels": labels_str,
        })
        
        output = result.model_dump()
        if output["label"].lower() not in [l.lower() for l in labels]:
            output["label"] = "other"
        
        return output
    else:
        # Descriptive prose output
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert document classifier. Analyze the document and provide a clear classification explanation.

Available categories: {labels}

Write your response as a clear explanation with:
1. The document classification
2. Your confidence level
3. Key reasons for this classification
4. Any alternative classifications that might apply

Use markdown formatting for headers and emphasis."""),
            ("user", """Classify this document:

Filename: {filename}
Content:
---
{document_text}
---"""),
        ])
        
        chain = prompt | llm
        
        result = await chain.ainvoke({
            "document_text": doc_text,
            "filename": document_ir.metadata.filename,
            "labels": labels_str,
        })
        
        return {"description": result.content}


def _classify_by_metadata(document_ir: DocumentIR) -> dict[str, Any]:
    """Fallback classification based on file metadata."""
    filename = document_ir.metadata.filename.lower()
    
    # Simple heuristics based on filename
    if any(term in filename for term in ["invoice", "inv_", "bill"]):
        label = "invoice"
    elif any(term in filename for term in ["contract", "agreement"]):
        label = "contract"
    elif any(term in filename for term in ["resume", "cv"]):
        label = "resume"
    elif any(term in filename for term in ["report", "rpt"]):
        label = "report"
    elif any(term in filename for term in ["receipt"]):
        label = "receipt"
    else:
        label = "other"
    
    return {
        "label": label,
        "confidence": 0.3,
        "reasons": ["Classification based on filename only (document content was empty)"],
        "secondary_label": None,
    }
