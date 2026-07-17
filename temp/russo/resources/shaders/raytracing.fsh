#version 300 es
precision highp float;

in vec2 v_uv;
out vec4 fragColor;

// Uniforms for window resizing
uniform vec2 u_resolution; 

// Define a Ray structure
struct Ray {
    vec3 origin;
    vec3 direction;
};

// Define a Sphere structure
struct Sphere {
    vec3 center;
    float radius;
    vec3 color;
};

// Setup a simple scene
const Sphere sphere = Sphere(vec3(0.0, 0.0, -5.0), 1.0, vec3(0.9, 0.2, 0.2));
const vec3 lightDir = normalize(vec3(0.5, 1.0, 0.3));
const vec3 backgroundColor = vec3(0.1, 0.1, 0.15);

// Ray-Sphere Intersection math
// Returns the distance 't' along the ray, or -1.0 if it misses
float intersectSphere(Ray ray, Sphere sphere) {
    vec3 oc = ray.origin - sphere.center;
    float b = dot(oc, ray.direction);
    float c = dot(oc, oc) - sphere.radius * sphere.radius;
    float discriminant = b * b - c;
    
    if (discriminant < 0.0) {
        return -1.0; // Miss
    }
    
    // Return the closest intersection point
    float t = -b - sqrt(discriminant);
    return (t > 0.0) ? t : -1.0;
}

void main() {
    // 1. Fix aspect ratio so the sphere isn't stretched
    float aspect = u_resolution.x / u_resolution.y;
    vec2 uv = v_uv;
    uv.x *= aspect;

    // 2. Initialize Camera/Ray (Perspective projection)
    Ray ray;
    ray.origin = vec3(0.0, 0.0, 0.0);                    // Camera at origin
    ray.direction = normalize(vec3(uv, -1.0));          // Looking down -Z

    // 3. Trace Ray against the scene
    float t = intersectSphere(ray, sphere);

    // 4. Shading
    if (t > 0.0) {
        // Hit point and Surface Normal
        vec3 hitPoint = ray.origin + t * ray.direction;
        vec3 normal = normalize(hitPoint - sphere.center);

        // Diffuse lighting (Lambertian)
        float diffuse = max(dot(normal, lightDir), 0.0);
        
        // Ambient light hack for depth
        float ambient = 0.1;
        
        vec3 finalColor = sphere.color * (diffuse + ambient);
        fragColor = vec4(finalColor, 1.0);
    } else {
        // Missed everything -> draw background
        fragColor = vec4(backgroundColor, 1.0);
    }
}