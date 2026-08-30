from ..render_graph import RenderGraph, RenderShader, RenderDomain
from ..render_graph import Graph
from pathlib import Path

_BASE = Path(__file__).parent
_PASSES = _BASE.parent.parent / "passes"

class SkyBox(Graph):
    name = "SkyBox"
    @classmethod
    def build(cls):
        cls.graph = RenderGraph()

        sky_pass = RenderShader("SkyPass", cls._file_to_node(
            _PASSES / "cubemap.vert",
            _PASSES / "sky" / "nishita.frag",
            geometry=_PASSES / "cubemap.geom",
        ), RenderDomain.CUBEMAP)

        sky_pass.add_output("Backbuffer")

        for render_pass in [
            sky_pass
        ]:
            cls.graph.add_shader(render_pass)

        cls.graph.set_swapchain_target("Backbuffer")