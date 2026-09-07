"""The first LangGraph generation workflow: one product, one template."""
import logging
from typing import Any, NotRequired, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from sqlalchemy import select
from sqlalchemy.orm import Session

from productframe_api.generation_persistence import (
    mark_generation_job_generating,
    save_generation_result,
    mark_generation_job_failed,
)
from productframe_api.generation_prompts import (
    GenerationPrompt,
    GenerationRequest,
    ProductContext,
    ReferenceImage,
    build_generation_prompt,
)
from productframe_api.models import GenerationJob, Product, SourceAsset

from .checkpoint import postgres_checkpointer
from .generation_storage import FakeGeneratedImageStorage, GeneratedImageStorage
from .image_provider import FakeImageGenerationProvider, GeneratedImage, ImageGenerationProvider
from .fidelity_validator import ProductFidelityError, finish_generated_image


logger = logging.getLogger(__name__)


class GenerationGraphState(TypedDict):
    request: GenerationRequest
    prompt: NotRequired[GenerationPrompt]
    generated_image: NotRequired[GeneratedImage]
    status: NotRequired[str]


def build_prompt_node(state: GenerationGraphState) -> dict[str, object]:
    prompt = build_generation_prompt(state["request"])
    return {"prompt": prompt, "status": "prompt_ready"}


def generate_image_node(
    state: GenerationGraphState,
    *,
    provider: ImageGenerationProvider,
) -> dict[str, object]:
    image = provider.generate(state["prompt"])
    return {"generated_image": image, "status": "generated"}


def complete_generation_node(state: GenerationGraphState) -> dict[str, str]:
    return {"status": "completed"}


def create_generation_graph(provider: ImageGenerationProvider | None = None):
    """Compile a one-job graph with an injectable image provider."""
    selected_provider = provider or FakeImageGenerationProvider()

    def generate_node(state: GenerationGraphState) -> dict[str, object]:
        return generate_image_node(state, provider=selected_provider)

    graph = StateGraph(GenerationGraphState)
    graph.add_node("build_prompt", build_prompt_node)
    graph.add_node("generate_image", generate_node)
    graph.add_node("complete", complete_generation_node)
    graph.add_edge(START, "build_prompt")
    graph.add_edge("build_prompt", "generate_image")
    graph.add_edge("generate_image", "complete")
    graph.add_edge("complete", END)
    return graph.compile()


def run_single_generation(
    request: GenerationRequest,
    *,
    provider: ImageGenerationProvider | None = None,
) -> GenerationGraphState:
    graph = create_generation_graph(provider)
    return graph.invoke({"request": request})


class PersistedGenerationState(TypedDict):
    job_id: str
    request: NotRequired[GenerationRequest]
    prompt: NotRequired[GenerationPrompt]
    generated_image: NotRequired[GeneratedImage | None]
    preview_object_key: NotRequired[str]
    generated_filename: NotRequired[str]
    generated_content_type: NotRequired[str]
    object_key: NotRequired[str]
    status: NotRequired[str]
    human_approved: NotRequired[bool]


