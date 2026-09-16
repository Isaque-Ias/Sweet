#version 460 core

in vec2 v_uv;
layout(location = 0) out vec4 Cloud_Out;

uniform sampler2D Cloud_SceneColor;
uniform sampler2D Cloud_Depth;
uniform sampler3D Cloud_Noise3D; // 3D noise texture for volumetric density

uniform mat4 sw_InvProjection;
uniform mat4 sw_InvView;

uniform vec3 sw_CameraPosition;  // Camera position in world space
uniform vec3 sw_LightDirection;   // Directional light ray direction
uniform vec3 sw_LightColor;

// Cloud Volume Bounds
const float CLOUD_BOTTOM = 500.0; // Lower altitude (in world units)
const float CLOUD_TOP    = 1500.0; // Upper altitude
const int   STEPS        = 64;     // Raymarching steps

// Reconstruct View-Space Position from Depth
vec3 reconstruct_view_position(vec2 uv, float depth)
{
    vec4 clip = vec4(uv * 2.0 - 1.0, depth * 2.0 - 1.0, 1.0);
    vec4 view = sw_InvProjection * clip;
    return view.xyz / view.w;
}

// Robust Ray-Slab (Plane Layer) Intersection
vec2 ray_cloud_layer_intersection(vec3 ray_origin, vec3 ray_dir) 
{
    // Prevent division by zero when looking horizontal
    float dy = abs(ray_dir.y) < 1e-4 ? (ray_dir.y < 0.0 ? -1e-4 : 1e-4) : ray_dir.y;

    float t1 = (CLOUD_BOTTOM - ray_origin.y) / dy;
    float t2 = (CLOUD_TOP - ray_origin.y) / dy;

    float t_entry = min(t1, t2);
    float t_exit  = max(t1, t2);

    return vec2(t_entry, t_exit);
}

// Sample density field using 3D noise
float sample_cloud_density(vec3 pos) 
{
    // Restrict cloud layer bounds
    if (pos.y < CLOUD_BOTTOM || pos.y > CLOUD_TOP) return 0.0;

    // Scale coords for noise lookup
    vec3 uvw = pos * 0.0005; 
    
    float density = texture(Cloud_Noise3D, uvw).r;
    
    // Attenuate top and bottom edges smoothly
    float height_fraction = (pos.y - CLOUD_BOTTOM) / (CLOUD_TOP - CLOUD_BOTTOM);
    float vertical_fade   = smoothstep(0.0, 0.2, height_fraction) * smoothstep(1.0, 0.7, height_fraction);
    
    return max(0.0, density - 0.3) * vertical_fade;
}

// Simple Beer-Lambert light extinction
float light_marching(vec3 pos) 
{
    vec3 light_dir = normalize(-sw_LightDirection);
    float step_size = 20.0;
    float total_density = 0.0;
    
    for (int i = 0; i < 6; i++) {
        pos += light_dir * step_size;
        total_density += sample_cloud_density(pos);
    }
    
    return exp(-total_density * 0.5);
}

void main()
{
    vec3 scene_color = texture(Cloud_SceneColor, v_uv).rgb;
    float depth      = texture(Cloud_Depth, v_uv).r;

    // Reconstruct world space ray direction
    vec4 clip = vec4(v_uv * 2.0 - 1.0, 1.0, 1.0);
    vec4 view = sw_InvProjection * clip;
    vec3 ray_dir = normalize(mat3(sw_InvView) * normalize(view.xyz));

    // Set ray distance using depth buffer
    float max_dist = 1e6; // Default to infinity for sky
    if (depth < 1.0) {
        vec3 view_pos = reconstruct_view_position(v_uv, depth);
        vec3 world_pos = (sw_InvView * vec4(view_pos, 1.0)).xyz;
        max_dist = length(world_pos - sw_CameraPosition);
    }

    // Intersect cloud layer
    vec2 hit = ray_cloud_layer_intersection(sw_CameraPosition, ray_dir);
    
    // Ensure bounds are valid along the forward ray path
    float t_min = max(hit.x, 0.0);
    float t_max = min(hit.y, max_dist);

    // If ray misses or geometry blocks before entering cloud layer
    if (t_min >= t_max) {
        Cloud_Out = vec4(scene_color, 1.0); 
        return;
    }

    // Raymarching Loop
    float step_size = (t_max - t_min) / float(STEPS);
    
    // Start marching from the center of the first step to prevent edge clipping gaps
    vec3 ray_pos = sw_CameraPosition + ray_dir * (t_min + step_size * 0.5);
    
    float transmittance = 1.0;
    vec3 integrated_light = vec3(0.0);

    for (int i = 0; i < STEPS; i++) {
        float density = sample_cloud_density(ray_pos);
        
        if (density > 0.01) {
            float light_transmittance = light_marching(ray_pos);
            vec3 cloud_color = sw_LightColor * light_transmittance;
            
            // Beer-Lambert scattering
            float step_transmittance = exp(-density * step_size * 0.05);
            integrated_light += cloud_color * density * transmittance * step_size;
            transmittance *= step_transmittance;

            if (transmittance < 0.01) break; // Early termination
        }
        
        ray_pos += ray_dir * step_size;
    }

    // Composite clouds over the rendered lighting output
    Cloud_Out = vec4(scene_color * transmittance + integrated_light, transmittance);
}