from __future__ import annotations
from typing import TYPE_CHECKING
from .material import GPUMaterial
if TYPE_CHECKING:
    from ..graphics.upload import GPUSource

class Visual:
    def __init__(self, source: GPUSource, material: GPUMaterial):
        self.source = source
        self.material = material