def create_persisted_generation_graph(
    db: Session,
    *,
    provider: ImageGenerationProvider,
    storage: GeneratedImageStorage,
    fidelity_validator: Any | None = None,
    checkpointer: Any | None = None,
):
    """Compile the one-job graph that writes its result to PostgreSQL and MinIO."""

    def load_job(state: PersistedGenerationState) -> dict[str, object]:
        job = db.get(GenerationJob, state["job_id"])
        if job is None:
            raise ValueError("Generation job not found")
        if job.generated_asset is not None:
            return {"status": "completed"}
        product = db.get(Product, job.product_id)
        if product is None or product.category is None:
            raise ValueError("Generation product is missing or has no category")
        mark_generation_job_generating(db, job.id)
        assets = db.scalars(select(SourceAsset).where(SourceAsset.product_id == product.id).order_by(SourceAsset.created_at, SourceAsset.id)).all()
        request = GenerationRequest(
            template_id=job.template_id,
            channel="ecommerce",
            product=ProductContext(
                name=product.name,
                category=product.category,
                product_type=product.product_type or product.name,
                colours=product.colours or "Not clearly visible",
                materials=product.materials or "Not clearly visible",
                features=tuple(product.features or ("No additional features confirmed",)),
                description=product.description or product.name,
                colour_details=(product.global_details or {}).get("colour") if product.global_details else None,
                global_details=product.global_details,
                category_details=product.category_details,
                confidence_details=product.confidence_details,
            ),
            product_reference_images=tuple(
                ReferenceImage(role="product_reference", object_key=asset.object_key, asset_id=asset.id)
                for asset in assets
            ),
        )
        return {"request": request, "status": "running"}

    def save_prompt(state: PersistedGenerationState) -> dict[str, str]:
        prompt = state["prompt"]
        job = db.get(GenerationJob, state["job_id"])
        if job is None:
            raise ValueError("Generation job not found")
        job.prompt = prompt.prompt
        job.negative_prompt = prompt.negative_prompt
        job.aspect_ratio = prompt.aspect_ratio
        db.commit()
        return {"status": "prompt_saved"}

    def generate(state: PersistedGenerationState) -> dict[str, object]:
        image = provider.generate(state["prompt"])
        job = db.get(GenerationJob, state["job_id"])
        if job is None:
            raise ValueError("Generation job not found")
        if not image.content or not image.content_type.startswith("image/"):
            raise ValueError("Generated output is not a valid image")
        if fidelity_validator is not None:
            try:
                restore = getattr(fidelity_validator, "restore", None)
                if callable(restore):
                    image = restore(state["prompt"], image)
                fidelity_validator.validate(state["prompt"], image)
            except ProductFidelityError:
                quarantine_key = f"workspaces/{job.workspace_id}/products/{job.product_id}/generations/{job.id}/rejected/{image.filename}"
                storage.put(quarantine_key, image)
                raise
        try:
            image = finish_generated_image(image)
        except Exception:
            # Finishing is cosmetic. A valid generation must remain deliverable
            # if decoding or enhancement fails for an unexpected provider format.
            logger.exception("Final image finishing failed; storing the validated image unchanged")
        key = f"workspaces/{job.workspace_id}/products/{job.product_id}/generations/{job.id}/preview/{image.filename}"
        storage.put(key, image)
        job.preview_object_key = key
        job.provider_request_id = image.request_id
        job.status = "awaiting_review"
        db.commit()
        # Do not return image bytes: the checkpoint must contain metadata only.
        return {"generated_image": None, "preview_object_key": key, "generated_filename": image.filename, "generated_content_type": image.content_type, "status": "awaiting_review"}

    def store_preview(state: PersistedGenerationState) -> dict[str, object]:
        image = state["generated_image"]
        if image is None or not image.content or not image.content_type.startswith("image/"):
            raise ValueError("Generated output is not a valid image")
        job = db.get(GenerationJob, state["job_id"])
        if job is None:
            raise ValueError("Generation job not found")
        key = f"workspaces/{job.workspace_id}/products/{job.product_id}/generations/{job.id}/preview/{image.filename}"
        storage.put(key, image)
        job.preview_object_key = key
        job.provider_request_id = image.request_id
        job.status = "awaiting_review"
        db.commit()
        return {"generated_image": None, "preview_object_key": key, "generated_filename": image.filename, "generated_content_type": image.content_type, "status": "awaiting_review"}

    def validate_image(state: PersistedGenerationState) -> dict[str, object]:
        job = db.get(GenerationJob, state["job_id"])
        if job is None:
            raise ValueError("Generation job not found")
        decision = interrupt({
            "type": "generated_image_review",
            "job_id": state["job_id"],
            "preview_object_key": state["preview_object_key"],
            "filename": state["generated_filename"],
            "content_type": state["generated_content_type"],
        })
        approved = decision.get("approved") if isinstance(decision, dict) else decision is True
        if approved is not True:
            job.status = "cancelled"
            job.error_message = "Rejected during human review"
            db.commit()
            return {"human_approved": False, "status": "rejected"}
        job.status = "validating"
        db.commit()
        return {"human_approved": True, "status": "validated"}

    def store(state: PersistedGenerationState) -> dict[str, str]:
        job_id = state["job_id"]
        job = db.get(GenerationJob, job_id)
        if job is None:
            raise ValueError("Generation job not found")
        object_key = f"workspaces/{job.workspace_id}/products/{job.product_id}/generations/{job.id}/final/{state['generated_filename']}"
        image = storage.get(state["preview_object_key"])
        storage.put(object_key, image)
        return {"object_key": object_key, "status": "stored"}

    def complete(state: PersistedGenerationState) -> dict[str, str]:
        save_generation_result(db, job_id=state["job_id"], object_key=state["object_key"], filename=state["generated_filename"], content_type=state["generated_content_type"])
        return {"status": "completed"}

    graph = StateGraph(PersistedGenerationState)
    graph.add_node("load_job", load_job)
    graph.add_node("build_prompt", lambda state: {"prompt": build_generation_prompt(state["request"]), "status": "prompt_ready"})
    graph.add_node("save_prompt", save_prompt)
    graph.add_node("generate_image", generate)
    graph.add_node("validate_image", validate_image)
    graph.add_node("store_preview", store_preview)
    graph.add_node("store_image", store)
    graph.add_node("complete", complete)
    def next_after_load(state: PersistedGenerationState) -> str:
        return END if state.get("status") == "completed" else "build_prompt"

    graph.add_edge(START, "load_job")
    graph.add_conditional_edges("load_job", next_after_load)
    graph.add_edge("build_prompt", "save_prompt")
    graph.add_edge("save_prompt", "generate_image")
    graph.add_edge("generate_image", "validate_image")
    graph.add_conditional_edges("validate_image", lambda state: "store_image" if state.get("human_approved") else END)
    graph.add_edge("store_image", "complete")
    graph.add_edge("complete", END)
    return graph.compile(checkpointer=checkpointer or InMemorySaver())


