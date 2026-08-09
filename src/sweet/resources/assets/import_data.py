from dataclasses import dataclass, field
from enum import Enum, auto
import numpy as np
from ..common import TRS
from typing import TypeAlias, Optional
from PIL import Image

@dataclass
class BufferData:
    dim_type: str
    data_type: str
    count: int
    data: np.ndarray

class AlphaMode(Enum):
    OPAQUE = auto()
    BLEND = auto()
    MASK = auto()

@dataclass
class TextureTransform:
    offset: list[float] = field(default_factory=lambda: [0.0, 0.0])
    scale: list[float] = field(default_factory=lambda: [1.0, 1.0])
    rotation: float = 0.0

@dataclass
class TextureChannelBinding:
    texture_index: int
    tex_coord: int = 0
    transform: Optional[TextureTransform] = None

@dataclass
class PBRCharacteristics:
    base_color_factor: list[float] = field(default_factory=lambda: [1.0, 1.0, 1.0, 1.0])
    metallic_factor: float = 1.0
    roughness_factor: float = 1.0
    base_color_texture: Optional[TextureChannelBinding] = None
    metallic_roughness_texture: Optional[TextureChannelBinding] = None
    specular_factor: float = 1.0
    specular_color_factor: list[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    specular_texture: Optional[TextureChannelBinding] = None

@dataclass
class StructuralTexture:
    binding: TextureChannelBinding
    explanation: str
    scalar_modifier: float = 1.0

@dataclass
class EmissiveCharacteristics:
    factor: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    texture: Optional[TextureChannelBinding] = None

@dataclass
class StructuralParameters:
    normal: Optional[StructuralTexture] = None
    occlusion: Optional[StructuralTexture] = None
    emissive: EmissiveCharacteristics = field(default_factory=EmissiveCharacteristics)

@dataclass
class MaterialData:
    name: str = "[Material sem nome]"
    alpha_cutoff: float = 0
    alpha_mode: AlphaMode = AlphaMode.OPAQUE
    double_sided: bool = False
    
    texture_coordinate_map: dict[int, list[int]] = field(default_factory=dict[int, list[int]])
    
    pbr_characteristics: PBRCharacteristics = field(default_factory=PBRCharacteristics)
    structural_parameters: StructuralParameters = field(default_factory=StructuralParameters)

@dataclass
class PrimitiveData:
    positions: BufferData | None
    normals: BufferData | None
    tangents: BufferData | None
    texcoord_0: BufferData | None
    texcoord_1: BufferData | None
    colors: BufferData | None
    joints: BufferData | None
    weights: BufferData | None
    indices: BufferData | None
    # targets: list[float] | None
    mode: int
    material: int | None
    aabb: list[float]

@dataclass
class MeshData:
    aabb: list[float]
    primitives: list[PrimitiveData] = field(default_factory=lambda: [])
    name: str = "[Modelo sem nome]"

@dataclass
class Perspective:
    fov: float = 70.0
    aspect: float = 16 / 9
    near: float = .1
    far: float = 1000.0

@dataclass
class Orthographic:
    xmag: float = 1.0
    ymag: float = 1.0
    near: float = .1
    far: float = 1000.0

Projection: TypeAlias = Perspective | Orthographic

class CameraMode(Enum):
    ORTHOGRAPHIC = auto()
    PERSPECTIVE = auto()

@dataclass
class CameraData:
    camera_mode: CameraMode = field(default_factory=lambda: CameraMode.PERSPECTIVE)
    projection: Projection = field(default_factory=lambda: Perspective())
    name: str = "[Camera sem nome]"

@dataclass
class TextureData:
    source: Image.Image
    width: int
    height: int
    components: int
    name: str = "[Textura sem nome]"

@dataclass
class NodeData:
    mesh: int | None
    skin: int | None
    camera: CameraData | None
    children: list["NodeData"]
    trs: TRS
    name: str = "[Nó sem nome]"

@dataclass
class SceneData:
    nodes: list[NodeData] = field(default_factory=lambda: [])
    meshes: dict[int, MeshData] = field(default_factory=lambda: {})
    textures: dict[int, TextureData] = field(default_factory=lambda: {})
    materials: dict[int, MaterialData] = field(default_factory=lambda: {})
    name: str = "[Cena sem nome]"

@dataclass
class ShaderData:
    vertex: str
    fragment: str

@dataclass
class ComputeData:
    src: str

@dataclass
class AssetData:
    textures: dict[str, TextureData]
    meshes: dict[str, MeshData]
    materials: dict[str, MaterialData]