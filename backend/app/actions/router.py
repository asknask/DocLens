"""
Action router - dispatches to specific action handlers.
"""
from typing import Any

from app.models.api_models import ActionType
from app.models.ir_models import DocumentIR

from .summarize import summarize_document
from .extract_structured import extract_structured_data
from .classify import classify_document
from .qa import answer_question
from .transform import transform_document
from .instruction_normalizer import normalize_instructions


async def execute_action(
    action: ActionType,
    document_ir: DocumentIR,
    options: dict[str, Any] | None = None,
    refine: str | None = None,
    output_format: str | None = "descriptive",
) -> dict[str, Any]:
    """
    Execute a document analysis action.
    
    Args:
        action: The action type to execute
        document_ir: Extracted document content
        options: Action-specific options
        refine: Free-text refinement instructions
        output_format: 'descriptive' for prose or 'json' for structured
        
    Returns:
        Action result as dictionary
    """
    options = options or {}
    output_format = output_format or "descriptive"
    
    # Normalize any refine instructions into options
    if refine:
        normalized = normalize_instructions(refine, action, options)
        if normalized.get("error"):
            # Return error if instructions are unsupported
            return {
                "error": "unsupported_instruction",
                "message": normalized["error"],
                "original_refine": refine,
            }
        options = {**options, **normalized.get("options", {})}
    
    # Dispatch to action handler
    if action == ActionType.SUMMARIZE:
        result = await summarize_document(document_ir, options, output_format)
    elif action == ActionType.EXTRACT_STRUCTURED:
        result = await extract_structured_data(document_ir, options, output_format)
    elif action == ActionType.CLASSIFY:
        result = await classify_document(document_ir, options, output_format)
    elif action == ActionType.QA:
        if "question" not in options:
            return {
                "error": "missing_required_option",
                "message": "QA action requires 'question' in options",
            }
        result = await answer_question(document_ir, options["question"], options, output_format)
    elif action == ActionType.TRANSFORM:
        result = await transform_document(document_ir, options, output_format)
    else:
        return {
            "error": "unknown_action",
            "message": f"Unknown action type: {action}",
        }
    
    return result

