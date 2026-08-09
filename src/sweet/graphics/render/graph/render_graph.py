from sweet.graphics.upload import GPUShader
from typing import Optional, NamedTuple

class ResourceDesc(NamedTuple):
    name: str
    size_bytes: int
    is_imported: bool = False

class ResourceLifetime:
    def __init__(self, desc: ResourceDesc):
        self.desc = desc
        self.first_pass: int = float("inf") # type: ignore
        self.last_pass: int = -1
        self.memory_offset: int = -1

    def update_lifetime(self, pass_index: int) -> None:
        self.first_pass = min(self.first_pass, pass_index)
        self.last_pass = max(self.last_pass, pass_index)

    def overlaps_with(self, other: "ResourceLifetime") -> bool:
        return not (self.last_pass < other.first_pass or self.first_pass > other.last_pass)

class RenderShader:
    def __init__(self, name: str, program: Optional[GPUShader] = None):
        self.name: str = name
        self.program: Optional[GPUShader] = program
        self.inputs: set[str] = set()
        self.outputs: set[str] = set()
        self.dependencies: dict[str, tuple[str, "RenderShader"]] = {}
        self._redirect: dict[str, tuple[str, "RenderShader"]] = {}
        self.is_culled: bool = True

    def add_input(self, resource_name: str) -> "RenderShader":
        self.inputs.add(resource_name)
        return self

    def add_output(self, resource_name: str) -> "RenderShader":
        self.outputs.add(resource_name)
        return self

    def connect_input(
        self, input_res: str, producer_shader: "RenderShader", producer_output_res: str
    ) -> None:
        self.inputs.add(input_res)
        producer_shader.outputs.add(producer_output_res)
        self.dependencies[input_res] = (producer_output_res, producer_shader)

    def resolve_redirections(self) -> None:
        self._redirect.clear()
        for input_res, (producer_attr, producer_shader) in self.dependencies.items():
            if not producer_shader.is_culled:
                self._redirect[input_res] = (producer_attr, producer_shader)


class MemoryPlanner:
    @staticmethod
    def plan_aliased_memory(
        lifetimes: list[ResourceLifetime], alignment: int = 256
    ) -> int:
        transient_resources = [
            r for r in lifetimes if not r.desc.is_imported and r.last_pass >= 0
        ]
        transient_resources.sort(key=lambda r: r.desc.size_bytes, reverse=True)

        placed_resources: list[ResourceLifetime] = []
        total_heap_size = 0

        for res in transient_resources:
            aligned_size = (res.desc.size_bytes + alignment - 1) & ~(alignment - 1)
            candidate_offset = 0

            while True:
                conflict = False
                for placed in placed_resources:
                    placed_aligned_size = (
                        placed.desc.size_bytes + alignment - 1
                    ) & ~(alignment - 1)
                    byte_overlap = not (
                        candidate_offset + aligned_size <= placed.memory_offset
                        or candidate_offset >= placed.memory_offset + placed_aligned_size
                    )

                    if byte_overlap and res.overlaps_with(placed):
                        candidate_offset = placed.memory_offset + placed_aligned_size
                        conflict = True
                        break

                if not conflict:
                    break

            res.memory_offset = candidate_offset
            placed_resources.append(res)
            total_heap_size = max(total_heap_size, candidate_offset + aligned_size)

        return total_heap_size


