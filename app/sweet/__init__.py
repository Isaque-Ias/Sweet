from . import (
    graphics,
    linalg,
    camera,
    network,
    inputting,
    looping,
    testing,
    entity,
    common,
)

def init():
    looping.GameLoop.setup()

def start():
    looping.GameLoop.start()