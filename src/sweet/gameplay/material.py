from abc import ABC, abstractmethod
from typing import Optional, Union, Sequence, Any
from ..resources.assets.import_data import *
from ..graphics.upload import GPUMaterial, UploadManager

class Material(ABC):
    def __init__(self, name: str, **kwargs: Any):
        pass

    @property
    @abstractmethod
    def source_material(self) -> GPUMaterial:
        pass

class PBRMaterial(Material):
    def __init__(self, name: str, **kwargs: Any):
        self._source_material = kwargs.get("source", None)
        self.name: str = name
        self.alpha_cutoff: float = 0.0
        self.alpha_mode: AlphaMode = AlphaMode.OPAQUE
        self.double_sided: bool = False

        self.base_color_factor: list[float] = [1.0, 1.0, 1.0, 1.0]
        self.base_color_texture: Optional[TextureChannelBinding] = None

        self.metallic_factor: float = 1.0
        self.roughness_factor: float = 1.0
        self.metallic_roughness_texture: Optional[TextureChannelBinding] = None

        self.specular_factor: float = 1.0
        self.specular_color_factor: list[float] = [1.0, 1.0, 1.0]
        self.specular_texture: Optional[TextureChannelBinding] = None

        self.clearcoat_factor: float = 0.0
        self.clearcoat_roughness_factor: float = 0.0
        self.clearcoat_texture: Optional[TextureChannelBinding] = None
        self.clearcoat_roughness_texture: Optional[TextureChannelBinding] = None

        self.normal_texture: Optional[StructuralTexture] = None
        self.occlusion_texture: Optional[StructuralTexture] = None

        self.emissive_factor: list[float] = [0.0, 0.0, 0.0]
        self.emissive_texture: Optional[TextureChannelBinding] = None

        self.texture_coordinate_map: dict[int, list[int]] = {}

    def _create_binding(
        self,
        texture_input: Union[int, TextureChannelBinding, "TextureData"],
        tex_coord: int = 0,
        transform: Optional[TextureTransform] = None,
    ) -> TextureChannelBinding:
        """Helper to create a TextureChannelBinding regardless of input type."""
        if isinstance(texture_input, TextureChannelBinding):
            return texture_input

        if isinstance(texture_input, int):
            return TextureChannelBinding(
                texture_index=texture_input,
                tex_coord=tex_coord,
                transform=transform,
            )

        return TextureChannelBinding(
            texture_index=-1,
            tex_coord=tex_coord,
            transform=transform,
            texture=texture_input,
        )

    def set_flags(
        self,
        double_sided: Optional[bool] = None,
        alpha_mode: Optional[AlphaMode] = None,
        alpha_cutoff: Optional[float] = None,
    ) -> "PBRMaterial":
        if double_sided is not None:
            self.double_sided = double_sided
        if alpha_mode is not None:
            self.alpha_mode = alpha_mode
        if alpha_cutoff is not None:
            self.alpha_cutoff = alpha_cutoff
        return self

    def set_base_color(
        self,
        factor: Optional[Sequence[float]] = None,
        texture: Optional[Union[int, TextureChannelBinding, "TextureData"]] = None,
        tex_coord: int = 0,
        transform: Optional[TextureTransform] = None,
    ) -> "PBRMaterial":
        if factor is not None:
            self.base_color_factor = list(factor)
        if texture is not None:
            self.base_color_texture = self._create_binding(texture, tex_coord, transform)
        return self

    def set_metallic_roughness(
        self,
        metallic: Optional[float] = None,
        roughness: Optional[float] = None,
        texture: Optional[Union[int, TextureChannelBinding, "TextureData"]] = None,
        tex_coord: int = 0,
        transform: Optional[TextureTransform] = None,
    ) -> "PBRMaterial":
        if metallic is not None:
            self.metallic_factor = metallic
        if roughness is not None:
            self.roughness_factor = roughness
        if texture is not None:
            self.metallic_roughness_texture = self._create_binding(texture, tex_coord, transform)
        return self

    def set_specular(
        self,
        factor: Optional[float] = None,
        color_factor: Optional[Sequence[float]] = None,
        texture: Optional[Union[int, TextureChannelBinding, "TextureData"]] = None,
        tex_coord: int = 0,
    ) -> "PBRMaterial":
        if factor is not None:
            self.specular_factor = factor
        if color_factor is not None:
            self.specular_color_factor = list(color_factor)
        if texture is not None:
            self.specular_texture = self._create_binding(texture, tex_coord)
        return self

    def set_clearcoat(
        self,
        factor: Optional[float] = None,
        roughness_factor: Optional[float] = None,
        clearcoat_texture: Optional[Union[int, TextureChannelBinding, "TextureData"]] = None,
        roughness_texture: Optional[Union[int, TextureChannelBinding, "TextureData"]] = None,
        tex_coord: int = 0,
    ) -> "PBRMaterial":
        if factor is not None:
            self.clearcoat_factor = factor
        if roughness_factor is not None:
            self.clearcoat_roughness_factor = roughness_factor
        if clearcoat_texture is not None:
            self.clearcoat_texture = self._create_binding(clearcoat_texture, tex_coord)
        if roughness_texture is not None:
            self.clearcoat_roughness_texture = self._create_binding(roughness_texture, tex_coord)
        return self

    def set_emissive(
        self,
        factor: Optional[Sequence[float]] = None,
        texture: Optional[Union[int, TextureChannelBinding, "TextureData"]] = None,
        tex_coord: int = 0,
        transform: Optional[TextureTransform] = None,
    ) -> "PBRMaterial":
        if factor is not None:
            self.emissive_factor = list(factor)
        if texture is not None:
            self.emissive_texture = self._create_binding(texture, tex_coord, transform)
        return self

    def set_normal_map(
        self,
        texture: Union[int, TextureChannelBinding, "TextureData"],
        scale: float = 1.0,
        explanation: str = "Normal map",
        tex_coord: int = 0,
    ) -> "PBRMaterial":
        binding = self._create_binding(texture, tex_coord)
        self.normal_texture = StructuralTexture(
            binding=binding,
            explanation=explanation,
            scalar_modifier=scale,
        )
        return self

    def set_occlusion_map(
        self,
        texture: Union[int, TextureChannelBinding, "TextureData"],
        strength: float = 1.0,
        explanation: str = "Ambient Occlusion map",
        tex_coord: int = 0,
    ) -> "PBRMaterial":
        binding = self._create_binding(texture, tex_coord)
        self.occlusion_texture = StructuralTexture(
            binding=binding,
            explanation=explanation,
            scalar_modifier=strength,
        )
        return self

    def build(self) -> MaterialData:
        """Constructs and returns the populated MaterialData instance."""
        pbr = PBRCharacteristics(
            base_color_factor=self.base_color_factor,
            base_color_texture=self.base_color_texture,
            metallic_factor=self.metallic_factor,
            roughness_factor=self.roughness_factor,
            metallic_roughness_texture=self.metallic_roughness_texture,
            specular_factor=self.specular_factor,
            specular_color_factor=self.specular_color_factor,
            specular_texture=self.specular_texture,
            clearcoat_factor=self.clearcoat_factor,
            clearcoat_roughness_factor=self.clearcoat_roughness_factor,
            clearcoat_texture=self.clearcoat_texture,
            clearcoat_roughness_texture=self.clearcoat_roughness_texture,
        )

        emissive = EmissiveCharacteristics(
            factor=self.emissive_factor,
            texture=self.emissive_texture,
        )

        structural = StructuralParameters(
            normal=self.normal_texture,
            occlusion=self.occlusion_texture,
            emissive=emissive,
        )

        return MaterialData(
            name=self.name,
            alpha_cutoff=self.alpha_cutoff,
            alpha_mode=self.alpha_mode,
            double_sided=self.double_sided,
            texture_coordinate_map=self.texture_coordinate_map,
            pbr_characteristics=pbr,
            structural_parameters=structural,
        )

    def upload(self):
        if self._source_material:
            UploadManager.upload_material(self.build(), {}, {}, self._source_material)
            return

        self._source_material = UploadManager.upload_material(self.build(), {}, {})

    @property
    def source_material(self) -> GPUMaterial:
        return self._source_material # type: ignore