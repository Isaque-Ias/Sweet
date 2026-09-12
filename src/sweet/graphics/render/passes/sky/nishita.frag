#version 330
in vec3 v_pos;
out vec4 fragColor;

uniform vec3 sw_SunDirection;
uniform vec3 sw_SunIntensity;

const float PI = 3.14159265359;

const float PLANET_RADIUS     = 6371000.0;
const float ATMOSPHERE_RADIUS = 6471000.0;

const vec3  RAYLEIGH_COEFF   = vec3(5.5e-6, 13.0e-6, 22.4e-6);
const float MIE_COEFF        = 21e-6;
const float RAYLEIGH_SCALE_H = 8000.0;   // rayleigh density falls off ~e-folding over 8km
const float MIE_SCALE_H      = 1200.0;   // mie (aerosols) is far more concentrated near ground
const float MIE_G            = 0.76;     // forward-scattering anisotropy

const int PRIMARY_STEPS = 32;
const int LIGHT_STEPS   = 16;

vec2 raySphereIntersect(vec3 ro, vec3 rd, float radius) {
    float b = dot(ro, rd);
    float c = dot(ro, ro) - radius * radius;
    float disc = b * b - c;
    if (disc < 0.0) return vec2(1e10, -1e10);
    float s = sqrt(disc);
    return vec2(-b - s, -b + s);
}

float rayleighPhase(float cosTheta) {
    return 3.0 / (16.0 * PI) * (1.0 + cosTheta * cosTheta);
}

float miePhase(float cosTheta, float g) {
    float g2 = g * g;
    float num = (1.0 - g2) * (1.0 + cosTheta * cosTheta);
    float den = (2.0 + g2) * pow(1.0 + g2 - 2.0 * g * cosTheta, 1.5);
    return (3.0 / (8.0 * PI)) * num / den;
}

// Accumulated (rayleigh, mie) optical depth from `ro` toward the sun,
// marching until the ray exits the atmosphere shell.
void opticalDepthToSun(vec3 ro, vec3 sunDir, out float depthR, out float depthM) {
    depthR = 0.0;
    depthM = 0.0;

    vec2 hit = raySphereIntersect(ro, sunDir, ATMOSPHERE_RADIUS);
    if (hit.x > hit.y) return;

    float rayLen = hit.y;
    float stepSize = rayLen / float(LIGHT_STEPS);
    float t = 0.0;

    for (int i = 0; i < LIGHT_STEPS; ++i) {
        vec3 pos = ro + sunDir * (t + stepSize * 0.5);
        float height = length(pos) - PLANET_RADIUS;

        if (height < 0.0) {
            // Sample point is under the horizon relative to the sun ->
            // the planet itself blocks all light along this path.
            depthR = 1e10;
            depthM = 1e10;
            return;
        }

        depthR += exp(-height / RAYLEIGH_SCALE_H) * stepSize;
        depthM += exp(-height / MIE_SCALE_H) * stepSize;
        t += stepSize;
    }
}

vec3 computeScattering(vec3 rayOrigin, vec3 rayDir, vec3 sunDir) {
    vec2 hit = raySphereIntersect(rayOrigin, rayDir, ATMOSPHERE_RADIUS);
    if (hit.x > hit.y) return vec3(0.0);

    // Clip the march to the ground if we're looking down at the planet.
    vec2 groundHit = raySphereIntersect(rayOrigin, rayDir, PLANET_RADIUS);
    float tMax = hit.y;
    if (groundHit.x > 0.0 && groundHit.x < tMax) {
        tMax = groundHit.x;
    }

    float tMin = max(hit.x, 0.0);
    float rayLen = tMax - tMin;
    if (rayLen <= 0.0) return vec3(0.0);

    float stepSize = rayLen / float(PRIMARY_STEPS);

    vec3 totalRayleigh = vec3(0.0);
    vec3 totalMie = vec3(0.0);
    float opticalDepthR = 0.0;
    float opticalDepthM = 0.0;

    float cosTheta = dot(rayDir, sunDir);
    float phaseR = rayleighPhase(cosTheta);
    float phaseM = miePhase(cosTheta, MIE_G);

    float t = tMin;
    for (int i = 0; i < PRIMARY_STEPS; ++i) {
        vec3 samplePos = rayOrigin + rayDir * (t + stepSize * 0.5);
        float height = length(samplePos) - PLANET_RADIUS;
        if (height < 0.0) break;

        float hR = exp(-height / RAYLEIGH_SCALE_H) * stepSize;
        float hM = exp(-height / MIE_SCALE_H) * stepSize;
        opticalDepthR += hR;
        opticalDepthM += hM;

        float lightDepthR, lightDepthM;
        opticalDepthToSun(samplePos, sunDir, lightDepthR, lightDepthM);

        vec3 tau = RAYLEIGH_COEFF * (opticalDepthR + lightDepthR)
                 + (MIE_COEFF * 1.1) * (opticalDepthM + lightDepthM);
        vec3 attenuation = exp(-tau);

        totalRayleigh += attenuation * hR;
        totalMie      += attenuation * hM;

        t += stepSize;
    }

    return sw_SunIntensity * (
        totalRayleigh * RAYLEIGH_COEFF * phaseR +
        totalMie * MIE_COEFF * phaseM
    );
}

void main() {
    vec3 rayDir = normalize(v_pos);
    vec3 rayOrigin = vec3(0.0, PLANET_RADIUS + 1000.0, 0.0);

    vec3 color = computeScattering(rayOrigin, rayDir, normalize(sw_SunDirection));

    fragColor = vec4(color, 1.0);
}
