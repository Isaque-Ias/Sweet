from dataclasses import dataclass
from ..common import MeshBuffer, TextureBuffer
from typing import Any

@dataclass
class Attribute:
    name: str
    location: int
    size: int
    type_name: int
    length: int

@dataclass
class DataBlock:
    name: str
    binding: int
    size: int
    members: list[Attribute]

@dataclass
class Introspection:
    geometry_layout: list[Attribute]
    instance_layout: list[Attribute]
    uniforms: list[Attribute]
    ubos: list[DataBlock]
    ssbos: list[DataBlock]

@dataclass
class DrawCall:
    mesh_handle: MeshBuffer
    texture_handle: TextureBuffer
    shader_handle: str
    parameters: dict[str, Any]