_PERSISTED_GRAPHS: dict[str, Any] = {}


def run_persisted_generation(
    db: Session,
    job_id: str,
    *,
    provider: ImageGenerationProvider | None = None,
    storage: GeneratedImageStorage | None = None,
    fidelity_validator: Any | None = None,
    checkpointer: Any | None = None,
) -> PersistedGenerationState:
    selected_provider = provider or FakeImageGenerationProvider()
    selected_storage = storage or FakeGeneratedImageStorage()

    def invoke(graph):
        job = db.get(GenerationJob, job_id)
        thread_id = job.graph_thread_id if job and job.graph_thread_id else f"generation-job-{job_id}"
        return graph.invoke({"job_id": job_id}, config={"configurable": {"thread_id": thread_id}})

    try:
        if checkpointer is not None:
            graph = _PERSISTED_GRAPHS.get(job_id)
            if graph is None:
                graph = create_persisted_generation_graph(db, provider=selected_provider, storage=selected_storage, fidelity_validator=fidelity_validator, checkpointer=checkpointer)
                _PERSISTED_GRAPHS[job_id] = graph
            return invoke(graph)
        # Production calls use PostgreSQL checkpoints. The connection remains
        # open for this invocation while the checkpoint is written durably.
        with postgres_checkpointer() as durable_checkpointer:
            graph = create_persisted_generation_graph(db, provider=selected_provider, storage=selected_storage, fidelity_validator=fidelity_validator, checkpointer=durable_checkpointer)
            return invoke(graph)
    except Exception as exc:
        db.rollback()
        try:
            mark_generation_job_failed(db, job_id=job_id, error_message=str(exc))
        except Exception:
            db.rollback()
        raise


def resume_persisted_generation(
    db: Session,
    job_id: str,
    *,
    approved: bool,
    provider: ImageGenerationProvider | None = None,
    storage: GeneratedImageStorage | None = None,
) -> PersistedGenerationState:
    """Resume review from PostgreSQL checkpoints, including after restart."""
    job = db.get(GenerationJob, job_id)
    if job is None:
        raise ValueError("Generation job not found")
    thread_id = job.graph_thread_id
    selected_provider = provider or FakeImageGenerationProvider()
    selected_storage = storage or FakeGeneratedImageStorage()
    try:
        if provider is None and storage is None and job_id in _PERSISTED_GRAPHS:
            graph = _PERSISTED_GRAPHS[job_id]
            return graph.invoke(Command(resume={"approved": approved}), config={"configurable": {"thread_id": thread_id}})
        with postgres_checkpointer() as durable_checkpointer:
            graph = create_persisted_generation_graph(db, provider=selected_provider, storage=selected_storage, checkpointer=durable_checkpointer)
            return graph.invoke(Command(resume={"approved": approved}), config={"configurable": {"thread_id": thread_id}})
    except Exception as exc:
        db.rollback()
        try:
            mark_generation_job_failed(db, job_id=job_id, error_message=str(exc))
        except Exception:
            db.rollback()
        _PERSISTED_GRAPHS.pop(job_id, None)
        raise
