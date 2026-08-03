import math
import sweet as sw
from sweet.core.linalg.vector import Vec3

win1 = sw.GLWindow(graphics_device=sw.gfx_device)
win1.position = (0, 150)

win2 = sw.GLWindow(graphics_device=sw.gfx_device)
win1.initialize(width=1366 // 2, height=768 - 300, title="Window 1")
win2.initialize(width=1366 // 2, height=768 - 300, title="Window 2")
win2.position = (1366 // 2, 150)

scene = sw.asset_manager.load_scene(r"temp\russo\Untitled.glb")
curr = 0
enties = scene.entities[0].flatten_leaves_first
while True:
    ent = scene.entities[0].flatten_leaves_first[curr]
    if not ent.get_mesh() is None:
        mex = ent.get_mesh()
        break
        
    curr += 1
player = sw.gameplay.entity.Entity("hi")
scene.add_entity(player)
render = sw.View(sw.gameplay.views.view.UpdatePolicy.EVERY_FRAME)
render2 = sw.View(sw.gameplay.views.view.UpdatePolicy.EVERY_FRAME)

render.set_target(win2)
render.set_viewport((0, 0, 1366 // 2, 768 - 300))
render.set_scene(scene)

render2.set_target(win1)
render2.set_viewport((0, 0, 1366 // 2, 768 - 300))
render2.set_scene(scene)

camera = sw.gameplay.camera.Camera()
camera.position = Vec3(0, 0, 3)

render.activate()
render2.activate()
ref = win2
class Player(sw.GameModel):
    def __init__(self):
        self.height = 50

    def main(self):
        if ref.input.is_key_held(sw.Key.W):
            camera.position.z -= .01 * math.cos(camera.rotation.values[1])
            camera.position.x -= .01 * math.sin(camera.rotation.values[1])
        if ref.input.is_key_held(sw.Key.S):
            camera.position.z += .01 * math.cos(camera.rotation.values[1])
            camera.position.x += .01 * math.sin(camera.rotation.values[1])
        if ref.input.is_key_held(sw.Key.A):
            camera.position.z += .01 * math.sin(camera.rotation.values[1])
            camera.position.x -= .01 * math.cos(camera.rotation.values[1])
        if ref.input.is_key_held(sw.Key.D):
            camera.position.z -= .01 * math.sin(camera.rotation.values[1])
            camera.position.x += .01 * math.cos(camera.rotation.values[1])

        camera.rotation.values[0] += ref.input.get_mouse_delta()[1] * 3.1415 / 180
        camera.rotation.values[1] += ref.input.get_mouse_delta()[0] * 3.1415 / 180

        render.view = camera.view_matrix()
        render.projection = camera.projection_matrix()
        render2.view = camera.view_matrix()
        render2.projection = camera.projection_matrix()

player.inherit_model(Player)
scene.activate()

sw.app.loop.start()