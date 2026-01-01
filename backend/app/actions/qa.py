"""
QA action - question answering over documents using LangChain.
"""
from typing import Any

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.config import get_settings
from app.models.ir_models import DocumentIR


class EvidenceItem(BaseModel):
    """Evidence supporting an answer."""
    quote: str = Field(description="Relevant quote from the document")
    location: str | None = Field(default=None, description="Location hint (page, section, etc.)")


class QAOutput(BaseModel):
    """Structured output for question answering."""
    answer: str = Field(description="Direct answer to the question")
    evidence: list[EvidenceItem] = Field(
        default_factory=list,
        description="Supporting evidence from the document"
    )
    confidence: float = Field(ge=0, le=1, description="Confidence in the answer")
    notes: str | None = Field(default=None, description="Any caveats or additional context")


def get_llm() -> ChatOpenAI:
    """Get configured ChatOpenAI model."""
    settings = get_settings()
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )


async def answer_question(
    document_ir: DocumentIR,
    question: str,
    options: dict[str, Any] | None = None,
    output_format: str = "descriptive",
) -> dict[str, Any]:
    """
    Answer a question about a document using LangChain.
    
    Args:
        document_ir: Extracted document content
        question: The question to answer
        options: Optional configuration (require_evidence, include_context)
        output_format: 'descriptive' for prose or 'json' for structured
        
    Returns:
        QAResult as dictionary
    """
    options = options or {}
    
    # Get document text
    doc_text = document_ir.get_text_for_llm(max_chars=50000)
    
    if not doc_text.strip():
        if output_format == "json":
            return {
                "answer": "I cannot answer this question as the document appears to be empty or contains only images without extracted text.",
                "evidence": [],
                "confidence": 0.0,
                "notes": "Document content was not available for analysis.",
            }
        else:
            return {
                "description": f"# Answer to: {question}\n\nI cannot answer this question as the document appears to be empty or contains only images without extracted text.",
            }
    
    # Build evidence instruction
    evidence_instruction = ""
    if options.get("require_evidence", True):
        evidence_instruction = """
You MUST provide evidence from the document to support your answer.
- Include 1-3 relevant quotes from the document
- Specify where in the document each quote appears if possible"""
    else:
        evidence_instruction = "Provide evidence if available, but it's not strictly required."
    
    llm = get_llm()
    
    if output_format == "json":
        # Structured JSON output (original behavior)
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert document analyst answering questions based on document content.

Guidelines:
- Answer based ONLY on information found in the document
- If the answer is not in the document, say so clearly
- Be direct and specific in your answer
{evidence_instruction}
- Provide a confidence score based on how clearly the document answers the question"""),
            ("user", """Document content:
---
{document_text}
---

Question: {question}

Please provide a comprehensive answer based on the document above."""),
        ])
        
        structured_llm = llm.with_structured_output(QAOutput)
        chain = prompt | structured_llm
        
        result = await chain.ainvoke({
            "document_text": doc_text,
            "question": question,
            "evidence_instruction": evidence_instruction,
        })
        
        output = result.model_dump()
        output["evidence"] = [
            {"quote": e["quote"], "location": e["location"]}
            for e in output["evidence"]
        ]
        
        return output
    else:
        # Descriptive prose output
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert document analyst answering questions based on document content.

Guidelines:
- Answer based ONLY on information found in the document
- If the answer is not in the document, say so clearly
- Be direct and specific in your answer
- Include relevant quotes to support your answer
- Indicate your confidence level

Write your response as a clear, readable answer with:
1. A direct answer to the question
2. Supporting evidence from the document
3. Any caveats or limitations

Use markdown formatting for headers, quotes, and emphasis."""),
            ("user", """Document content:
---
{document_text}
---

Question: {question}

Please provide a comprehensive answer based on the document above."""),
        ])
        
        chain = prompt | llm
        
        result = await chain.ainvoke({
            "document_text": doc_text,
            "question": question,
        })
        
        return {"description": result.content}
