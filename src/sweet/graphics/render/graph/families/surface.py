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

            cls.graph.register_resource("Mesh_Positions", is_imported=True)
            cls.graph.register_resource("Mesh_Normals", is_imported=True)
            cls.graph.register_resource("Mesh_UVs", is_imported=True)
            cls.graph.register_resource("Backbuffer", is_imported=True)

            gbuffer_pass = cls._file_to_node("GBufferPass", _PASSES / "gbuffer" / "gbuffer.vsh", _PASSES / "gbuffer" / "gbuffer.fsh")
            gbuffer_pass.add_input("Mesh_Positions")
            gbuffer_pass.add_input("Mesh_Normals")
            gbuffer_pass.add_input("Mesh_UVs")
            gbuffer_pass.add_output("GBuffer_Depth")
            gbuffer_pass.add_output("GBuffer_Albedo")
            gbuffer_pass.add_output("GBuffer_Normals")

            lighting_pass = cls._file_to_node("LightingPass", _PASSES / "lighting" / "lighting.vsh", _PASSES / "lighting" / "lighting.fsh")
            lighting_pass.connect_input("GBuffer_Albedo", gbuffer_pass, "GBuffer_Albedo")
            lighting_pass.connect_input("GBuffer_Normals", gbuffer_pass, "GBuffer_Normals")
            lighting_pass.add_output("Lit_Color")

            present_pass = cls._file_to_node("PresentPass", _PASSES / "present" / "present.vsh", _PASSES / "present" / "present.fsh")
            present_pass.connect_input("Lit_Color", lighting_pass, "Lit_Color")
            present_pass.add_output("Backbuffer")

            for p in [gbuffer_pass, lighting_pass, present_pass]:
                cls.graph.add_shader(p)

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