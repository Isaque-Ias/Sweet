class Light:
    def __init__(self, light_type: str="point"):
        self.type = light_type
        self.color = (1.0, 1.0, 1.0)
        self.intensity = 1.0