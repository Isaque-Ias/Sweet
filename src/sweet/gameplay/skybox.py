from __future__ import annotations
from enum import Enum, auto
from typing import Any, Optional, TYPE_CHECKING
from ..graphics.render.process import PipelineManager
from .view import View
from ..plataform.hal.manager import GraphicsDevice
import glm
if TYPE_CHECKING:
    from .scene import Scene

graphics_device: GraphicsDevice

class SkyBoxType(Enum):
    NISHITA = auto()

def cubemap_view_projection(position: Optional[glm.vec3] = None, near_plane: float=0.1, far_plane: float=100.0):
    if position is None:
        position = glm.vec3([0, 0, 0])
        
    projection = glm.perspective(glm.radians(90.0), 1.0, near_plane, far_plane) # type: ignore

    views = [
        # +X
        glm.lookAt(position, position + glm.vec3(1.0, 0.0, 0.0), glm.vec3(0.0, -1.0, 0.0)), # type: ignore
        # -X
        glm.lookAt(position, position + glm.vec3(-1.0, 0.0, 0.0), glm.vec3(0.0, -1.0, 0.0)), # type: ignore
        # +Y
        glm.lookAt(position, position + glm.vec3(0.0, 1.0, 0.0), glm.vec3(0.0, 0.0, 1.0)), # type: ignore
        # -Y
        glm.lookAt(position, position + glm.vec3(0.0, -1.0, 0.0), glm.vec3(0.0, 0.0, -1.0)), # type: ignore
        # +Z
        glm.lookAt(position, position + glm.vec3(0.0, 0.0, 1.0), glm.vec3(0.0, -1.0, 0.0)), # type: ignore
        # -Z
        glm.lookAt(position, position + glm.vec3(0.0, 0.0, -1.0), glm.vec3(0.0, -1.0, 0.0)) # type: ignore
    ]
    
    return views, projection

from PIL import Image
import moderngl

def save_cubemap_to_disk(cubemap_tex: moderngl.TextureCube, prefix: str = "cubemap_face"):
    face_names = ["px", "nx", "py", "ny", "pz", "nz"]
    width, height = cubemap_tex.size

    for i, name in enumerate(face_names):
        raw_data = cubemap_tex.read(face=i)
        
        img = Image.frombytes("RGBA", (width, height), raw_data)
        
        img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        
        img.save(f"{prefix}_{i}_{name}.png")
        print(f"Saved {prefix}_{i}_{name}.png")

class SkyBox:
    def __init__(self, type: SkyBoxType):
        self.type = type
        self.views: list[View] = []
        self.scene: Optional[Scene] = None

        self.resolution = 1024
        self._cubemap = graphics_device.create_cubemap(self.resolution, 4)

        self.target = self._cubemap.get_target()
        
    def update(self, **kwargs: Any):
        # if kwargs["time"]
        if self.scene:
           PipelineManager.process_cubemaps([self], "SkyBox")

        # save_cubemap_to_disk(self._cubemap._cubemap, Path(__file__).parent / "cubemap")