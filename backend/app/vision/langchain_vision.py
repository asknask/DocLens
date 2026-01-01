"""
LangChain-based vision processing using OpenAI.
Describes images and extracts text/OCR from visual content.
"""
import base64
from typing import Optional

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from app.config import get_settings
from app.models.ir_models import ImageBlock


class ImageDescription(BaseModel):
    """Structured output for image description."""
    description: str = Field(description="Detailed description of the image content")
    visible_text: str = Field(default="", description="Any visible text in the image (OCR)")
    is_document: bool = Field(default=False, description="Whether this appears to be a document/page scan")
    key_elements: list[str] = Field(default_factory=list, description="Key visual elements identified")


def get_vision_model() -> ChatOpenAI:
    """Get configured vision-capable ChatOpenAI model."""
    settings = get_settings()
    return ChatOpenAI(
        model=settings.openai_vision_model,
        api_key=settings.openai_api_key,
        max_tokens=4000,  # Increased for detailed tabular data extraction
        temperature=0,
    )


def image_to_base64_url(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    """Convert image bytes to base64 data URL."""
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"


async def describe_image(
    image_block: ImageBlock,
    context: Optional[str] = None,
) -> ImageDescription:
    """
    Describe an image using LangChain with OpenAI vision.
    
    Args:
        image_block: ImageBlock with image data or path
        context: Optional context about the document
        
    Returns:
        ImageDescription with structured output
    """
    settings = get_settings()
    
    # Get image data
    if image_block.image_data:
        image_bytes = image_block.image_data
    elif image_block.image_path:
        with open(image_block.image_path, "rb") as f:
            image_bytes = f.read()
    else:
        raise ValueError("ImageBlock has no image data or path")
    
    # Create base64 URL
    image_url = image_to_base64_url(image_bytes, image_block.mime_type)
    
    # Build prompt
    system_context = ""
    if context:
        system_context = f"Context about the document: {context}\n\n"
    
    prompt = f"""{system_context}Analyze this image and provide:
1. A detailed description of what you see
2. Any visible text - transcribe ALL text exactly as shown. IMPORTANT: If the image contains tabular data, tables, or data grids:
   - Identify column headers first
   - Format as a proper table with columns aligned
   - Use markdown table format or clear column separators (|)
   - Preserve the relationship between row labels and their values in each column
   - Example: "Sensor | Current | Min | Max" then "CPU Temp | 48.5°C | 45.1°C | 80.0°C"
3. Whether this appears to be a document/page scan
4. Key visual elements

Be thorough and precise. For data/monitoring screenshots, accuracy of values and their column positions is critical."""

    # Create message with image
    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {"url": image_url, "detail": "auto"},
            },
        ]
    )
    
    # Get vision model with structured output
    model = get_vision_model()
    structured_model = model.with_structured_output(ImageDescription)
    
    # Invoke model
    result = await structured_model.ainvoke([message])
    
    return result


async def describe_images_batch(
    image_blocks: list[ImageBlock],
    context: Optional[str] = None,
) -> list[ImageDescription]:
    """
    Describe multiple images in batch.
    
    Args:
        image_blocks: List of ImageBlocks to process
        context: Optional context about the document
        
    Returns:
        List of ImageDescriptions in same order as input
    """
    import asyncio
    
    if not image_blocks:
        return []
    
    # Process images concurrently with some limit
    semaphore = asyncio.Semaphore(3)  # Max 3 concurrent requests
    
    async def process_with_semaphore(img_block: ImageBlock) -> ImageDescription:
        async with semaphore:
            try:
                return await describe_image(img_block, context)
            except Exception as e:
                # Return a minimal description on error
                return ImageDescription(
                    description=f"[Error processing image: {str(e)}]",
                    visible_text="",
                    is_document=False,
                    key_elements=[],
                )
    
    tasks = [process_with_semaphore(img) for img in image_blocks]
    results = await asyncio.gather(*tasks)
    
    return list(results)


def update_image_blocks_with_descriptions(
    image_blocks: list[ImageBlock],
    descriptions: list[ImageDescription],
) -> None:
    """
    Update ImageBlocks in-place with vision descriptions.
    
    Args:
        image_blocks: Original image blocks
        descriptions: Corresponding descriptions
    """
    for img_block, desc in zip(image_blocks, descriptions):
        img_block.vision_description = desc.description
        if desc.visible_text:
            img_block.ocr_text = desc.visible_text


# Synchronous wrapper for non-async contexts
def describe_image_sync(
    image_block: ImageBlock,
    context: Optional[str] = None,
) -> ImageDescription:
    """Synchronous wrapper for describe_image."""
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(describe_image(image_block, context))
