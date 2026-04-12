import time
from OpenGL.GL import *
from PIL import Image
import numpy as np
import os
import json

class Testing:
    OUTPUT_DIR = "texture_dump"

    MAX_TEXTURE_ID = 1000
    MAX_ATLAS_WIDTH = 4096
    PADDING = 2

    _times = {}
    _temp = {}
    def_cap = 10

    @classmethod
    def set_perf_cap(cls, name, cap):
        if cls._times.get(name) == None:
            cls._times[name] = {"data": [], "cap": cap}
        else:
            cls._times[name]["cap"] = cap

    @classmethod
    def set_def_cap(cls, cap):
        cls._def_cap = cap

    @classmethod
    def get_names(cls):
        return cls._times.keys()

    @classmethod
    def get_tick(cls, name):
        return cls._times[name]
        
    @classmethod
    def tick_time_start(cls, name):
        cls._temp[name] = time.perf_counter()

    @classmethod
    def tick_time_end(cls, name):
        end = time.perf_counter()
        start = cls._temp[name]

        if cls._times.get(name) == None:
            cls._times[name] = {"data": [], "cap": cls._def_cap}

        if len(cls._times[name]["data"]) >= cls._times[name]["cap"]:
            cls._times[name]["data"].pop(0)
            if cls._times[name].get("start") is not None:
                cls._times[name]["start"] -= 1
                if cls._times[name]["start"] < 0:
                    cls._times[name]["exceeded"] = True

        cls._times[name]["data"].append(end - start)
        
        cls._temp.pop(name)

    @classmethod
    def get_average(cls, name):
        return sum(cls._times[name]["data"]) / len(cls._times[name]["data"])
    
    @classmethod
    def cummulation_start(cls):
        for name in cls.get_names():
            tick = cls.get_tick(name)
            tick["start"] = len(tick["data"])
            
    @classmethod
    def cummulation_end(cls):
        for name in cls.get_names():
            tick = cls.get_tick(name)
            if tick.get("start") is not None:
                start = tick["start"]
                total = sum(tick["data"][start:])
                if tick.get("cummulation") == None:
                    tick["cummulation"] = [total]
                else:
                    tick["cummulation"].append(total)
                    if len(tick["cummulation"]) > 10:
                        tick["cummulation"].pop(0)

    @classmethod
    def get_relatory(cls):
        if len(cls._times) == 0:
            return "No timings were made."
        message = ""
        for key in cls._times.keys():
            message = message + f"{format(cls.get_average(key), '.20f')} seconds on \"{key}\" in {len(cls._times[key]["data"])} tries.\n"
            cummulation = cls._times[key].get("cummulation")
            if cummulation is not None:
                message = message + f"Cummulation: {sum(cummulation) / len(cummulation)}\n"
        return message
    
    @classmethod
    def dump_textures(cls, dir=None):
        if dir == None:
            dir = cls.OUTPUT_DIR
        os.makedirs(dir, exist_ok=True)

        textures = []

        for tex_id in range(1, cls.MAX_TEXTURE_ID + 1):

            if not glIsTexture(tex_id):
                continue

            glBindTexture(GL_TEXTURE_2D, tex_id)

            width = glGetTexLevelParameteriv(GL_TEXTURE_2D, 0, GL_TEXTURE_WIDTH)
            height = glGetTexLevelParameteriv(GL_TEXTURE_2D, 0, GL_TEXTURE_HEIGHT)

            if width <= 0 or height <= 0:
                continue

            try:
                pixels = glGetTexImage(
                    GL_TEXTURE_2D,
                    0,
                    GL_RGBA,
                    GL_UNSIGNED_BYTE
                )
            except Exception:
                continue

            image = np.frombuffer(pixels, dtype=np.uint8).reshape(height, width, 4)
            image = np.flipud(image)

            img = Image.fromarray(image, "RGBA")

            img_path = f"{dir}/textures/tex_{tex_id}.png"
            os.makedirs(f"{dir}/textures", exist_ok=True)
            img.save(img_path)

            textures.append((tex_id, img))

            print(f"Dumped texture {tex_id}")

        return textures

    @classmethod
    def build_atlas(cls, textures, dir=None):
        if dir == None:
            dir = cls.OUTPUT_DIR

        if not textures:
            print("No textures found, skipping atlas.")
            return

        atlas_width = cls.MAX_ATLAS_WIDTH
        x = y = 0
        row_height = 0

        placements = {}

        # Estimate atlas height
        total_height = 0
        current_width = 0
        max_row_height = 0

        for _, img in textures:
            w, h = img.size
            if current_width + w > atlas_width:
                total_height += max_row_height + cls.PADDING
                current_width = 0
                max_row_height = 0

            current_width += w + cls.PADDING
            max_row_height = max(max_row_height, h)

        total_height += max_row_height

        atlas = Image.new("RGBA", (atlas_width, total_height), (0, 0, 0, 0))

        for tex_id, img in textures:
            w, h = img.size

            if x + w > atlas_width:
                x = 0
                y += row_height + cls.PADDING
                row_height = 0

            atlas.paste(img, (x, y))

            placements[str(tex_id)] = {
                "x": x,
                "y": y,
                "width": w,
                "height": h
            }

            x += w + cls.PADDING
            row_height = max(row_height, h)

        atlas_path = f"{dir}/atlas/atlas.png"
        os.makedirs(f"{dir}/atlas", exist_ok=True)
        atlas.save(atlas_path)

        meta_path = f"{dir}/atlas/atlas.json"
        with open(meta_path, "w") as f:
            json.dump(placements, f, indent=2)

        print(f"\nAtlas saved as {atlas_path}")
        print(f"Metadata saved as {meta_path}")

    @classmethod
    def save_shader_cache(cls, path=None):
        textures = cls.dump_textures(path)
        cls.build_atlas(textures, path)