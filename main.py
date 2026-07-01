import math
import sweet as sw
from pathlib import Path
from sweet.vector import Vec3

class Floor(sw.Entity):
    def __init__(self):
        super().__init__((0, 0, 0), tick=True)
        self.pos = Vec3(0, 0, 0)

    def draw(self):
        floor_texture = sw.Resources.texture("plane")
        floor_model = sw.Resources.model("floor")

        sw.entity.Draw.draw_image(
            floor_model,
            floor_texture,
            Vec3(self.pos.x, self.pos.y, self.pos.z),
            Vec3(1000, 1, 1000),
            Vec3(0, 0, 0),
        )


class Player(sw.Entity):
    def __init__(self):
        super().__init__((0, 0, 200), tick=True)
        self.pos: Vec3
        self.angle: Vec3
        self.camera_angle = Vec3(0, 0, 0)
        self.mouse_x, self.mouse_y = sw.inputting.Input.get_mouse_pos()
        self.fov = 70
        self.speed = 1
        self.player_height = 1
        self.velocity = Vec3(0, 0, 0)

        self.cam_distance = 4.0
        self.cam_height = 2.0
        self.cam_shoulder = 1.6

        sw.inputting.Input.set_mouse_visibility(False)

    def tick(self):
        screen_size = sw.Display.screen_size

        # --- mouse look (do this FIRST so movement/camera use the current frame's angle) ---
        mouse_x, mouse_y = sw.inputting.Input.get_mouse_pos()
        mouse_dx = mouse_x - self.mouse_x
        mouse_dy = mouse_y - self.mouse_y
        self.mouse_x, self.mouse_y = mouse_x, mouse_y

        self.camera_angle.x -= mouse_dx * 0.2
        self.camera_angle.y += mouse_dy * 0.2
        self.camera_angle.y = min(89, max(-89, self.camera_angle.y))

        if self.mouse_x == 0 or self.mouse_x == screen_size[0] - 1:
            sw.inputting.Input.set_mouse_pos(screen_size[0] // 2, self.mouse_y)
            self.mouse_x = screen_size[0] // 2
        if self.mouse_y == 0 or self.mouse_y == screen_size[1] - 1:
            sw.inputting.Input.set_mouse_pos(self.mouse_x, screen_size[1] // 2)
            self.mouse_y = screen_size[1] // 2

        # --- gravity / vertical movement ---
        self.velocity.y -= 0.5
        self.pos += self.velocity

        self.pos.y = max(self.pos.y, self.player_height)
        if (
            sw.inputting.Input.get_pressed(sw.inputting.Input.key_code.SPACE)
            and self.pos.y <= self.player_height
        ):
            self.velocity.y = 20

        # --- horizontal movement (relative to camera yaw) ---
        yaw = math.radians(self.camera_angle.x)
        pitch = math.radians(self.camera_angle.y)

        if sw.inputting.Input.get_press(sw.inputting.Input.key_code.W):
            self.pos.x -= math.sin(yaw) * self.speed
            self.pos.z -= math.cos(yaw) * self.speed
        if sw.inputting.Input.get_press(sw.inputting.Input.key_code.S):
            self.pos.x += math.sin(yaw) * self.speed
            self.pos.z += math.cos(yaw) * self.speed
        if sw.inputting.Input.get_press(sw.inputting.Input.key_code.A):
            self.pos.x -= math.cos(yaw) * self.speed
            self.pos.z += math.sin(yaw) * self.speed
        if sw.inputting.Input.get_press(sw.inputting.Input.key_code.D):
            self.pos.x += math.cos(yaw) * self.speed
            self.pos.z -= math.sin(yaw) * self.speed

        if sw.inputting.Input.get_press(sw.inputting.Input.key_code.Q):
            self.fov += 1
        if sw.inputting.Input.get_press(sw.inputting.Input.key_code.E):
            self.fov -= 1

        # --- single, unified over-the-shoulder camera ---
        # forward = Vec3(math.sin(yaw), 0, math.cos(yaw))
        right = Vec3(math.cos(yaw), 0, -math.sin(yaw))

        # look direction including pitch (for pull-back/height as you look up/down)
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

        main_cam = sw.camera.CameraManager.get_main_camera()
        main_cam.pos = cam_pos
        main_cam.angles = self.camera_angle
        main_cam.fov = self.fov

    def draw(self):
        player_texture = sw.Resources.texture("plane")
        player_model = sw.Resources.model("player2")

        sw.entity.Draw.draw_image(
            player_model,
            player_texture,
            self.pos,
            Vec3(1, 1, 1),
            Vec3(0, 0, 0),
        )


class Plane(sw.Entity):
    def __init__(self):
        super().__init__((0, 0, 0), tick=True)
        self.pos = Vec3(0, 0, 0)

    def tick(self):
        if sw.inputting.Input.get_press(sw.inputting.Input.key_code.I):
            self.pos.y -= 1
        if sw.inputting.Input.get_press(sw.inputting.Input.key_code.J):
            self.pos.x -= 1
        if sw.inputting.Input.get_press(sw.inputting.Input.key_code.K):
            self.pos.y += 1
        if sw.inputting.Input.get_press(sw.inputting.Input.key_code.L):
            self.pos.x += 1
        if sw.inputting.Input.get_press(sw.inputting.Input.key_code.N):
            self.pos.z += 1
        if sw.inputting.Input.get_press(sw.inputting.Input.key_code.M):
            self.pos.z -= 1

    def draw(self):
        plane_texture = sw.Resources.texture("plane")
        plane_model = sw.Resources.model("plane")

        sw.entity.Draw.draw_image(
            plane_model,
            plane_texture,
            Vec3(self.pos.x, self.pos.y, self.pos.z),
            Vec3(1, 1, 1),
            Vec3(0, 0, 0),
        )


if __name__ == "__main__":
    sw.Display.resizable(True)
    screen_size = sw.Display.screen_size
    sw.Display.size((screen_size[0], screen_size[1]))
    sw.Display.background((135, 206, 250, 255))

    sw.init()

    CWD = Path.cwd()
    sw.Resources.load_assets(CWD / "assets.json")
    BUILD = CWD / "src" / "sweet" / "build"

    Floor()
    Plane()
    Player()

    sw.run()
