from ..render_graph import RenderGraph, RenderShader, RenderDomain
from ..render_graph import Graph
from pathlib import Path

_BASE = Path(__file__).parent
_PASSES = _BASE.parent.parent / "passes"

class Deffered(Graph):
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
            _PASSES / "shadow" / "shadow.vert",
            _PASSES / "shadow" / "shadow.frag",
        ), RenderDomain.SCENE)

        shadow_pass.add_input("Mesh_Positions")
        shadow_pass.add_input("Mesh_Normals")

        shadow_pass.add_output("depth_ShadowMap")

        gbuffer_pass = RenderShader("GBufferPass", cls._file_to_node(
            _PASSES / "gbuffer" / "gbuffer.vert",
            _PASSES / "gbuffer" / "gbuffer.frag",
        ), RenderDomain.SCENE)

        gbuffer_pass.add_input("Mesh_Positions")
        gbuffer_pass.add_input("Mesh_Normals")
        gbuffer_pass.add_input("Mesh_UVs")

        gbuffer_pass.add_output("depth_GBuffer")
        gbuffer_pass.add_output("GBuffer_Albedo")
        gbuffer_pass.add_output("GBuffer_Normals")

        ssao_pass = RenderShader("SSAOPass", cls._file_to_node(
            _PASSES / "ssao" / "ssao.vert",
            _PASSES / "ssao" / "ssao.frag",
        ), RenderDomain.SCREEN)

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

        lighting_pass = RenderShader("LightingPass", cls._file_to_node(
            _PASSES / "lighting" / "lighting.vert",
            _PASSES / "lighting" / "lighting.frag",
        ), RenderDomain.SCREEN)

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
            ssao_pass,
            "SSAO_Out",
        )

        lighting_pass.connect_input(
            "Light_ShadowMap",
            shadow_pass,
            "depth_ShadowMap",
        )

        lighting_pass.add_output("Light_Out")

        present_pass = RenderShader("PresentPass", cls._file_to_node(
            _PASSES / "present" / "present.vert",
            _PASSES / "present" / "present.frag",
        ), RenderDomain.SCREEN)

        present_pass.connect_input(
            "Present_Light",
            lighting_pass,
            "Light_Out",
        )

        present_pass.add_output("Backbuffer")

        for render_pass in [
            shadow_pass,
            gbuffer_pass,
            ssao_pass,
            lighting_pass,
            present_pass,
        ]:
            cls.graph.add_shader(render_pass)

        cls.graph.set_swapchain_target("Backbuffer")