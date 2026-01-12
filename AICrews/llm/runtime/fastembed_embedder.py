from AICrews.observability.logging import get_logger
from typing import Iterable, List, Sequence, Union


logger = get_logger(__name__)

try:
    from crewai.rag.embeddings.providers.custom.embedding_callable import (
        CustomEmbeddingFunction,
    )
except Exception:  # pragma: no cover
    CustomEmbeddingFunction = object  # type: ignore[misc,assignment]


class FastEmbedEmbeddingFunction(CustomEmbeddingFunction):
    """CrewAI/Chroma compatible embedding callable backed by FastEmbed (CPU/local).

    CrewAI's embedder expects an EmbeddingFunction Protocol:
    - __call__(input: List[str]) -> List[vector]
    - optional embed_query for query embedding
    """

    _model = None

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name

    @classmethod
    def _get_model(cls, model_name: str):
        if cls._model is not None:
            return cls._model

        try:
            from fastembed import TextEmbedding
        except Exception as e:
            raise RuntimeError(
                "fastembed is required for local embeddings. Install it in the runtime environment."
            ) from e

        logger.info("Loading FastEmbed model: %s", model_name)
        cls._model = TextEmbedding(model_name=model_name)
        return cls._model

    def __call__(self, input: Union[str, Sequence[str]]) -> List[List[float]]:
        if isinstance(input, str):
            texts: List[str] = [input]
        else:
            texts = list(input)

        if not texts:
            raise ValueError("Embedding input is empty")

        model = self._get_model(self.model_name)
        embeddings: Iterable = model.embed(texts)
        vectors = []
        for emb in embeddings:
            # emb is typically a numpy array
            try:
                vectors.append(emb.tolist())
            except Exception:
                vectors.append(list(emb))
        return vectors

    def embed_query(self, input: Union[str, Sequence[str]]) -> List[List[float]]:
        return self.__call__(input)
