#version 430 core

// Your incoming vertex layout
in vec2 v_texcoord;
in vec4 v_color;
in vec3 v_normal;
in vec3 v_frag_pos;
in vec3 v_cam_pos;

uniform sampler2D uTexture;
out vec4 FragColor;

// --- RAY TRACING DATA STRUCTURES ---
struct Ray {
    vec3 origin;
    vec3 direction;
};

struct Material {
    vec3 color;
    float specular;
    float reflectivity;
};

struct HitRecord {
    bool hit;
    float t;
    vec3 position;
    vec3 normal;
    Material material;
};

const float INF = 1e20;
const int MAX_BOUNCES = 3;

// --- INTERSECTION FUNCTIONS ---
HitRecord intersectSphere(Ray ray, vec3 center, float radius, Material mat) {
    HitRecord record;
    record.hit = false;
    
    vec3 oc = ray.origin - center;
    float a = dot(ray.direction, ray.direction);
    float b = 2.0 * dot(oc, ray.direction);
    float c = dot(oc, oc) - radius * radius;
    float discriminant = b * b - 4.0 * a * c;
    
    if (discriminant > 0.0) {
        float t = (-b - sqrt(discriminant)) / (2.0 * a);
        if (t > 0.001) {
            record.hit = true;
            record.t = t;
            record.position = ray.origin + t * ray.direction;
            record.normal = normalize(record.position - center);
            record.material = mat;
            return record;
        }
    }
    return record;
}

HitRecord intersectPlane(Ray ray, float height, Material mat) {
    HitRecord record;
    record.hit = false;
    
    if (abs(ray.direction.y) > 0.001) {
        float t = (height - ray.origin.y) / ray.direction.y;
        if (t > 0.001) {
            record.hit = true;
            record.t = t;
            record.position = ray.origin + t * ray.direction;
            record.normal = vec3(0.0, 1.0, 0.0);
            
            float check = mod(floor(record.position.x) + floor(record.position.z), 2.0);
            record.material = mat;
            if (check == 0.0) {
                record.material.color *= 0.5;
            }
            return record;
        }
    }
    return record;
}

// --- SCENE EVALUATION ---
HitRecord checkScene(Ray ray) {
    HitRecord closestHit;
    closestHit.hit = false;
    closestHit.t = INF;
    
    // Internal Ray Traced Materials
    Material sphereMat = Material(vec3(0.9, 0.2, 0.2), 50.0, 0.4); // Shiny Red Sphere
    Material floorMat  = Material(vec3(0.8, 0.8, 0.8), 10.0, 0.1); // Matte Floor
    
    // Trace against internal geometric shapes
    HitRecord sphereHit = intersectSphere(ray, vec3(0.0, 0.0, -5.0), 1.5, sphereMat);
    if (sphereHit.hit && sphereHit.t < closestHit.t) {
        closestHit = sphereHit;
    }
    
    HitRecord floorHit = intersectPlane(ray, -1.5, floorMat);
    if (floorHit.hit && floorHit.t < closestHit.t) {
        closestHit = floorHit;
    }
    
    return closestHit;
}

// --- MAIN ROUTINE ---
void main()
{
    // 1. Fetch texture and color background from your layout
    vec4 texColor = texture(uTexture, v_texcoord) * v_color;

    // 2. Initialize primary ray using your World Space inputs
    Ray ray;
    ray.origin = v_cam_pos;                       // Starts at camera positions
    ray.direction = normalize(v_frag_pos - v_cam_pos); // Shoots directly through fragment world position
    
    // Light settings matched to your configuration (using camera position as light)
    vec3 lightPos = v_cam_pos;
    vec3 lightColor = vec3(1.0);
    float ambientStrength = 0.25;

    vec3 rayTracedColor = vec3(0.0);
    float reflectionWeight = 1.0;

    // 3. Ray Tracing Loop
    for (int bounce = 0; bounce < MAX_BOUNCES; bounce++) {
        HitRecord hit = checkScene(ray);
        
        if (!hit.hit) {
            // Fallback: If a ray misses internal objects, sample your container mesh surface colors
            vec3 fallbackMeshLighting = (ambientStrength + max(dot(normalize(v_normal), normalize(lightPos - v_frag_pos)), 0.0)) * lightColor;
            vec3 fallbackColor = fallbackMeshLighting * texColor.rgb;
            
            rayTracedColor += fallbackColor * reflectionWeight;
            break;
        }
        
        // Calculate Light Vectors for ray trace geometry
        vec3 lightDir = normalize(lightPos - hit.position);
        vec3 viewDir = normalize(ray.origin - hit.position);
        
        // Shadow Trace
        Ray shadowRay;
        shadowRay.origin = hit.position + hit.normal * 0.001;
        shadowRay.direction = lightDir;
        HitRecord shadowHit = checkScene(shadowRay);
        
        float shadowFactor = 1.0;
        if (shadowHit.hit && shadowHit.t < length(lightPos - hit.position)) {
            shadowFactor = 0.0;
        }
        
        // Ray Traced Shading Calculations
        vec3 ambient = ambientStrength * lightColor * hit.material.color;
        
        float diff = max(dot(hit.normal, lightDir), 0.0);
        vec3 diffuse = diff * lightColor * hit.material.color;
        
        vec3 halfDir = normalize(lightDir + viewDir);
        float spec = pow(max(dot(hit.normal, halfDir), 0.0), hit.material.specular);
        vec3 specular = vec3(1.0) * spec;
        
        vec3 localColor = ambient + (diffuse + specular) * shadowFactor;
        
        rayTracedColor += localColor * reflectionWeight * (1.0 - hit.material.reflectivity);
        
        // Compute Bounce Ray
        reflectionWeight *= hit.material.reflectivity;
        if (reflectionWeight < 0.01) break;
        
        ray.origin = hit.position + hit.normal * 0.001;
        ray.direction = reflect(ray.direction, hit.normal);
    }
    
    // Output final results
    FragColor = vec4(rayTracedColor, texColor.a);
}
