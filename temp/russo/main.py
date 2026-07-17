import math
import sweet as sw
from pathlib import Path
from sweet.vector import Vec3
from sweet.inputting import Input

sw.Display.resizable(True)
screen_size = sw.Display.screen_size
sw.Display.size((screen_size[0], screen_size[1]))
sw.Display.background((135, 206, 250, 255))

sw.init()

CWD = Path.cwd()
PROJECT = CWD / "temp" / "russo"

sw.System.set_config(PROJECT / "config" / "config.json")

sw.Resources.load_assets(PROJECT / "assets.json")

BUILD = CWD / "src" / "sweet" / "build"
panini = sw.Shader.get("panini")
panini_program = panini.program
panini_fbo = sw.Shader.new_fbo(screen_size)

from tracker import FaceTracker
from bodytracker import BodyTracker, SKELETON_CONNECTIONS

tracker = BodyTracker(
    show_window=True,
    show_landmarks=True,
)
import numpy as np

def look_at(pos_a, pos_b, roll: float = 0.0):
    """
    Calcula (pitch, yaw, roll) para que o eixo local +Z do sprite
    (o eixo de "profundidade") aponte de pos_a para pos_b, seguindo
    a mesma convenção de rotação usada em create_model_matrix
    (vetores-linha, R = Rx @ Ry @ Rz).

    Args:
        pos_a: posição de origem (x, y, z)
        pos_b: posição alvo (x, y, z)
        roll: rotação livre em torno do próprio eixo de mira (não afeta
              a direção apontada, default 0.0)

    Returns:
        (pitch, yaw, roll) em radianos, prontos para usar em
        sprite.rotation = look_at(a, b)
    """
    d = np.asarray(pos_b, dtype=np.float32) - np.asarray(pos_a, dtype=np.float32)
    dist = np.linalg.norm(d)
    if dist < 1e-9:
        # A e B são o mesmo ponto: não há direção definida, mantém rotação neutra
        return 0.0, 0.0, roll

    dx, dy, dz = d / dist

    # Derivado invertendo: forward_Z' = (sin(yaw)*cos(pitch), -sin(pitch), cos(yaw)*cos(pitch))
    pitch = np.arcsin(np.clip(-dy, -1.0, 1.0))
    yaw = np.arctan2(dx, dz)

    return pitch, yaw, roll

class Player(sw.Entity):
    def __init__(self):
        super().__init__((0, 0, 0))
        self.pos: Vec3
        self.camera_angle = Vec3(0, 0, 0)
        self.mouse_x, self.mouse_y = Input.get_mouse_pos()
        self.fov = 70
        self.speed = 10
        self.player_height = 1
        self.velocity = Vec3(0, 0, 0)

        self.third_person = True
        self.cam_distance = 4.0
        self.cam_height = 2.0
        self.cam_shoulder = 1.6

        self.texture = sw.Resources.texture("hand2")
        self.model = sw.Resources.model("hand")

        Input.set_mouse_visibility(False)
        Input.set_mouse_exclusivity(True)

    def tick(self):
        # --- toggle third person ---
        if Input.is_key_pressed(Input.key_code.F5):
            self.third_person = not self.third_person
            
        # --- mouse look ---
        mouse_x, mouse_y = Input.get_mouse_pos()
        mouse_dx = mouse_x - self.mouse_x
        mouse_dy = mouse_y - self.mouse_y
        self.mouse_x, self.mouse_y = mouse_x, mouse_y

        self.camera_angle.x -= mouse_dx * 0.2
        self.camera_angle.y += mouse_dy * 0.2
        self.camera_angle.y = min(89, max(-89, self.camera_angle.y))

        self.velocity.y -= 0.5
        self.pos += self.velocity

        self.pos.y = max(self.pos.y, self.player_height)
        if (
            Input.is_key_pressed(Input.key_code.SPACE)
            and self.pos.y <= self.player_height
        ):
            self.velocity.y = 20

        yaw = math.radians(self.camera_angle.x)
        pitch = math.radians(self.camera_angle.y)

        if Input.is_key_held(Input.key_code.W):
            self.pos.x -= math.sin(yaw) * self.speed * sw.Time.delta()
            self.pos.z -= math.cos(yaw) * self.speed * sw.Time.delta()
        if Input.is_key_held(Input.key_code.S):
            self.pos.x += math.sin(yaw) * self.speed * sw.Time.delta()
            self.pos.z += math.cos(yaw) * self.speed * sw.Time.delta()
        if Input.is_key_held(Input.key_code.A):
            self.pos.x -= math.cos(yaw) * self.speed * sw.Time.delta()
            self.pos.z += math.sin(yaw) * self.speed * sw.Time.delta()
        if Input.is_key_held(Input.key_code.D):
            self.pos.x += math.cos(yaw) * self.speed * sw.Time.delta()
            self.pos.z -= math.sin(yaw) * self.speed * sw.Time.delta()

        if Input.is_key_held(Input.key_code.Q):
            self.fov += 1
        if Input.is_key_held(Input.key_code.E):
            self.fov -= 1

        if self.third_person:
            right = Vec3(math.cos(yaw), 0, -math.sin(yaw))

            look_dir = Vec3(
                math.sin(yaw) * math.cos(pitch),
                math.sin(pitch),
                math.cos(yaw) * math.cos(pitch),
            )

            cam_pos = self.pos
            cam_pos += Vec3(0, self.cam_height, 0)
            right_dist = right * self.cam_shoulder
            back_dist = look_dir * self.cam_distance
            cam_pos += right_dist + back_dist
        else:
            cam_pos = self.pos
            cam_pos += Vec3(0, self.player_height, 0)

        main_cam = sw.camera.CameraManager.get_main_camera()
        main_cam.pos = cam_pos
        main_cam.angles = self.camera_angle
        main_cam.fov = self.fov

    def draw(self):
        if self.third_person:
            sw.entity.Draw.draw_image(
                self.model,
                self.texture,
                self.pos,
            )

