#version 430 core

out vec4 FragColor;
in vec2 TexCoords;

uniform sampler2D screenTexture;

// --- DYNAMIC UNIFORMS ---
uniform vec2 u_resolution;         // Pass your window size here (e.g., vec2(800.0, 600.0))
uniform float u_fov = 120.0;       // Scene Field of View
uniform float u_d = 1.0;           // Panini parameter (0.0 to 1.0)

void main() {
    // 1. Calculate the aspect ratio from the pixel sizes
    float aspect = u_resolution.x / u_resolution.y;

    // 2. Convert UVs to normalized -1 to 1 screen space
    vec2 pos = TexCoords * 2.0 - 1.0;

    // 3. Compute Panini projection math constants based on FOV
    float fov_rad = radians(u_fov);
    float half_tan = tan(fov_rad * 0.5);
    
    // --- AUTOMATIC SCALE CALCULATOR ---
    // Calculate exactly how much the Panini math shrinks the furthest edge 
    // of the screen, and use that inverse value as our dynamic zoom factor.
    float max_phi = half_tan;
    float edge_scale = (u_d + 1.0) / (u_d + cos(max_phi));
    
    // Apply the automatic scale calibration
    pos /= edge_scale;

    // 4. Calculate the viewing ray projection angles (factoring in aspect ratio)
    float phi = pos.x * half_tan;
    float sin_phi = sin(phi);
    float cos_phi = cos(phi);

    // 5. Transform coordinates using Panini cylinder formulas
    float tan_theta = (pos.y / aspect) * half_tan; 
    
    float x_warp = (u_d + 1.0) * sin_phi / (u_d + cos_phi);
    float y_warp = (u_d + 1.0) * tan_theta / (u_d + cos_phi);

    // 6. Convert back from -1 to 1 space into 0 to 1 UV texture space
    vec2 warpedTexCoords;
    warpedTexCoords.x = (x_warp / half_tan) * 0.5 + 0.5;
    warpedTexCoords.y = ((y_warp * aspect) / half_tan) * 0.5 + 0.5;

    // 7. Safety boundary check: Cut off anything wrapped past image edges
    if (warpedTexCoords.x < 0.0 || warpedTexCoords.x > 1.0 || 
        warpedTexCoords.y < 0.0 || warpedTexCoords.y > 1.0) {
        FragColor = vec4(0.0, 0.0, 0.0, 1.0); // Black bars where data doesn't exist
    } else {
        FragColor = texture(screenTexture, warpedTexCoords);
    }
}