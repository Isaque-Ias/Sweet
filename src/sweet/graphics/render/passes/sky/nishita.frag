#version 330 core

out vec4 FragColor;
in vec2 v_uv;

// Uniforms
uniform sampler2D Sky_Light;        // Texture from the previous lighting pass
uniform mat4 sw_InvView;            // Inverse View Matrix (Camera-to-World)
uniform mat4 sw_InvProjection;      // Inverse Projection Matrix (Clip-to-View)

uniform vec3 sw_SunDirection;
uniform vec3 sw_SunIntensity;

const float EARTH_RADIUS = 6371000.0; // 6,371 km
const float ATM_RADIUS   = 6471000.0; // 6,471 km
const float HR           = 8000.0;    // Rayleigh scale height (8 km)
const float HM           = 1200.0;    // Mie scale height (1.2 km)

const vec3 BETA_R = vec3(5.8e-6, 1.35e-5, 3.31e-5);
const vec3 BETA_M = vec3(4.0e-6);
const float G     = 0.76;

vec2 raySphereIntersect(vec3 ro, vec3 rd, float radius) {
    float b = dot(ro, rd);
    float c = dot(ro, ro) - radius * radius;
    float d = b * b - c;
    if (d < 0.0) return vec2(-1.0);
    return vec2(-b - sqrt(d), -b + sqrt(d));
}

float densityRayleigh(float h) { return exp(-h / HR); }
float densityMie(float h)      { return exp(-h / HM); }

void main() {
    vec4 sceneColor = texture(Sky_Light, v_uv);

    // If the pixel contains geometry from the lighting pass, keep it
    if (sceneColor.a >= 0.1) {
        FragColor = sceneColor;
        return;
    }

    // Otherwise, render the Nishita sky on the background/transparent pixels
    vec3 sw_CameraPosition = sw_InvView[3].xyz;

    // Reconstruct world-space ray direction
    vec4 ndc = vec4(v_uv * 2.0 - 1.0, 1.0, 1.0);
    vec4 viewRay = sw_InvProjection * ndc;
    viewRay = viewRay / viewRay.w;
    vec3 rayDir = normalize(mat3(sw_InvView) * viewRay.xyz);

    vec3 rayOrigin = sw_CameraPosition + vec3(0.0, EARTH_RADIUS + 1000, 0.0);

    vec2 hitAtm = raySphereIntersect(rayOrigin, rayDir, ATM_RADIUS);
    if (hitAtm.y < 0.0) {
        FragColor = vec4(0.0, 0.0, 0.0, 1.0);
        return;
    }

    float tMin = max(hitAtm.x, 0.0);
    float tMax = hitAtm.y;

    vec2 hitGround = raySphereIntersect(rayOrigin, rayDir, EARTH_RADIUS);
    if (hitGround.x > 0.0) {
        tMax = hitGround.x;
    }

    float cosTheta = dot(rayDir, sw_SunDirection);
    float phaseR = (3.0 / (16.0 * 3.14159265)) * (1.0 + cosTheta * cosTheta);
    float phaseM = (3.0 / (8.0 * 3.14159265)) * ((1.0 - G * G) * (1.0 + cosTheta * cosTheta)) / 
                   ((2.0 + G * G) * pow(1.0 + G * G - 2.0 * G * cosTheta, 1.5));

    const int STEPS = 16;
    const int LIGHT_STEPS = 8;
    float stepSize = (tMax - tMin) / float(STEPS);
    
    vec3 sumR = vec3(0.0);
    vec3 sumM = vec3(0.0);
    float opticalDepthR = 0.0;
    float opticalDepthM = 0.0;

    for (int i = 0; i < STEPS; ++i) {
        vec3 samplePos = rayOrigin + rayDir * (tMin + (float(i) + 0.5) * stepSize);
        float height = length(samplePos) - EARTH_RADIUS;

        float hr = densityRayleigh(height) * stepSize;
        float hm = densityMie(height) * stepSize;

        opticalDepthR += hr;
        opticalDepthM += hm;

        vec2 hitSunAtm = raySphereIntersect(samplePos, sw_SunDirection, ATM_RADIUS);
        float lightStepSize = hitSunAtm.y / float(LIGHT_STEPS);
        float lightOpticalDepthR = 0.0;
        float lightOpticalDepthM = 0.0;

        for (int j = 0; j < LIGHT_STEPS; ++j) {
            vec3 lightSamplePos = samplePos + sw_SunDirection * ((float(j) + 0.5) * lightStepSize);
            float lightHeight = length(lightSamplePos) - EARTH_RADIUS;
            lightOpticalDepthR += densityRayleigh(lightHeight) * lightStepSize;
            lightOpticalDepthM += densityMie(lightHeight) * lightStepSize;
        }

        vec3 tau = BETA_R * (opticalDepthR + lightOpticalDepthR) + 
                   BETA_M * 1.1 * (opticalDepthM + lightOpticalDepthM);
        vec3 attenuation = exp(-tau);

        sumR += hr * attenuation;
        sumM += hm * attenuation;
    }

    vec3 radiance = sw_SunIntensity * (sumR * BETA_R * phaseR + sumM * BETA_M * phaseM);

    // Output the calculated atmospheric scattering to the background
    FragColor = vec4(radiance, 1.0);
}