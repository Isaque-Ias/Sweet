#version 460 core

in vec2 v_uv;

layout(location = 0) out vec4 Blur_Out;

uniform sampler2D Present_Light;

void main()
{
    vec2 center = vec2(0.5, 0.5);
    float dist = distance(v_uv, center);
    
    // Adjust where the blur starts and spreads
    float innerRadius = 0.25; 
    float outerRadius = 0.85; 
    float blurFactor = smoothstep(innerRadius, outerRadius, dist);

    vec3 color = vec3(0.0);

    if (blurFactor <= 0.0)
    {
        color = texture(Present_Light, v_uv).rgb;
    }
    else
    {
        vec2 texelSize = 1.0 / vec2(textureSize(Present_Light, 0));
        float maxBlurPixels = 100.0; // Control total blur size here
        float currentMaxRadius = blurFactor * maxBlurPixels;

        vec3 accColor = vec3(0.0);
        float totalWeight = 0.0;

        // Vogel Spiral (Golden Angle) - distributes samples organically 
        // without any grid lines, rings, moiré, or random noise grain.
        const int SAMPLE_COUNT = 24;
        const float GOLDEN_ANGLE = 2.39996323; // ~137.5 degrees in radians

        for (int i = 0; i < SAMPLE_COUNT; ++i)
        {
            // Calculate organic disk distribution
            float r = sqrt(float(i) + 0.5) / sqrt(float(SAMPLE_COUNT));
            float theta = float(i) * GOLDEN_ANGLE;
            
            vec2 offset = vec2(cos(theta), sin(theta)) * r * currentMaxRadius * texelSize;
            
            // Weight samples slightly more towards the inner core of the blur disk
            float weight = 1.0 - (r * 0.2);
            
            accColor += texture(Present_Light, v_uv + offset).rgb * weight;
            totalWeight += weight;
        }

        color = accColor / totalWeight;
    }

    // Tone mapping and gamma correction
    color = color / (color + vec3(1.0));
    color = pow(color, vec3(1.0 / 2.2));
    
    Blur_Out = vec4(color, 1.0);
}