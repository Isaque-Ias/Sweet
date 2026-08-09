from abc import ABC, abstractmethod
from typing import Any, Optional
from ..resources.assets.import_data import AlphaMode
from ..graphics.upload import GPUTexture
from dataclasses import dataclass, field

class Material(ABC):
    @abstractmethod
    def extract(self) -> Any:
        pass

    @property
    @abstractmethod
    def alpha_mode(self) -> AlphaMode:
        pass

@dataclass
class PBRBaseLayer:
    color_texture: Optional[GPUTexture] = None
    color_factor: list[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    
    metalness_texture: Optional[GPUTexture] = None
    metalness_factor: float = 1.0
    
    roughness_texture: Optional[GPUTexture] = None
    roughness_factor: float = 1.0

@dataclass
class PBRSpecularLayer:
    texture: Optional[GPUTexture] = None
    factor: float = 1.0
    ior: float = 1.5

@dataclass
class PBRTransmissionLayer:
    texture: Optional[GPUTexture] = None
    factor: float = 1.0

@dataclass
class PBREmissiveLayer:
    texture: Optional[GPUTexture] = None
    factor: float = 1.0

class PBRMaterial(Material):
    def __init__(self, alpha_mode: AlphaMode = AlphaMode.OPAQUE):
        self._alpha_mode = alpha_mode
        
        self.base = PBRBaseLayer()
        self.specular = PBRSpecularLayer()
        self.transmission = PBRTransmissionLayer()
        self.emissive = PBREmissiveLayer()

    @property
    def alpha_mode(self) -> AlphaMode:
        return self._alpha_mode

    @alpha_mode.setter
    def alpha_mode(self, alpha_mode: AlphaMode) -> None:
        self._alpha_mode = alpha_mode

    def extract(self) -> dict[str, Any]:
        return {
            "base_color": self.base.color_factor,
            "metalness": self.base.metalness_factor,
            "roughness": self.base.roughness_factor,
            "specular": self.specular.factor,
            "transmission": self.transmission.factor,
            "emissive": self.emissive.factor,
        }