import sweet as sw


window = sw.Window("aa", (300, 100), (10, 100))
window.config = {
    "title": "abc",
    "resizable": True
}
window.show()

window2 = sw.Window("bb", (300, 200), (500, 400))
window2.show()
window2.close()
window2.show()

scene = sw.Assets.load_scene(r"temp\russo\pbr_sphere.glb")
print(scene)
sw.start()