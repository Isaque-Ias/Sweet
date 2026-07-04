import sweet as sw
from pathlib import Path

sw.Display.resizable(True)
screen_size = sw.Display.screen_size
sw.Display.size((screen_size[0], screen_size[1]))
sw.Display.background((135, 206, 250, 255))

sw.init()

CWD = Path.cwd()
PROJECT = CWD / "temp" / "russo"
sw.Resources.load_assets(PROJECT / "assets.json")
BUILD = CWD / "src" / "sweet" / "build"
panini = sw.Shader.add(BUILD / "__panini__.vsh", BUILD / "__panini__.fsh", "panini")
panini_program = panini.program
panini_fbo = sw.Shader.new_fbo(screen_size)

class test(sw.Entity):
    def __init__(self):
        super().__init__()
        
    def tick(self):
        pass

    def draw(self):
        pass

if __name__ == "__main__":

    test()
    sw.run()
