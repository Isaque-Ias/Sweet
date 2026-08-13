from ..render_graph import RenderShader, RenderGraph
from .....resources.assets.importer import ImportManager
from ....upload import UploadManager
from pathlib import Path

_BASE = Path(__file__).parent
_PASSES = _BASE.parent.parent / "passes"

class Deffered:
    @classmethod
    def _file_to_node(cls, name: str, vertex: str | Path, fragment: str | Path):
        shader_prog = ImportManager.load_shaders(vertex, fragment)
        gpu_shader = UploadManager.upload_shaders(shader_prog)
        shader = RenderShader(name, gpu_shader)
        return shader

    @classmethod
    def build(cls):
        cls.graph = RenderGraph()

        # ============================================================
        # IMPORTED RESOURCES
        # ============================================================

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

        # ============================================================
        # SHADOW BRANCH
        #
        # Mesh
        #   ↓
        # ShadowPass
        #   ↓
        # ShadowMap
        #
        # This branch does NOT depend on GBuffer.
        # ============================================================

        shadow_pass = cls._file_to_node(
            "ShadowPass",
            _PASSES / "shadow" / "shadow.vert",
            _PASSES / "shadow" / "shadow.frag",
        )

        shadow_pass.add_input("Mesh_Positions")
        shadow_pass.add_input("Mesh_Normals")

        shadow_pass.add_output("ShadowMap")

        # ============================================================
        # GBUFFER BRANCH
        #
        # Mesh
        #   ↓
        # GBufferPass
        #   ├── Albedo
        #   ├── Normals
        #   └── Depth
        # ============================================================

        gbuffer_pass = cls._file_to_node(
            "GBufferPass",
            _PASSES / "gbuffer" / "gbuffer.vert",
            _PASSES / "gbuffer" / "gbuffer.frag",
        )

        gbuffer_pass.add_input("Mesh_Positions")
        gbuffer_pass.add_input("Mesh_Normals")
        gbuffer_pass.add_input("Mesh_UVs")

        gbuffer_pass.add_output("GBuffer_Depth")
        gbuffer_pass.add_output("GBuffer_Albedo")
        gbuffer_pass.add_output("GBuffer_Normals")

        # ============================================================
        # SSAO BRANCH
        #
        # GBuffer
        #    │
        #    └── Depth + Normals
        #             ↓
        #           SSAO
        #             ↓
        #         AO_Texture
        #
        # This is the second branch.
        # ============================================================

        ssao_pass = cls._file_to_node(
            "SSAOPass",
            _PASSES / "ssao" / "ssao.vert",
            _PASSES / "ssao" / "ssao.frag",
        )

        ssao_pass.connect_input(
            "GBuffer_Depth",
            gbuffer_pass,
            "GBuffer_Depth",
        )

        ssao_pass.connect_input(
            "GBuffer_Normals",
            gbuffer_pass,
            "GBuffer_Normals",
        )

        ssao_pass.add_output("SSAO")

        # ============================================================
        # LIGHTING MERGE
        #
        #                    ShadowMap ─────┐
        #                    Albedo ────────┤
        #                    Normals ───────┤
        #                    Depth ─────────┤
        #                    SSAO ──────────┤
        #                                   ↓
        #                                Lighting
        #
        # This is deliberately the merge point of the graph.
        # ============================================================

        lighting_pass = cls._file_to_node(
            "LightingPass",
            _PASSES / "lighting" / "lighting.vert",
            _PASSES / "lighting" / "lighting.frag",
        )

        lighting_pass.connect_input(
            "GBuffer_Albedo",
            gbuffer_pass,
            "GBuffer_Albedo",
        )

        lighting_pass.connect_input(
            "GBuffer_Normals",
            gbuffer_pass,
            "GBuffer_Normals",
        )

        lighting_pass.connect_input(
            "GBuffer_Depth",
            gbuffer_pass,
            "GBuffer_Depth",
        )

        lighting_pass.connect_input(
            "SSAO",
            ssao_pass,
            "SSAO",
        )

        lighting_pass.connect_input(
            "ShadowMap",
            shadow_pass,
            "ShadowMap",
        )

        lighting_pass.add_output("Lit_Color")

        # ============================================================
        # PRESENT
        #
        # Lighting
        #    ↓
        # Present
        #    ↓
        # Backbuffer
        # ============================================================

        present_pass = cls._file_to_node(
            "PresentPass",
            _PASSES / "present" / "present.vert",
            _PASSES / "present" / "present.frag",
        )

        present_pass.connect_input(
            "Lit_Color",
            lighting_pass,
            "Lit_Color",
        )

        present_pass.add_output("Backbuffer")

        # ============================================================
        # REGISTER EVERYTHING
        # ============================================================

        for render_pass in [
            shadow_pass,
            gbuffer_pass,
            ssao_pass,
            lighting_pass,
            present_pass,
        ]:
            cls.graph.add_shader(render_pass)

        cls.graph.set_swapchain_target("Backbuffer")

    @classmethod
    def initialize(cls):
        cls.graph.initialize()

        # print("=== INITIAL ROOT RESOURCE MAP ===")
        # root_map = cls.graph.get_initial_resource_map()
        # for res_name, consumer_passes in root_map.items():
        #     print(f" Root Resource '{res_name}' enters at -> Passes: {consumer_passes}")

        # print("\n=== ACTIVE EXECUTION PIPELINE ===")
        # for idx, pass_node in enumerate(cls.graph.active_passes):
        #     print(f" [{idx}] {pass_node.name}")
        #     for in_res, (prod_res, prod_pass) in pass_node._redirect.items():
        #         print(f"      └─ Reads '{in_res}' from [{prod_pass.name}].{prod_res}")