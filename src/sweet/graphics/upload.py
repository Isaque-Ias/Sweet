from __future__ import annotations
from typing import TYPE_CHECKING
from ..core import system
from ..plataform.renderer.render_device import GLContext
from .gl import upload
from dataclasses import dataclass
if TYPE_CHECKING:
    from ..resources.assets.import_data import MeshData

@dataclass
class GPUHandle:
    defined: bool
    key: str

class UploadManager:
    @classmethod
    def upload_mesh(cls, mesh: MeshData) -> GPUHandle:
        if system.state.engine.render == "GLCONTEXT":
            GLContext.use_context()
            handle = upload.GeometryUploader.upload_mesh(mesh)
            defined = True
        else:
            system.warn(f"Upload de mesh falhou para mesh '{mesh.name}'")
            handle = ""
            defined = False

        return GPUHandle(defined=defined, key=handle)