class Scene:
    def __init__(self):
        self.children = []

class SceneManager:
    _scenes: dict[str, Scene] = {}

    @classmethod
    def new_scene(cls, name: str):
        scene = Scene()
        cls._scenes[name] = scene
        return scene
    
    def load_model(self):
        pass

    def load_texture(self):
        pass

    def load_scene(self):
        pass
