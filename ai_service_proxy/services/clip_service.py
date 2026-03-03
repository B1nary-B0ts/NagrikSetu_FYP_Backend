import clip
import torch

class ClipService:
    _model = None
    _preprocess = None
    _device = "cpu"

    @classmethod
    def get_model(cls):
        if cls._model is None:
            cls._model, cls._preprocess = clip.load(
                "ViT-B/32",
                device=cls._device
            )
            cls._model.eval()
        return cls._model, cls._preprocess