class RenderGraph:
    def __init__(self):
        self.shaders: list[RenderShader] = []
        self.resource_descriptors: dict[str, ResourceDesc] = {}
        self.graph_outputs: set[str] = set()
        self.valid_resources: set[str] = set()
        self.active_passes: list[RenderShader] = []
        self.lifetimes: dict[str, ResourceLifetime] = {}
        self.total_transient_heap_size: int = 0

    def register_resource(self, name: str, size_bytes: int = 0, is_imported: bool = False) -> None:
        self.resource_descriptors[name] = ResourceDesc(name, size_bytes, is_imported)

    def add_shader(self, shader: RenderShader) -> RenderShader:
        if shader not in self.shaders:
            self.shaders.append(shader)
        return shader

    def set_swapchain_target(self, resource_name: str) -> None:
        self.graph_outputs.add(resource_name)

    def initialize(self) -> None:
        self.valid_resources.clear()
        self.active_passes.clear()
        self.lifetimes.clear()

        for shader in self.shaders:
            shader.is_culled = True
            shader._redirect.clear() # type: ignore

        resource_producers: dict[str, RenderShader] = {
            out_res: shader for shader in self.shaders for out_res in shader.outputs
        }

        resources_to_process: list[str] = list(self.graph_outputs)
        visited_resources: set[str] = set(resources_to_process)

        while resources_to_process:
            res = resources_to_process.pop()
            self.valid_resources.add(res)

            producer = resource_producers.get(res)
            if producer is None:
                continue

            if producer.is_culled:
                producer.is_culled = False
                self.active_passes.append(producer)

            for input_res in producer.inputs:
                if input_res not in visited_resources:
                    visited_resources.add(input_res)
                    resources_to_process.append(input_res)

        self.active_passes.reverse()

        for shader in self.active_passes:
            shader.resolve_redirections()

        for pass_idx, shader in enumerate(self.active_passes):
            for out_res in shader.outputs:
                if out_res in self.valid_resources:
                    desc = self.resource_descriptors.get(
                        out_res, ResourceDesc(out_res, size_bytes=1024 * 1024)
                    )
                    lifetime = self.lifetimes.setdefault(out_res, ResourceLifetime(desc))
                    lifetime.update_lifetime(pass_idx)

            for input_res in shader.inputs:
                if input_res in self.valid_resources:
                    desc = self.resource_descriptors.get(
                        input_res, ResourceDesc(input_res, size_bytes=1024 * 1024)
                    )
                    lifetime = self.lifetimes.setdefault(
                        input_res, ResourceLifetime(desc)
                    )
                    lifetime.update_lifetime(pass_idx)

        self.total_transient_heap_size = MemoryPlanner.plan_aliased_memory(
            list(self.lifetimes.values())
        )

    def get_initial_resource_map(self) -> dict[str, list[str]]:
        produced_resources: set[str] = {
            out_res for shader in self.active_passes for out_res in shader.outputs
        }

        initial_map: dict[str, list[str]] = {}

        for shader in self.active_passes:
            for input_res in shader.inputs:
                if input_res not in produced_resources and input_res in self.valid_resources:
                    initial_map.setdefault(input_res, []).append(shader.name)

        return initial_map

    # def print_memory_plan(self) -> None:
    #     """Displays execution order, resource lifetimes, and aliased memory layout."""
    #     print("=== EXECUTION TIMELINE ===")
    #     for idx, shader in enumerate(self.active_passes):
    #         print(f" Pass {idx}: [{shader.name}]")

    #     print("\n=== RESOURCE LIFETIMES & ALIASED OFFSETS ===")
    #     raw_sum = 0
    #     for name, life in self.lifetimes.items():
    #         if life.desc.is_imported:
    #             print(f" Resource '{name}': Persistent (Imported)")
    #             continue

    #         raw_sum += life.desc.size_bytes
    #         size_mb = life.desc.size_bytes / (1024 * 1024)
    #         offset_mb = life.memory_offset / (1024 * 1024)
    #         print(
    #             f" Resource '{name}': Lifetime = Pass [{life.first_pass}..{life.last_pass}] "
    #             f"| Size = {size_mb:.1f} MB | Heap Offset = {offset_mb:.1f} MB"
    #         )

    #     print(f"\nTotal Unaliased Size : {raw_sum / (1024 * 1024):.1f} MB")
    #     print(f"Aliased Heap Required: {self.total_transient_heap_size / (1024 * 1024):.1f} MB")
