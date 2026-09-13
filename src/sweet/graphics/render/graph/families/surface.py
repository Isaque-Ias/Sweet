from ..render_graph import RenderGraph, RenderShader, RenderDomain, PassConfig, MipSelect
from ..render_graph import Graph
from pathlib import Path

_BASE = Path(__file__).parent
_PASSES = _BASE.parent.parent / "passes"

class Deffered(Graph):
    name = "Deffered"
    @classmethod
    def build(cls):
        cls.graph = RenderGraph()

        cls.graph.register_resource(
            "Mesh_Positions",
            is_imported=True,
        )

        cls.graph.register_resource(
            "Mesh_Normals",
            is_imported=True,
        )

        cls.graph.register_resource(
            "Mesh_UVs",
            is_imported=True,
        )

        cls.graph.register_resource(
            "Backbuffer",
            is_imported=True,
        )

        shadow_pass = RenderShader("ShadowPass", cls._file_to_node(
            _PASSES / "shadow" / "shadow_depth.vert",
            _PASSES / "shadow" / "shadow.frag",
            # geometry=_PASSES / "shadow" / "shadow.geom"
        ), PassConfig(
            # hdr=False,
            depth_texture=True,
            domain=RenderDomain.LIGHT
            )
        )

        shadow_pass.add_input("Mesh_Positions")
        shadow_pass.add_input("Mesh_Normals")

        shadow_pass.add_output("depth_ShadowMap")

        gbuffer_pass = RenderShader("GBufferPass", cls._file_to_node(
            _PASSES / "gbuffer" / "gbuffer.vert",
            _PASSES / "gbuffer" / "gbuffer.frag",
        ), PassConfig(
            depth_texture=True,
            domain=RenderDomain.SCENE
            )
        )

        gbuffer_pass.add_input("Mesh_Positions")
        gbuffer_pass.add_input("Mesh_Normals")
        gbuffer_pass.add_input("Mesh_UVs")

        gbuffer_pass.add_output("depth_GBuffer")
        gbuffer_pass.add_output("GBuffer_Albedo")
        gbuffer_pass.add_output("GBuffer_Normals")

        ssao_pass = RenderShader("SSAOPass", cls._file_to_node(
            _PASSES / "fullscreen.vert",
            _PASSES / "ssao" / "ssao.frag",
        ), PassConfig(
            # hdr=False,
            domain=RenderDomain.SCREEN
            )
        )

        ssao_pass.connect_input(
            "SSAO_Depth",
            gbuffer_pass,
            "depth_GBuffer",
        )

        ssao_pass.connect_input(
            "SSAO_Normals",
            gbuffer_pass,
            "GBuffer_Normals",
        )

        ssao_pass.add_output("SSAO_Out")

        ssao_blur_x_pass = RenderShader("SSAOBlurXPass", cls._file_to_node(
            _PASSES / "fullscreen.vert",
            _PASSES / "ssao_blur" / "horizontal.frag",
        ), PassConfig(
            # hdr=False,
            domain=RenderDomain.SCREEN
            )
        )

        ssao_blur_x_pass.connect_input(
            "SSAO_Input",
            ssao_pass,
            "SSAO_Out",
        )

        ssao_blur_x_pass.connect_input(
            "SSAO_Normals",
            gbuffer_pass,
            "GBuffer_Normals",
        )

        ssao_blur_x_pass.connect_input(
            "SSAO_Depth",
            gbuffer_pass,
            "depth_GBuffer",
        )
        
        ssao_blur_x_pass.add_output("AOX_Out")

        ssao_blur_y_pass = RenderShader("SSAOBlurYPass", cls._file_to_node(
            _PASSES / "fullscreen.vert",
            _PASSES / "ssao_blur" / "vertical.frag",
        ), PassConfig(
            # hdr=False,
            domain=RenderDomain.SCREEN
            )
        )

        ssao_blur_y_pass.connect_input(
            "SSAO_Input",
            ssao_blur_x_pass,
            "AOX_Out",
        )

        ssao_blur_y_pass.connect_input(
            "SSAO_Normals",
            gbuffer_pass,
            "GBuffer_Normals",
        )

        ssao_blur_y_pass.connect_input(
            "SSAO_Depth",
            gbuffer_pass,
            "depth_GBuffer",
        )
        
        ssao_blur_y_pass.add_output("AOY_Out")

        lighting_pass = RenderShader("LightingPass", cls._file_to_node(
            _PASSES / "lighting" / "lighting.vert",
            _PASSES / "lighting" / "lighting.frag",
        ), PassConfig(
            domain=RenderDomain.SCREEN
            )
        )

        lighting_pass.connect_input(
            "Light_Albedo",
            gbuffer_pass,
            "GBuffer_Albedo",
        )

        lighting_pass.connect_input(
            "Light_Normals",
            gbuffer_pass,
            "GBuffer_Normals",
        )

        lighting_pass.connect_input(
            "Light_Depth",
            gbuffer_pass,
            "depth_GBuffer",
        )

        lighting_pass.connect_input(
            "Light_SSAO",
            # ssao_pass, "SSAO_Out"
            ssao_blur_y_pass,
            "AOY_Out",
        )

        lighting_pass.connect_input(
            "Light_ShadowMap",
            shadow_pass,
            "depth_ShadowMap",
        )

        lighting_pass.add_output("Light_Out")

        # ---------------------------------------------------------------------
        # 2. VOLUMETRIC FOG PASS (Composites fog over lit solid scene)
        # ---------------------------------------------------------------------
        # fog_pass = RenderShader("VolumetricFogPass", cls._file_to_node(
        #     _PASSES / "fullscreen.vert",
        #     _PASSES / "fog" / "fog.frag",
        # ), RenderDomain.SCREEN)

        # # Reads current lit scene color to blend fog onto
        # fog_pass.connect_input(
        #     "fogSceneColor",
        #     lighting_pass,
        #     "Light_Out",
        # )
        # # Reads scene depth to stop raymarching at solid surfaces
        # fog_pass.connect_input(
        #     "fogDepth",
        #     gbuffer_pass,
        #     "depth_GBuffer",
        # )
        # # Reads shadow map for volumetric light shafts/god rays
        # fog_pass.connect_input(
        #     "fogShadow",
        #     shadow_pass,
        #     "depth_ShadowMap",
        # )

        # fog_pass.add_output("outFog")

        # sky

        background_pass = RenderShader("SkyPass", cls._file_to_node(
            _PASSES / "sky" / "background.vert",
            _PASSES / "sky" / "background.frag",
        ), PassConfig(
            domain=RenderDomain.SCREEN
            )
        )

        background_pass.connect_input(
            "bgLight",
            lighting_pass,
            "Light_Out"
        )

        background_pass.add_output("bgOut")


        # bloom

        bloom_pass = RenderShader("BloomPass", cls._file_to_node(
            _PASSES / "fullscreen.vert",
            _PASSES / "bloom" / "bloom.frag",
        ), PassConfig(
            domain=RenderDomain.SCREEN
            )
        )

        bloom_pass.connect_input(
            "Bloom_Light",
            background_pass,
            "bgOut",
        )

        bloom_pass.add_output("Bloom_Out")

        # blur bloom

        bloom_blur_pass = RenderShader("BlurBloomPass", cls._file_to_node(
            _PASSES / "fullscreen.vert",
            _PASSES / "bloom" / "blur.frag",
        ), PassConfig(
            domain=RenderDomain.SCREEN
            )
        )

        bloom_blur_pass.connect_input(
            "Bloom_Input",
            bloom_pass,
            "Bloom_Out",
        )

        bloom_blur_pass.add_output("BloomBlur_Out")

        # Luminance

        luminance_pass = RenderShader("LuminancePass", cls._file_to_node(
            _PASSES / "fullscreen.vert",
            _PASSES / "tonemap" / "luminance.frag",
        ), PassConfig(
            mip_levels=-1,
            domain=RenderDomain.SCREEN
            )
        )

        luminance_pass.connect_input(
            "hdrSceneTexture",
            background_pass,
            "bgOut",
        )

        luminance_pass.add_output("LumPass")

        # Tonemap

        tonemap_pass = RenderShader("TonemapPass", cls._file_to_node(
            _PASSES / "fullscreen.vert",
            _PASSES / "tonemap" / "tonemap.frag",
        ), PassConfig(
            domain=RenderDomain.SCREEN
            )
        )

        tonemap_pass.connect_input(
            "TonehdrSceneTexture",
            background_pass,
            "bgOut",
        )

        tonemap_pass.connect_input(
            "avgLuminanceTex",
            luminance_pass,
            "LumPass",
            MipSelect.LOWEST,
        )

        tonemap_pass.connect_input(
            "HDRBloomTone",
            bloom_blur_pass,
            "BloomBlur_Out",
        )

        tonemap_pass.add_output("TonePass")

        # present

        present_pass = RenderShader("PresentPass", cls._file_to_node(
            _PASSES / "present" / "present.vert",
            _PASSES / "present" / "present.frag",
        ), PassConfig(
            domain=RenderDomain.SCREEN
            )
        )

        present_pass.connect_input(
            "Present_Light",
            # lighting_pass,
            # "Light_Out",
            tonemap_pass,
            "TonePass",
        )

        present_pass.add_output("Backbuffer")

        for render_pass in [
            shadow_pass,
            gbuffer_pass,
            ssao_pass,
            ssao_blur_x_pass,
            ssao_blur_y_pass,
            lighting_pass,
            bloom_pass,
            bloom_blur_pass,
            background_pass,
            luminance_pass,
            tonemap_pass,
            present_pass
        ]:
            cls.graph.add_shader(render_pass)

        cls.graph.set_swapchain_target("Backbuffer")