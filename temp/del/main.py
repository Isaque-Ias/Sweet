import sweet as sw
from pathlib import Path
from objects import *

if __name__ == "__main__":
    sw.Display.resizable(True)
    screen_size = sw.Display.screen_size
    sw.Display.size((screen_size[0], screen_size[1]))
    sw.Display.background((135, 206, 250, 255))

    sw.init()

    CWD = Path.cwd()
    PROJECT = CWD / "temp" / "del"
    sw.Resources.load_assets(PROJECT / "assets.json")
    BUILD = CWD / "src" / "sweet" / "build"

    Player()

    walker = WalkingCube(sw.Vec3(0, 0, -10), speed=sw.Vec3(1, 0, 0))
    WalkingCube(sw.Vec3(2, 0, -10), walker, speed=sw.Vec3(0, 0, -1))
    Cube(sw.Vec3(-2, 0, -10), walker)
    Cube(sw.Vec3(0, 0, -12), walker)
    WalkingCube(sw.Vec3(0, 0, -8), walker, speed=sw.Vec3(1, 0, 1))

    Cube(sw.Vec3(5, -1, -10))

    sw.run()
