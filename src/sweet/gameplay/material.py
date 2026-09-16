from abc import ABC, abstractmethod
from typing import Optional
from ..resources.assets.import_data import AlphaMode
from ..graphics.upload import GPUTexture, GPUMaterial
from dataclasses import dataclass, field

class Material(ABC):
    @property
    @abstractmethod
    def alpha_mode(self) -> AlphaMode:
        pass

    @property
    @abstractmethod
    def source_material(self) -> GPUMaterial:
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
    def __init__(self):
        self._alpha_mode = AlphaMode.OPAQUE
        
        self.base = PBRBaseLayer()
        self.specular = PBRSpecularLayer()
        self.emissive = PBREmissiveLayer()
        self.orm = None
        self.specular = None
        self._material_id = None
        
    @property
    def alpha_mode(self) -> AlphaMode:
        return self._alpha_mode

    @alpha_mode.setter
    def alpha_mode(self, alpha_mode: AlphaMode) -> None:
        self._alpha_mode = alpha_mode

    @property
    def source_material(self) -> GPUMaterial:
        return self._material_id # type: ignore