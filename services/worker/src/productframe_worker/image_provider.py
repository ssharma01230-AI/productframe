"""Provider interface for generated product images.

The graph will depend on this small interface rather than a specific model
vendor. The fake provider is used until a real image-generation adapter is
connected.
"""
from dataclasses import dataclass
from typing import Protocol

from productframe_api.generation_prompts import GenerationPrompt


@dataclass(frozen=True, slots=True)
class GeneratedImage:
    content: bytes
    content_type: str
    filename: str
    provider: str
    request_id: str | None = None


class ImageGenerationProvider(Protocol):
    def generate(self, request: GenerationPrompt) -> GeneratedImage:
        """Generate one image from a fully assembled provider-neutral request."""
        ...


# A valid 1x1 PNG. It keeps tests independent from external model providers.
_FAKE_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c6360f8cf00000003000100018d0d0d"
    "0000000049454e44ae426082"
)


class FakeImageGenerationProvider:
    """Deterministic provider for graph and prompt integration tests."""

    def __init__(self) -> None:
        self.requests: list[GenerationPrompt] = []

    def generate(self, request: GenerationPrompt) -> GeneratedImage:
        self.requests.append(request)
        return GeneratedImage(
            content=_FAKE_PNG,
            content_type="image/png",
            filename=f"{request.template_id}.png",
            provider="fake",
        )