class Floor(sw.Entity):
    def __init__(self):
        super().__init__((0, -100, 0))
        self.texture = sw.Resources.texture("hand")
        self.model = sw.Resources.model("handd")
        self.time_lim = 3
        self.time = 0
        self.lerp_start = self.pos
        self.lerp_end = self.pos
        self.lerp_rot_start = self.angle
        self.lerp_rot_end = self.angle
        self.part = {}
        self.bones = {}
        self.rel = Vec3(0, 0, 0)
        self.min_y = 10000

    def tick(self):
        self.time += 1
        if self.time >= self.time_lim:
            self.lerp_start = Vec3(self.lerp_end.x, self.lerp_end.y, self.lerp_end.z)
            self.lerp_rot_start = Vec3(self.lerp_rot_end.x, self.lerp_rot_end.y, self.lerp_rot_end.z)
            
            tracker.track()
            if tracker.body_detected:
                for part in tracker.landmarks.keys():
                    body_part = tracker.landmarks[part]
                    self.part[part] = Vec3(body_part.x, -body_part.y, body_part.z) * 20
                    if tracker.hip_position:
                        self.rel = Vec3(-tracker.hip_position[0], tracker.hip_position[1], -tracker.hip_position[2]) * 20

            self.time = 0

        t = self.time / self.time_lim
        self.pos = self.lerp_start * (1 - t) + self.lerp_end * t
        self.angle = self.lerp_rot_start * (1 - t) + self.lerp_rot_end * t

    def draw(self):
        for part in self.part.values():
            sw.Draw.render(
                self.model,
                self.texture,
                part - self.rel,
                scale=Vec3(.1, .1, .1)
            )
            if (part - self.rel).y < self.min_y:
                self.min_y = (part - self.rel).y

        for part in SKELETON_CONNECTIONS:
            start = self.part[part[0]]
            end = self.part[part[1]]
            median = (start + end) / 2
            dist = (start - end).magnitude() / 2
            look_at_dir = look_at(start.unp(), end.unp())
            sw.Draw.render(
                self.model,
                self.texture,
                median - self.rel,
                scale=Vec3(.1, .1, dist),
                angle=Vec3(*look_at_dir) * 180 / 3.1415
            )

        sw.Draw.render(
            self.model,
            self.texture,
            Vec3(0, self.min_y, 0),
            scale=Vec3(100, .1, 100)
        )

if __name__ == "__main__":
    global player
    player = Player()
    Floor()
    sw.run()
