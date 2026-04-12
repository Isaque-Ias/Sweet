class Cam:
    def __init__(self, pos: tuple, scale: tuple, angle: int, name: str) -> None:
        self.set_name(name)
        self.set_pos(pos)
        self.set_scale(scale)
        self.set_angle(angle)

    def set_pos(self, pos: tuple) -> None:
        self._pos = pos

    def set_scale(self, scale: tuple) -> None:
        self._scale = scale

    def set_angle(self, angle: str) -> None:
        self._angle = angle

    def set_name(self, name: str) -> None:
        self._name = name

    def get_pos(self) -> tuple:
        return self._pos

    def get_scale(self) -> tuple:
        return self._scale

    def get_angle(self) -> int:
        return self._angle

    def get_name(self) -> str:
        return self._name

class Camera:
    _cams: dict[Cam] = {"main": Cam([0, 0], [1, 1], 0, "main")}
    _main: str = "main"

    @classmethod
    def create_cam(cls, name: str) -> Cam:
        if cls._cams.get(name):
            raise KeyError
        
        cam = Cam([0, 0], [0, 0], 0, name)
        cls._cams[name] = cam
        return cam
    
    @classmethod
    def destroy_cam(cls, name: str) -> None:
        cls._cams.pop(name)

    @classmethod
    def set_main_camera(cls, name: str) -> None:
        cls._main = name
    
    @classmethod
    def get_main_camera(cls) -> Cam:
        return cls._cams[cls._main]

    @classmethod
    def get_camera(cls, name: str) -> Cam:
        return cls._cams[name]