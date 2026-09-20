from pathlib import Path
import struct
from ..render_graph import RenderGraph, RenderShader, RenderDomain, PassConfig, MipSelect, Graph

_BASE = Path(__file__).parent
_PASSES = _BASE.parent.parent / "passes"

class Deferred(Graph):
    name = "Deferred"
    
    @classmethod
    def build(cls):
        cls.graph = RenderGraph()

        quad_func = lambda cmd, vdata: cmd.draw(domain="view", vertex_count=3, instance_count=1) # type: ignore
        
        # --- Imported Engine Resources ---
        cls.graph.register_resource("Mesh_Positions", is_imported=True)
        cls.graph.register_resource("Mesh_Normals", is_imported=True)
        cls.graph.register_resource("Mesh_UVs", is_imported=True)
        cls.graph.register_resource("Backbuffer", is_imported=True)

        # -------------------------------------------------------------------
        # 1. SHADOW PASS
        # -------------------------------------------------------------------
        shadow_pass = RenderShader("ShadowPass", cls._file_to_node(
            _PASSES / "shadow" / "shadow_depth.vert",
            _PASSES / "shadow" / "shadow.frag",
        ), PassConfig(
            depth_texture=True,
            domain=RenderDomain.LIGHT,
            render_func=lambda cmd, vdata: cmd.draw(domain="view", vertex_count=vdata.max_indices_in_batch, instance_count=vdata.object_count) # type: ignore
        ))
        shadow_pass.add_input("Mesh_Positions")
        shadow_pass.add_input("Mesh_Normals")
        shadow_pass.add_output("depth_ShadowMap")

        # -------------------------------------------------------------------
        # 2. G-BUFFER PASS
        # -------------------------------------------------------------------
        gbuffer_pass = RenderShader("GBufferPass", cls._file_to_node(
            _PASSES / "gbuffer" / "gbuffer.vert",
            _PASSES / "gbuffer" / "gbuffer.frag",
        ), PassConfig(
            depth_texture=True,
            domain=RenderDomain.SCENE,
            render_func=lambda cmd, vdata: cmd.draw(domain="view", vertex_count=vdata.max_indices_in_batch, instance_count=vdata.object_count) # type: ignore
        ))
        gbuffer_pass.add_input("Mesh_Positions")
        gbuffer_pass.add_input("Mesh_Normals")
        gbuffer_pass.add_input("Mesh_UVs")

        gbuffer_pass.add_output("depth_GBuffer")
        gbuffer_pass.add_output("GBuffer_Albedo")
        gbuffer_pass.add_output("GBuffer_Normals")
        gbuffer_pass.add_output("GBuffer_ORM")
        gbuffer_pass.add_output("GBuffer_Specular")
        gbuffer_pass.add_output("GBuffer_Emissive")

        # -------------------------------------------------------------------
        # 3. SSAO & BILATERAL BLUR PASSES
        # -------------------------------------------------------------------
        ssao_pass = RenderShader("SSAOPass", cls._file_to_node(
            _PASSES / "fullscreen.vert",
            _PASSES / "ssao" / "ssao.frag",
        ), PassConfig(domain=RenderDomain.SCREEN, render_func=quad_func))
        ssao_pass.connect_input("SSAO_Depth", gbuffer_pass, "depth_GBuffer")
        ssao_pass.connect_input("SSAO_Normals", gbuffer_pass, "GBuffer_Normals")
        ssao_pass.add_output("SSAO_Out")

        ssao_blur_x_pass = RenderShader("SSAOBlurXPass", cls._file_to_node(
            _PASSES / "fullscreen.vert",
            _PASSES / "ssao_blur" / "horizontal.frag",
        ), PassConfig(domain=RenderDomain.SCREEN, render_func=quad_func))
        ssao_blur_x_pass.connect_input("SSAO_Input", ssao_pass, "SSAO_Out")
        ssao_blur_x_pass.connect_input("SSAO_Normals", gbuffer_pass, "GBuffer_Normals")
        ssao_blur_x_pass.connect_input("SSAO_Depth", gbuffer_pass, "depth_GBuffer")
        ssao_blur_x_pass.add_output("AOX_Out")

        ssao_blur_y_pass = RenderShader("SSAOBlurYPass", cls._file_to_node(
            _PASSES / "fullscreen.vert",
            _PASSES / "ssao_blur" / "vertical.frag",
        ), PassConfig(domain=RenderDomain.SCREEN, render_func=quad_func))
        ssao_blur_y_pass.connect_input("SSAO_Input", ssao_blur_x_pass, "AOX_Out")
        ssao_blur_y_pass.connect_input("SSAO_Normals", gbuffer_pass, "GBuffer_Normals")
        ssao_blur_y_pass.connect_input("SSAO_Depth", gbuffer_pass, "depth_GBuffer")
        ssao_blur_y_pass.add_output("AOY_Out")

        # -------------------------------------------------------------------
        # 4. LIGHTING & ENVIRONMENT PASSES
        # -------------------------------------------------------------------
        lighting_pass = RenderShader("LightingPass", cls._file_to_node(
            _PASSES / "lighting" / "lighting.vert",
            _PASSES / "lighting" / "lighting.frag",
        ), PassConfig(domain=RenderDomain.SCREEN, render_func=quad_func))
        lighting_pass.connect_input("Light_Albedo", gbuffer_pass, "GBuffer_Albedo")
        lighting_pass.connect_input("Light_Normals", gbuffer_pass, "GBuffer_Normals")
        lighting_pass.connect_input("Light_ORM", gbuffer_pass, "GBuffer_ORM")
        lighting_pass.connect_input("Light_Emissive", gbuffer_pass, "GBuffer_Emissive")
        lighting_pass.connect_input("Light_Specular", gbuffer_pass, "GBuffer_Specular")
        lighting_pass.connect_input("Light_Depth", gbuffer_pass, "depth_GBuffer")
        lighting_pass.connect_input("Light_ClearCoat", gbuffer_pass, "GBuffer_Clearcoat")
        lighting_pass.connect_input("Light_SSAO", ssao_blur_y_pass, "AOY_Out")
        lighting_pass.connect_input("Light_ShadowMap", shadow_pass, "depth_ShadowMap")
        lighting_pass.add_output("Light_Out")

        background_pass = RenderShader("SkyPass", cls._file_to_node(
            _PASSES / "sky" / "background.vert",
            _PASSES / "sky" / "background.frag",
        ), PassConfig(domain=RenderDomain.SCREEN, render_func=quad_func))
        background_pass.connect_input("bgLight", lighting_pass, "Light_Out")
        background_pass.connect_input("u_DepthTexture", gbuffer_pass, "depth_GBuffer")
        background_pass.add_output("bgOut")

        volume_pass = RenderShader("VolumePass", cls._file_to_node(
            _PASSES / "fullscreen.vert",
            _PASSES / "volumes" / "volume_raymarch.frag",
        ), PassConfig(domain=RenderDomain.SCREEN, render_func=quad_func))
        volume_pass.connect_input("u_SceneColor", background_pass, "bgOut")
        volume_pass.connect_input("u_DepthTexture", gbuffer_pass, "depth_GBuffer")
        volume_pass.connect_input("u_ShadowMap", shadow_pass, "depth_ShadowMap")
        volume_pass.add_output("Volume_Out")

        bloom_extract_pass = RenderShader("BloomExtractPass", cls._file_to_node(
            _PASSES / "fullscreen.vert",
            _PASSES / "bloom" / "extract.frag",
        ), PassConfig(domain=RenderDomain.SCREEN, render_func=quad_func))
        bloom_extract_pass.connect_input("Bloom_Light", volume_pass, "Volume_Out")
        bloom_extract_pass.add_output("Bloom_Out")

        def render_bloom(cmd, vdata):
            bloom_target = vdata.pass_targets["BloomPass"]
            extract_target = vdata.pass_targets["BloomExtractPass"]
            num_mips = bloom_target.get_color_texture().mip_levels
            vp_w, vp_h = vdata.viewport[2], vdata.viewport[3]

            # Disable blending for downsampling
            cmd.set_blend_state(enabled=False)
            cmd.set_uniform_value("u_mode", struct.pack("1i", 0))

            # ---------------------------------------------------------------
            # 1. DOWNSAMPLE CHAIN (mip 0 -> mip N)
            # ---------------------------------------------------------------
            for i in range(num_mips - 1):
                src_mip, dst_mip = i, i + 1
                src_w, src_h = max(1, vp_w >> src_mip), max(1, vp_h >> src_mip)
                dst_w, dst_h = max(1, vp_w >> dst_mip), max(1, vp_h >> dst_mip)

                # Clear WITH BLACK (0,0,0) to get rid of red/magenta background
                cmd.begin_render_pass(
                    target=bloom_target, 
                    target_mip=dst_mip, 
                    viewport=(0, 0, dst_w, dst_h),
                    clear_color=(0.0, 0.0, 0.0)
                )
                
                # Send texture dimensions of the SOURCE mip
                cmd.set_uniform_value("u_texelSize", struct.pack("2f", 1.0 / float(src_w), 1.0 / float(src_h)))
                cmd.set_uniform_value("u_srcMipLevel", struct.pack("1f", src_mip))

                if src_mip == 0:
                    cmd.use_target_texture(extract_target, 0, location=0, src_mip=0)
                else:
                    cmd.use_target_texture(bloom_target, 0, location=0, src_mip=src_mip)

                cmd.draw(domain="view", vertex_count=3, instance_count=1)
                cmd.end_render_pass()

            # ---------------------------------------------------------------
            # 2. UPSAMPLE CHAIN (mip N -> mip 0) with Additive Accumulation
            # ---------------------------------------------------------------
            cmd.set_uniform_value("u_mode", struct.pack("1i", 1))
            
            # Enable additive blending
            cmd.set_blend_state(enabled=True, src_factor="ONE", dst_factor="ONE", blend_op="ADD")

            for i in range(num_mips - 1, 0, -1):
                src_mip, dst_mip = i, i - 1
                dst_w, dst_h = max(1, vp_w >> dst_mip), max(1, vp_h >> dst_mip)

                # DO NOT CLEAR during upsampling - we need to accumulate onto existing lower mips
                cmd.begin_render_pass(
                    target=bloom_target, 
                    target_mip=dst_mip, 
                    viewport=(0, 0, dst_w, dst_h),
                    clear_color=(0.0, 0.0, 0.0)
                )

                cmd.set_uniform_value("u_texelSize", struct.pack("2f", 1.0 / float(dst_w), 1.0 / float(dst_h)))
                cmd.set_uniform_value("u_filterRadius", struct.pack("1f", 2.0)) # Increase radius for spread
                cmd.set_uniform_value("u_srcMipLevel", struct.pack("1f", src_mip))

                cmd.use_target_texture(bloom_target, 0, location=0, src_mip=src_mip)

                cmd.draw(domain="view", vertex_count=3, instance_count=1)
                cmd.end_render_pass()

            cmd.set_blend_state(enabled=False)
            
        bloom_pass = RenderShader("BloomPass", cls._file_to_node(
            _PASSES / "fullscreen.vert",
            _PASSES / "bloom" / "bloom.frag",
        ), PassConfig(domain=RenderDomain.SCREEN, render_func=quad_func, mip_levels=6, blend_enable=True, custom_pass_management=False))
        bloom_pass.connect_input("u_srcTexture", bloom_extract_pass, "Bloom_Out")
        bloom_pass.add_output("Bloom_Final")

        luminance_pass = RenderShader("LuminancePass", cls._file_to_node(
            _PASSES / "fullscreen.vert",
            _PASSES / "tonemap" / "luminance.frag",
        ), PassConfig(mip_levels=-1, domain=RenderDomain.SCREEN, render_func=quad_func))
        luminance_pass.connect_input("hdrSceneTexture", volume_pass, "Volume_Out")
        luminance_pass.add_output("LumPass")

        tonemap_pass = RenderShader("TonemapPass", cls._file_to_node(
            _PASSES / "fullscreen.vert",
            _PASSES / "tonemap" / "tonemap.frag",
        ), PassConfig(domain=RenderDomain.SCREEN, render_func=quad_func))
        tonemap_pass.connect_input("TonehdrSceneTexture", volume_pass, "Volume_Out")
        tonemap_pass.connect_input("avgLuminanceTex", luminance_pass, "LumPass", MipSelect.LOWEST)
        tonemap_pass.connect_input("HDRBloomTone", bloom_pass, "Bloom_Final")
        tonemap_pass.add_output("TonePass")

        # -------------------------------------------------------------------
        # 7. PRESENT / SWAPCHAIN PASS
        # -------------------------------------------------------------------
        present_pass = RenderShader("PresentPass", cls._file_to_node(
            _PASSES / "present" / "present.vert",
            _PASSES / "present" / "present.frag",
        ), PassConfig(domain=RenderDomain.SCREEN, render_func=quad_func))
        present_pass.connect_input("Present_Light", tonemap_pass, "TonePass")
        present_pass.add_output("Backbuffer")

        for render_pass in [
            shadow_pass,
            gbuffer_pass,
            ssao_pass,
            ssao_blur_x_pass,
            ssao_blur_y_pass,
            lighting_pass,
            background_pass,
            volume_pass,
            bloom_extract_pass,
            bloom_pass,
            luminance_pass,
            tonemap_pass,
            present_pass,
        ]:
            cls.graph.add_shader(render_pass)

        cls.graph.set_swapchain_target("Backbuffer")