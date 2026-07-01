from PIL import Image, ImageEnhance
import uuid
from .shaders import ShaderTexture
from ..common import *
from ..path_solver import solve_path
import OpenGL.GL as gl # type: ignore
import json
from pathlib import Path
from collections.abc import Callable
class Texture:
    _atlas_size = ShaderTexture.get_atlas_size()
    _textures: dict[str, "Imaging"] = {}

    @classmethod
    def load_json_textures(cls, path: str | Path) -> None:
        with open(path, "r") as file:
            assets = json.load(file)

        for asset_type in assets.keys():
            if asset_type == "textures":
                textures = assets[asset_type]
                for key in textures.keys():
                    path = textures[key]
                    absolute_path = solve_path(path)
                    cls.set_texture(key, absolute_path)

    @classmethod
    def set_texture(cls, name: str, path: Path) -> "Imaging":
        if not cls._textures.get(name) == None:
            raise KeyError

        elif path.suffix in [".png", ".jpg", ".jpeg"]:
            surface: Image.Image = Image.open(path)

            file_type = FileType.BATCH
            if max(surface.width, surface.height) > 1024:
                file_type = FileType.BACKGROUND

            cls._textures[name] = Imaging(name, surface, file_type, gl.GL_RGBA, uuid.uuid4().hex)  # type: ignore
            cls._textures[name].upload()
            return cls._textures[name]

        else:
            raise FileNotFoundError

    @classmethod
    def link_texture(cls, image: "Imaging", name: str, new_name: str) -> None:
        cls.delete_texture(name)
        cls._textures[new_name] = image

    @classmethod
    def get_texture(cls, name: str) -> "Imaging":
        if cls._textures.get(name) is None:
            raise KeyError(
                f"Texture '{name}' not found. Have you loaded the assets.json file?"
            )
        return cls._textures[name]

    @classmethod
    def delete_texture(cls, name: str) -> None:
        if cls._textures.get(name) is None:
            raise KeyError(
                f"Texture '{name}' not found. Have you loaded the assets.json file?"
            )
        del cls._textures[name]


class Imaging:
    def __init__(
        self,
        name: str,
        image: Image.Image,
        file_type: FileType,
        image_format: int,
        occupation: str | None = None,
    ) -> None:
        self.name = name
        self.occupation = occupation
        self.image_format = image_format
        self.file_type = file_type
        self.uploadead = False
        self.opaque = self.opaque_test(image)
        self.uv = UVLocation()

        self.set_image(image)

    def opaque_test(self, image: Image.Image) -> bool:
        if image.mode not in ("RGBA", "LA") and "transparency" not in image.info:
            return True

        image.convert("RGBA")
        alpha = image.split()[-1]
        min_alpha, _ = alpha.getextrema()

        return min_alpha == 255

    def set_image(self, image: Image.Image, upload: bool = False) -> None:
        self._image = image

        if upload:
            self.upload()
        self.uploadead = upload

    def get_image(self) -> Image.Image:
        return self._image

    def get_width(self) -> int:
        return self._image.width

    def get_height(self) -> int:
        return self._image.height

    def get_uv(self) -> UVLocation:
        return self.uv

    def get_texture(self) -> str | None:
        return self.uv.texture

    def upload(self) -> None:
        if self.occupation == None:
            raise ValueError("Sem ocupação definida")
        if self.file_type in [FileType.DYNAMIC, FileType.BACKGROUND]:
            self.uv = ShaderTexture.create_texture(
                self.get_image(), ConvertType.IMAGE, self.occupation
            )
        elif self.file_type == FileType.BATCH:
            self.uv = ShaderTexture.create_texture_atlas(
                self.get_image(), ConvertType.IMAGE, self.uv
            )
        else:
            raise TypeError

    def get_occupation(self):
        return self.occupation

    def set_occupation(self, occupation: str) -> None:
        if not self.occupation == occupation:
            self.occupation = occupation

    @staticmethod
    def set_saturation(img: Image.Image, factor: float) -> Image.Image:
        enhancer = ImageEnhance.Color(img)
        return enhancer.enhance(factor)

    @staticmethod
    def set_opacity(img: Image.Image, alpha_factor: float) -> Image.Image:
        img = img.convert("RGBA")
        r, g, b, a = img.split()
        a = a.point(lambda p: int(p * alpha_factor))
        return Image.merge("RGBA", (r, g, b, a))

    @staticmethod
    def rescale(img: Image.Image, sx: float, sy: float) -> Image.Image:
        w, h = img.size
        return img.resize((int(w * sx), int(h * sy)), Image.NEAREST)  # type: ignore

    @staticmethod
    def rotate(img: Image.Image, angle: float) -> Image.Image:
        return img.rotate(angle, expand=True)

    @staticmethod
    def resize_canvas(img: Image.Image, new_w: int, new_h: int) -> Image.Image:
        new_img = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
        new_img.paste(img, (0, 0))
        return new_img

    @staticmethod
    def translate(img: Image.Image, dx: int, dy: int) -> Image.Image:
        canvas = Image.new("RGBA", img.size, (0, 0, 0, 0))
        canvas.paste(img, (dx, dy))
        return canvas

    @staticmethod
    def apply_channels(
        img: Image.Image,
        fr: Callable[[int], int] = lambda x: x,
        fg: Callable[[int], int] = lambda x: x,
        fb: Callable[[int], int] = lambda x: x,
        fa: Callable[[int], int] = lambda x: x,
    ) -> Image.Image:
        img = img.convert("RGBA")
        r, g, b, a = img.split()

        r = r.point(fr)
        g = g.point(fg)
        b = b.point(fb)
        a = a.point(fa)

        return Image.merge("RGBA", (r, g, b, a))

    @staticmethod
    def paste_image(
        base: Image.Image, overlay: Image.Image, x: int, y: int
    ) -> Image.Image:
        base = base.convert("RGBA")
        overlay = overlay.convert("RGBA")

        result = base.copy()
        result.paste(overlay, (x, y), overlay)
        return result
