import io
from pathlib import Path
from ...core import system
import trimesh
from pygltflib import GLTF2
from pygltflib import Node as GLBNode
from pygltflib import Scene as GLBScene
from pygltflib import TextureInfo as GLBTextureInfo
from pygltflib import OcclusionTextureInfo as GLBOcclusionTextureInfo
from pygltflib import NormalMaterialTexture as GLBNormalMaterialTexture
from ..common import TRS
from ...core.linalg.vector import Vec3
from ...core.linalg.rotation import QuaternionAngle
import math
from typing import cast, Callable, Any, Optional, Sequence
from .import_data import *
import numpy as np
from PIL import Image
from PIL.Image import Transpose

class ImportManager:
    _model_formats = [".glb", ".obj"]
    _texture_formats = [".glb", ".png", ".jpeg"]
    _scene_formats = [".glb"]

    _ALPHA_MODE_MAP: dict[str, AlphaMode] = {
        "BLEND": AlphaMode.BLEND,
        "MASK": AlphaMode.MASK,
        "OPAQUE": AlphaMode.OPAQUE,
    }
    
    _COMPONENT_TYPE_MAP: dict[int, tuple[str, type[np.generic]]] = {
            5120: ("BYTE", np.int8),
            5121: ("UNSIGNED_BYTE", np.uint8),
            5122: ("SHORT", np.int16),
            5123: ("UNSIGNED_SHORT", np.uint16),
            5125: ("UNSIGNED_INT", np.uint32),
            5126: ("FLOAT", np.float32),
    }
    
    _TYPE_COUNTS_MAP = {
        "SCALAR": 1,
        "VEC2": 2,
        "VEC3": 3,
        "VEC4": 4,
        "MAT2": 4,
        "MAT3": 9,
        "MAT4": 16,
    }

    _TARGET_MAP: dict[int, str] = {
        34962: "ARRAY_BUFFER",
        34963: "ELEMENT_ARRAY_BUFFER"
    }

    @staticmethod
    def load_compute_shaders(path: str | Path) -> ComputeData:
        solved_path = system.solve_path(path)
        with open(solved_path, "r") as file:
            shader = file.read()

        shader_data = ComputeData(src=shader)
        return shader_data

    @staticmethod
    def load_shaders(path_vertex: str | Path, path_fragment: str | Path, path_geometry: Optional[str | Path]=None) -> ShaderData:
        absolute_vertex = system.solve_path(path_vertex)
        absolute_fragment = system.solve_path(path_fragment)
        
        with open(absolute_vertex, "r") as file:
            VERTEX_SHADER = file.read()
        with open(absolute_fragment, "r") as file:
            FRAGMENT_SHADER = file.read()

        geometry_shader = None
        if not path_geometry is None:
            absolute_geometry = system.solve_path(path_geometry)
            with open(absolute_geometry, "r") as file:
                geometry_shader = file.read()

        shader_data = ShaderData(
            vertex=VERTEX_SHADER,
            fragment=FRAGMENT_SHADER,
            geometry=geometry_shader
        )
        return shader_data

    @staticmethod
    def get_model_fallback():
        config = system.state.env.resources.importing.fallback_model
        if config == "__default__":
            BASE = Path(__file__).parent
            fallback_path = BASE.parent / "build" / "__fallback__.obj"
        else:
            fallback_path = system.solve_path(config)
            if not fallback_path.exists():
                raise FileNotFoundError(f"Modelo de fallback não encontrada em: {fallback_path}")

        return fallback_path

    @classmethod
    def _model_validation(cls, path: str | Path, command: Callable[..., Any]) -> Any:
        solved_path = system.solve_path(path)
        file_format = solved_path.suffix

        if not file_format in cls._model_formats:
            system.warn(f"Não há suporte para formato fornecido: {file_format} em {solved_path}")
            solved_path = cls.get_model_fallback()
            file_format = solved_path.suffix

        if not solved_path.exists():
            system.warn(f"Modelo não encontrado no caminho: {solved_path}")
            solved_path = cls.get_model_fallback()
            file_format = solved_path.suffix

        
        result = command(solved_path, file_format)
        return result

    @classmethod
    def _min_max_to_center(cls, aabb: Sequence[float]) -> list[float]:
        center: list[float] = [
            (aabb[0] + aabb[3]) / 2,
            (aabb[1] + aabb[4]) / 2,
            (aabb[2] + aabb[5]) / 2,
        ]
        half_extent: list[float] = [
            (aabb[3] + aabb[0]) / 2,
            (aabb[4] + aabb[1]) / 2,
            (aabb[5] + aabb[2]) / 2,
        ]
        return center + half_extent

    @classmethod
    def _load_obj_model(cls, path: Path, material_id: int | None = None) -> PrimitiveData:
        mesh = trimesh.load(path, force='mesh') # type: ignore
        positions = mesh.vertices.flatten().tolist() # type: ignore
        indices = mesh.faces.flatten().tolist() # type: ignore
        
        normals = mesh.vertex_normals.flatten().tolist() if hasattr(mesh, 'vertex_normals') else None # type: ignore
        
        texcoord_0 = None
        if hasattr(mesh.visual, 'uv') and mesh.visual.uv is not None: # type: ignore
            texcoord_0 = mesh.visual.uv.flatten().tolist() # type: ignore
            
        colors = None
        if hasattr(mesh.visual, 'vertex_colors') and mesh.visual.vertex_colors is not None: # type: ignore
            colors = mesh.visual.vertex_colors.flatten().tolist() # type: ignore

        aabb_np = mesh.bounds.tolist() if hasattr(mesh, 'bounds') else [[0, 0, 0], [0, 0, 0]]
        aabb = cls._min_max_to_center(aabb_np[0] + aabb_np[1])
        
        return PrimitiveData(
            positions=BufferData(positions), # type: ignore
            normals=BufferData(normals) if normals else None, # type: ignore
            tangents=None,
            texcoord_0=BufferData(texcoord_0) if texcoord_0 else None, # type: ignore
            texcoord_1=None,
            colors=BufferData(colors) if colors else None, # type: ignore
            joints=None,
            weights=None,
            indices=BufferData(indices), # type: ignore
            mode=4,
            material=material_id,
            aabb=aabb
        )

    @classmethod
    def _load_png_texture(cls, path: Path) -> TextureData:
        with Image.open(path) as img:
            width, height = img.size
            
            if img.mode in ('RGBA', 'LA', 'P'):
                target_mode = 'RGBA'
                components = 4
            else:
                target_mode = 'RGB'
                components = 3
                
            converted_img = img.convert(target_mode)
            
            return TextureData(
                source=converted_img,
                width=width,
                height=height,
                components=components,
                name="[Textura sem nome]"
            )
    
    @classmethod
    def load_model(cls, path: str | Path, query: Optional[str]=None) -> Optional[MeshData]:
        def command(solved_path: Path, file_format: str) -> Optional[MeshData]:
            if file_format == ".glb":
                content = GLTF2().load(solved_path) # type: ignore
                if not content is None:
                    first_candidate: Optional[MeshData] = None
                    
                    for node in content.nodes:
                        if not node.mesh is None:
                            mesh_data = cls._get_mesh(node, content)
                            if query is None:
                                return mesh_data
                            if first_candidate is None:
                                first_candidate = mesh_data
                            if mesh_data.name == query or node.name == query:
                                return mesh_data

                    return first_candidate
                else:
                    system.warn(f"Conteúdo de {solved_path} é vazio")
                    
                    return None

            elif file_format == ".obj":
                primitive = cls._load_obj_model(solved_path)
                return MeshData(
                    aabb=primitive.aabb,
                    primitives=[primitive],
                    name=solved_path.stem
                )

            else:
                system.warn(f"Formato de modelo não suportado para arquivo em '{solved_path}'. Tente usar: {cls._model_formats}")
                return None

        final_model = cls._model_validation(path, command)
        return final_model
    
    @classmethod
    def load_models(cls, path: str | Path) -> Optional[MeshData]:
        def command(solved_path: Path, content: Any) -> dict[str, MeshData]:
            if not content is None:
                mesh_set: dict[str, MeshData] = {}

                for node in content.nodes:
                    if (not node.mesh is None):
                        mesh_data = cls._get_mesh(node, content)
                        mesh_set[mesh_data.name] = mesh_data
                        
                return mesh_set
            else:
                system.warn(f"Conteúdo de {solved_path} é vazio")
                return {}

        final_models = cls._model_validation(path, command)
        return final_models

    @staticmethod
    def _matrix_to_trs(node: GLBNode) -> TRS:
        m = node.matrix
        if m is None or len(m) != 16:
            trs = TRS(
                position=Vec3.from_iter(node.translation or [0, 0, 0]),
                rotation=QuaternionAngle(),
                scale=Vec3.from_iter(node.scale or [1, 1, 1]),
            )

            return trs
        tx, ty, tz = m[12], m[13], m[14]

        sx = math.sqrt(m[0]*m[0] + m[1]*m[1] + m[2]*m[2])
        sy = math.sqrt(m[4]*m[4] + m[5]*m[5] + m[6]*m[6])
        sz = math.sqrt(m[8]*m[8] + m[9]*m[9] + m[10]*m[10])

        r00 = m[0] / sx if sx != 0.0 else 0.0
        r10 = m[1] / sx if sx != 0.0 else 0.0
        r20 = m[2] / sx if sx != 0.0 else 0.0

        r01 = m[4] / sy if sy != 0.0 else 0.0
        r11 = m[5] / sy if sy != 0.0 else 0.0
        r21 = m[6] / sy if sy != 0.0 else 0.0

        r02 = m[8] / sz if sz != 0.0 else 0.0
        r12 = m[9] / sz if sz != 0.0 else 0.0
        r22 = m[10] / sz if sz != 0.0 else 0.0
        
        trace = r00 + r11 + r22

        if trace > 0.0:
            s_quat = math.sqrt(trace + 1.0) * 2.0
            qw = 0.25 * s_quat
            qx = (r21 - r12) / s_quat
            qy = (r02 - r20) / s_quat
            qz = (r10 - r01) / s_quat
        elif (r00 > r11) and (r00 > r22):
            s_quat = math.sqrt(1.0 + r00 - r11 - r22) * 2.0
            qw = (r21 - r12) / s_quat
            qx = 0.25 * s_quat
            qy = (r01 + r10) / s_quat
            qz = (r02 + r20) / s_quat
        elif r11 > r22:
            s_quat = math.sqrt(1.0 + r11 - r00 - r22) * 2.0
            qw = (r02 - r20) / s_quat
            qx = (r01 + r10) / s_quat
            qy = 0.25 * s_quat
            qz = (r12 + r21) / s_quat
        else:
            s_quat = math.sqrt(1.0 + r22 - r00 - r11) * 2.0
            qw = (r10 - r01) / s_quat
            qx = (r02 + r20) / s_quat
            qy = (r12 + r21) / s_quat
            qz = 0.25 * s_quat

        trs = TRS(
            position=Vec3(tx, ty, tz),
            rotation=QuaternionAngle(qx, qy, qz, qw),
            scale=Vec3(sx, sy, sz)
        )
        return trs

    @staticmethod
    def _trs_to_matrix(node: GLBNode):
        if node.matrix is not None and len(node.matrix) == 16:
            return [float(x) for x in node.matrix]
            
        t = node.translation if node.translation else (0.0, 0.0, 0.0)
        r = node.rotation if node.rotation else (0.0, 0.0, 0.0, 1.0)
        s = node.scale if node.scale else (1.0, 1.0, 1.0)
        
        qx, qy, qz, qw = r
        sx, sy, sz = s
        
        x2, y2, z2 = qx + qx, qy + qy, qz + qz
        xx, xy, xz = qx * x2, qx * y2, qx * z2
        yy, yz, zz = qy * y2, qy * z2, qz * z2
        wx, wy, wz = qw * x2, qw * y2, qw * z2
        
        return [
            (1.0 - (yy + zz)) * sx, (xy + wz) * sx,        (xz - wy) * sx,        0.0,
            (xy - wz) * sy,        (1.0 - (xx + zz)) * sy, (yz + wx) * sy,        0.0,
            (xz + wy) * sz,        (yz - wx) * sz,        (1.0 - (xx + yy)) * sz, 0.0,
            t[0],                  t[1],                  t[2],                  1.0
        ]

    @classmethod
    def _node_hierarchy(cls, node_ids: list[int], nodes: list[GLBNode], content: GLTF2) -> tuple[list[NodeData], list[int]]:
        node_hierarchy: list[NodeData] = []
        flat_nodes: list[int] = []

        for node_id in node_ids:
            glb_node = nodes[node_id]
            name = glb_node.name or "[Sem nome]"
            glb_children = glb_node.children or []
            flat_nodes.append(node_id)
            
            children, flat = cls._node_hierarchy(glb_children, nodes, content)
            flat_nodes.extend(flat)

            trs = cls._matrix_to_trs(glb_node)

            camera = None
            if not glb_node.camera is None:
                camera = cls._get_camera(glb_node, content)

            # lights = gltf.extensions["KHR_lights_punctual"]["lights"]
            
            node = NodeData(
                name=name,
                mesh=glb_node.mesh,
                skin=glb_node.skin,
                camera=camera,
                children=children,
                trs=trs
            )

            node_hierarchy.append(node)
            
        return node_hierarchy, flat_nodes

    @classmethod
    def _access_data(cls, index: int | None, content: GLTF2) -> BufferData | None:
        if index == None:
            return
        
        accessor = content.accessors[index]

        buffer_view = content.bufferViews[accessor.bufferView or 0]
        
        raw_blob = cast(bytearray, content.binary_blob()) if content.binary_blob() else b""
            
        view_start = buffer_view.byteOffset or 0
        accessor_offset = accessor.byteOffset or 0

        name, dtype = cls._COMPONENT_TYPE_MAP[accessor.componentType]
        num_components = cls._TYPE_COUNTS_MAP[accessor.type]

        absolute_start = view_start + accessor_offset
        # view_length = buffer_view.byteLength or 0
        element_size = num_components * np.dtype(dtype).itemsize
        stride = buffer_view.byteStride or 0 if buffer_view.byteStride else element_size

        accessor_byte_length = (accessor.count - 1) * stride + element_size
        
        accessor_bytes = raw_blob[absolute_start : absolute_start + accessor_byte_length]

        np_dtype = np.dtype(dtype).newbyteorder('<')
        array = np.frombuffer(accessor_bytes, dtype=np_dtype)
        
        if stride != element_size:
            row_items = stride // np.dtype(dtype).itemsize
            array = array.reshape(accessor.count, row_items)[:, :num_components]
        else:
            if accessor.type != "SCALAR":
                array = array.reshape(accessor.count, num_components)

        return BufferData(accessor.type, name, array.shape[0], array)

    @classmethod
    def _image_data(cls, index: int | None, content: GLTF2) -> bytearray | None:
        if index is None:
            return

        buffer_view = content.bufferViews[index]

        raw_blob = content.binary_blob() if content.binary_blob() else None
            
        view_start = buffer_view.byteOffset or 0
    
        absolute_start = view_start
        view_length = buffer_view.byteLength or 0
        
        buffer_bytes = cast(bytearray, raw_blob[absolute_start : absolute_start + view_length]) # type: ignore
    
        return buffer_bytes

    @classmethod
    def _get_texture(cls, index: int, content: GLTF2) -> TextureData:
        source = content.images[index]
        raw_bytes = cls._image_data(source.bufferView, content)
        if raw_bytes is None: raw_bytes = bytearray()

        pil_img = Image.open(io.BytesIO(raw_bytes))

        if pil_img.mode in ('RGBA', 'LA', 'P'):
            target_mode = 'RGBA'
            components = 4
        else:
            target_mode = 'RGB'
            components = 3

        pil_img = pil_img.convert(target_mode)
        
        pil_img = pil_img.transpose(Transpose.FLIP_TOP_BOTTOM)
        
        width, height = pil_img.size
        
        final_image = TextureData(
            source=pil_img,
            width=width,
            height=height,
            components=components,
            name="[Textura sem nome]"
        )
        return final_image

    @classmethod
    def _process_binding(cls, texture_info: GLBTextureInfo | GLBOcclusionTextureInfo | GLBNormalMaterialTexture | None, local_uv_map: dict[int, list[int]]) -> Optional[TextureChannelBinding]:
        if texture_info is None:
            return None
        
        idx = texture_info.index or 0
        coord = texture_info.texCoord or 0
        
        if coord not in local_uv_map:
            local_uv_map[coord] = []
        if idx not in local_uv_map[coord]:
            local_uv_map[coord].append(idx)
        
        transform_obj = None
        if hasattr(texture_info, "extensions") and texture_info.extensions:
            ext_transform = texture_info.extensions.get("KHR_texture_transform")
            if ext_transform:
                transform_obj = TextureTransform(
                    offset=ext_transform.get("offset", [0.0, 0.0]),
                    scale=ext_transform.get("scale", [1.0, 1.0]),
                    rotation=ext_transform.get("rotation", 0.0)
                )
        
        return TextureChannelBinding(texture_index=idx or 0, tex_coord=coord or 0, transform=transform_obj)

    @classmethod
    def _get_material(cls, index: int, content: GLTF2) -> MaterialData:
        material = content.materials[index]
        
        local_uv_map: dict[int, list[int]] = {}

        resolved_alpha_mode = cls._ALPHA_MODE_MAP.get(material.alphaMode or "", AlphaMode.OPAQUE)
        resolved_cutoff = material.alphaCutoff if material.alphaCutoff is not None else 0.0

        pbr_struct = PBRCharacteristics()
        if material.pbrMetallicRoughness:
            pbr = material.pbrMetallicRoughness
            pbr_struct.base_color_factor = pbr.baseColorFactor or [1.0, 1.0, 1.0, 1.0]
            pbr_struct.metallic_factor = pbr.metallicFactor or 1
            pbr_struct.roughness_factor = pbr.roughnessFactor or 1
            pbr_struct.base_color_texture = cls._process_binding(pbr.baseColorTexture, local_uv_map)
            pbr_struct.metallic_roughness_texture = cls._process_binding(pbr.metallicRoughnessTexture, local_uv_map)

        if material.extensions and "KHR_materials_specular" in material.extensions:
            spec = material.extensions["KHR_materials_specular"]
            pbr_struct.specular_factor = spec.get("specularFactor", 1.0)
            pbr_struct.specular_color_factor = spec.get("specularColorFactor", [1.0, 1.0, 1.0])
            pbr_struct.specular_texture = cls._process_binding(spec.get("specularTexture"), local_uv_map)

        structural_struct = StructuralParameters()
        
        if material.normalTexture:
            binding = cls._process_binding(material.normalTexture, local_uv_map)
            if binding:
                structural_struct.normal = StructuralTexture(
                    binding=binding,
                    explanation="Modulates surface vectors to simulate fine geometric detail using RGB vectors.",
                    scalar_modifier=getattr(material.normalTexture, "scale", 1.0)
                )

        if material.occlusionTexture:
            material.occlusionTexture.index
            binding = cls._process_binding(material.occlusionTexture, local_uv_map)
            if binding:
                structural_struct.occlusion = StructuralTexture(
                    binding=binding,
                    explanation="Grayscale map (Red channel) specifying ambient shading in recessed micro-areas.",
                    scalar_modifier=getattr(material.occlusionTexture, "strength", 1.0)
                )

        structural_struct.emissive = EmissiveCharacteristics(
            factor=material.emissiveFactor or [0, 0, 0],
            texture=cls._process_binding(material.emissiveTexture, local_uv_map)
        )

        material_data = MaterialData(
            name=material.name or "[Material sem nome]",
            alpha_cutoff=resolved_cutoff,
            alpha_mode=resolved_alpha_mode,
            double_sided=bool(material.doubleSided),
            texture_coordinate_map=local_uv_map,
            pbr_characteristics=pbr_struct,
            structural_parameters=structural_struct
        )
        
        return material_data

    @classmethod
    def _get_mesh(cls, node: GLBNode | NodeData, content: GLTF2) -> MeshData:
        mesh = content.meshes[node.mesh or 0]
        primitives: list[PrimitiveData] = []
        mesh_min: list[float] = []
        mesh_max: list[float] = []
        for primitive in mesh.primitives:
            primitive = mesh.primitives[0]

            pos_id = int(primitive.attributes.POSITION) # type: ignore

            positions = cls._access_data(pos_id, content) # type: ignore
            normals = cls._access_data(primitive.attributes.NORMAL, content) # type: ignore
            tangents = cls._access_data(primitive.attributes.TANGENT, content) # type: ignore
            textures_0 = cls._access_data(primitive.attributes.TEXCOORD_0, content) # type: ignore
            textures_1 = cls._access_data(primitive.attributes.TEXCOORD_1, content) # type: ignore
            colors = cls._access_data(primitive.attributes.COLOR_0, content) # type: ignore
            joints = cls._access_data(primitive.attributes.JOINTS_0, content) # type: ignore
            weights = cls._access_data(primitive.attributes.WEIGHTS_0, content) # type: ignore
            indices = cls._access_data(primitive.indices, content)
            mode = primitive.mode or 4
            material = primitive.material
            # target = primitive.targets

            min_aabb = content.accessors[pos_id].min or [0, 0, 0]
            max_aabb = content.accessors[pos_id].max or [0, 0, 0]

            if not mesh_min: mesh_min = min_aabb.copy()
            if not mesh_max: mesh_max = min_aabb.copy()

            for i in range(len(mesh_min)):
                if mesh_min[i] > min_aabb[i]:
                    mesh_min[i] = min_aabb[i]
            for i in range(len(mesh_max)):
                if mesh_max[i] < max_aabb[i]:
                    mesh_max[i] = max_aabb[i]
            
            aabb = min_aabb + max_aabb
            
            primitive_data = PrimitiveData(
                positions=positions,
                normals=normals,
                tangents=tangents,
                texcoord_0=textures_0,
                texcoord_1=textures_1,
                colors=colors,
                joints=joints,
                weights=weights,
                indices=indices,
                mode=mode,
                material=material,
                aabb=aabb
            )
            primitives.append(primitive_data)

        mesh_aabb = cls._min_max_to_center(mesh_min + mesh_max)

        mesh_data = MeshData(
            primitives=primitives,
            aabb=mesh_aabb,
            name=node.name or "[Sem nome]"
        )

        return mesh_data

    @classmethod
    def _get_camera(cls, node: GLBNode, content: GLTF2) -> CameraData:
        camera = content.cameras[node.camera or 0]

        mode = None
        projection = None
        if camera.type == "orthographic" and camera.orthographic:
            mode = CameraMode.ORTHOGRAPHIC
            ortho = camera.orthographic
            projection = Orthographic(
                ortho.xmag or 1.0,
                ortho.ymag or 1.0,
                ortho.znear or .1,
                ortho.zfar or 1000.0,
            )
        elif camera.type == "perspective" and camera.perspective:
            mode = CameraMode.PERSPECTIVE
            perspec = camera.perspective
            projection = Perspective(
                perspec.yfov or 70.0,
                perspec.aspectRatio or 16 / 9,
                perspec.znear or .1,
                perspec.zfar or 1000.0,
            )

        if not mode is None and not projection is None:
            camera_data = CameraData(camera_mode=mode, projection=projection, name=node.name or "[Sem nome]")
        else:
            camera_data = CameraData(name=node.name or "[Sem nome]")

        return camera_data

    @classmethod
    def _get_mesh_list(cls, node_ids: list[int], content: GLTF2) -> tuple[dict[int, MeshData], list[MeshData]]:
        mesh_data: dict[int, MeshData] = {}
        mesh_list: list[MeshData] = []
        
        for node_id in node_ids:
            node = content.nodes[node_id]
            if (not node.mesh is None) and mesh_data.get(node.mesh) is None:
                mesh = cls._get_mesh(node, content)
                mesh_data[node.mesh] = mesh
                mesh_list.append(mesh)

        return mesh_data, mesh_list

    @classmethod
    def _get_material_list(cls, meshes: list[MeshData], content: GLTF2) -> tuple[dict[int, MaterialData], list[MaterialData]]:
        material_data: dict[int, MaterialData] = {}
        material_list: list[MaterialData] = []
        for mesh in meshes:
            for primitive in mesh.primitives:
                if (not primitive.material is None) and material_data.get(primitive.material) is None:
                    material = cls._get_material(primitive.material, content)
                    material_data[primitive.material] = material
                    material_list.append(material)
            
        return material_data, material_list

    @classmethod
    def _get_texture_list(cls, materials: list[MaterialData], content: GLTF2) -> dict[int, TextureData]:
        texture_data: dict[int, TextureData] = {}
        for material in materials:
            for textures in material.texture_coordinate_map.values():
                for texture_id in textures:
                    if texture_data.get(texture_id) is None:
                        texture = cls._get_texture(texture_id, content)
                        texture_data[texture_id] = texture

        return texture_data

    @classmethod
    def _create_scene(cls, glbscene: GLBScene, content: GLTF2) -> SceneData:
        name = glbscene.name or "[Sem nome]"
        glb_nodes = glbscene.nodes or []

        node_data, flat_nodes = cls._node_hierarchy(glb_nodes, content.nodes, content)
        mesh_data, flat_mesh = cls._get_mesh_list(flat_nodes, content)
        material_data, flat_material = cls._get_material_list(flat_mesh, content)
        texture_data = cls._get_texture_list(flat_material, content)

        scene = SceneData(
            meshes=mesh_data,
            textures=texture_data,
            materials=material_data,
            nodes=node_data,
            name=name
        )
        return scene

    @classmethod
    def _scene_validation(cls, path: str | Path, command: Callable[..., Any]) -> Any:
        solved_path = system.solve_path(path)
        file_format = solved_path.suffix

        fallback_scene = SceneData()

        if not file_format in cls._scene_formats:
            system.warn(f"Não há suporte para formato fornecido: {file_format} em {solved_path}")
            return fallback_scene

        if not solved_path.exists():
            system.warn(f"Modelo não encontrado no caminho: {solved_path}")
            return fallback_scene

        if file_format == ".glb":
            content = GLTF2().load(solved_path) # type: ignore
            result = command(solved_path, content)
            return result
            
        return fallback_scene

    @classmethod
    def load_scene(cls, path: str | Path) -> SceneData:
        def command(solved_path: Path, content: GLTF2 | None):
            fallback_scene = SceneData()

            if not content is None:
                main_scene = content.scene or 0
                default_scene = content.scenes[main_scene]
                
                scene = cls._create_scene(default_scene, content)
                return scene
            else:
                system.warn(f"Conteúdo de {solved_path} é vazio")
                return fallback_scene

        final_scene = cls._scene_validation(path, command)
        return final_scene

    @classmethod
    def load_scenes(cls, path: str | Path) -> dict[str, SceneData]:
        def command(solved_path: Path, content: GLTF2 | None):
            fallback_scene = SceneData()

            if not content is None:
                scene_set: dict[str, SceneData] = {}
                for scene in content.scenes:
                    scene_data = cls._create_scene(scene, content)
                    scene_set[scene_data.name] = scene_data

                return scene_set

            else:
                system.warn(f"Conteúdo de {solved_path} é vazio")
                return {"fallback": fallback_scene}

        final_scenes = cls._scene_validation(path, command)
        return final_scenes

    @classmethod
    def _texture_validation(cls, path: str | Path, command: Callable[..., Any]) -> Any:
        solved_path = system.solve_path(path)
        file_format = solved_path.suffix

        if not file_format in cls._texture_formats:
            system.warn(f"Não há suporte para formato fornecido: {file_format} em {solved_path}")
            solved_path = cls.get_model_fallback()
            file_format = solved_path.suffix

        if not solved_path.exists():
            system.warn(f"Modelo não encontrado no caminho: {solved_path}")
            solved_path = cls.get_model_fallback()
            file_format = solved_path.suffix

        final_texture = command(solved_path, file_format)
        return final_texture

    @classmethod
    def load_texture(cls, path: str | Path, query: Optional[str] = None) -> Optional[TextureData]:
        def command(solved_path: Path, file_format: str) -> Optional[TextureData]:
            if file_format == ".glb":
                content = GLTF2().load(solved_path) # type: ignore
                if not content is None:
                    first_candidate: Optional[TextureData] = None

                    for index in range(len(content.textures)):
                        texture_data = cls._get_texture(index, content)
                        if query is None:
                            return texture_data
                        if first_candidate is None:
                            first_candidate = texture_data
                        if texture_data.name == query:
                            return texture_data

                    return first_candidate
                else:
                    system.warn(f"Conteúdo de {solved_path} é vazio")
                    
                    return None

            elif file_format in (".png", ".jpeg"):
                return cls._load_png_texture(solved_path)

            else:
                system.warn(f"Formato de modelo não suportado para arquivo em '{solved_path}'. Tente usar: {cls._model_formats}")
                return None

        final_textures = cls._texture_validation(path, command)
        return final_textures

    @classmethod
    def load_textures(cls, path: str | Path) -> dict[str, TextureData]:
        def command(solved_path: Path, file_format: str) -> dict[str, TextureData]:
            if file_format == ".glb":
                content = GLTF2().load(solved_path) # type: ignore
                if content == None:
                    return {}

                texture_set: dict[str, TextureData] = {}
                for index in range(len(content.textures)):
                    texture_data = cls._get_texture(index, content)
                    texture_set[texture_data.name] = texture_data

                return texture_set

            elif file_format in (".png", ".jpeg"):
                textures: dict[str, TextureData] = {}
                texture = cls._load_png_texture(solved_path)
                textures[texture.name] = texture
                return textures

            else:
                system.warn(f"Formato de modelo não suportado para arquivo em '{solved_path}'. Tente usar: {cls._model_formats}")
                return {}

        final_textures = cls._texture_validation(path, command)
        return final_textures

    @classmethod
    def load_assets(cls, path: str | Path) -> AssetData:
        def command(solved_path: Path, content: GLTF2 | None) -> AssetData:
            if not content is None:
                texture_set: dict[str, TextureData] = {}
                for index in range(len(content.textures)):
                    texture_data = cls._get_texture(index, content)
                    texture_set[texture_data.name] = texture_data
                    
                mesh_set: dict[str, MeshData] = {}
                for node in content.nodes:
                    if (not node.mesh is None):
                        mesh_data = cls._get_mesh(node, content)
                        mesh_set[mesh_data.name] = mesh_data
                    
                material_set: dict[str, MaterialData] = {}
                for index in range(len(content.materials)):
                    material_data = cls._get_material(index, content)
                    material_set[material_data.name] = material_data
                
                asset_data = AssetData(
                    textures=texture_set,
                    meshes=mesh_set,
                    materials=material_set
                )
                return asset_data

            else:
                system.warn(f"Conteúdo de {solved_path} é vazio")
                fallback_asset = AssetData(
                    textures={},
                    meshes={},
                    materials={}
                )
                return fallback_asset

        final_asset = cls._scene_validation(path, command)
        return final_asset