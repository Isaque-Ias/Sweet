from .vector import Vec3

class Camera:
    def __init__(self, name: str, pos: Vec3 = Vec3(0, 0, 0), angle: Vec3 = Vec3(0, 0, 0), fov: float = 60.0, near: float = 0.1, far: float = 1000.0):
        self.name = name
        self.pos = pos
        self.angle = angle
        self.fov = fov
        self.far = far
        self.near = near

        self.alpha_pos = pos
        self.alpha_angle = angle
        self.alpha_fov = fov

    def lerp_pos(self, alpha: float):
        return self.pos * alpha + self.alpha_pos * (1 - alpha)

    def lerp_angle(self, alpha: float):
        return self.angle * alpha + self.alpha_angle * (1 - alpha)

    def lerp_fov(self, alpha: float):
        return self.fov * alpha + self.alpha_fov * (1 - alpha)

class CameraManager:
    _cams: dict["str", Camera] = {
        "main": Camera(name="main")
    }
    _main: str = "main"

    @classmethod
    def update_camera_lerp(cls):
        for camera in cls._cams.values():
            camera.alpha_pos = Vec3(*camera.pos)
            camera.alpha_angle = Vec3(*camera.angle)
            camera.alpha_fov = camera.fov

    @classmethod
    def create_cam(cls, name: str) -> Camera:
        if cls._cams.get(name):
            raise KeyError
        
        cam = Camera(name=name)
        cls._cams[name] = cam
        return cam
    
    @classmethod
    def destroy_cam(cls, name: str) -> None:
        cls._cams.pop(name)

    @classmethod
    def set_main_camera(cls, name: str) -> None:
        cls._main = name
    
    @classmethod
    def get_main_camera(cls) -> Camera:
        return cls._cams[cls._main]

    @classmethod
    def get_camera(cls, name: str) -> Camera:
        return cls._cams[name]