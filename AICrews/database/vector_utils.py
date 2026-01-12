import os

from AICrews.observability.logging import get_logger

logger = get_logger(__name__)

try:
    from fastembed import TextEmbedding
except ModuleNotFoundError:
    TextEmbedding = None


class VectorUtil:
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            if TextEmbedding is None:
                raise RuntimeError("fastembed is required for local embeddings")
            # 使用 FastEmbed 加载轻量级 ONNX 模型
            # 首次运行会自动下载 (约 <100MB)，比 PyTorch 方案小 10 倍以上
            logger.info("Loading local embedding model (FastEmbed: all-MiniLM-L6-v2)")

            # cache_dir 可以指定模型下载路径，默认在 ~/.cache/fastembed
            cls._model = TextEmbedding(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
        return cls._model

    @classmethod
    def get_embedding(cls, text: str):
        """
        本地生成向量，使用 FastEmbed (ONNX Runtime)，无需 PyTorch
        """
        try:
            model = cls.get_model()
            # 移除换行符，减少噪音
            text = text.replace("\n", " ")

            # model.embed 接受列表，返回的是一个生成器 (generator)
            # 我们这里只处理单条文本
            embeddings_generator = model.embed([text])

            # 获取第一个结果 (它是 numpy array)
            embedding_numpy = next(embeddings_generator)

            # 转为 list 存入数据库
            return embedding_numpy.tolist()

        except Exception as e:
            logger.error(f"Failed to generate local embedding: {e}", exc_info=True)
            # 返回 384 维的零向量 (all-MiniLM-L6-v2 的维度固定 384)
            return [0.0] * 384
