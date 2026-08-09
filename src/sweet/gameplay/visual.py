from __future__ import annotations
from typing import TYPE_CHECKING
from .material import Material
if TYPE_CHECKING:
    from ..graphics.upload import GPUSource

class Visual:
    def __init__(self, source: GPUSource, material: Material):
        self.source = source
        self.material = material