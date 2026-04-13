from PIL import Image, ImageEnhance
import uuid
from .shaders import ShaderHandler
import pygame as pg
from ..common import *
from pathlib import Path

class Texture:
    _textures: dict["Imaging"] = {}
    
    @classmethod
    def set_texture(cls, name: str, path: Path | str, save_type: FileType=FileType.PGSURF) -> None:
        if not cls._textures.get(path) == None:
            raise KeyError

        if save_type == FileType.PGSURF:
            surface: pg.Surface = pg.image.load(path)
            cls._textures[name] = Imaging(surface, FileType.PGSURF)
            return
        if save_type == FileType.PILIMAGE:
            surface: Image.Image = Image.open(path).convert("RGBA")
            cls._textures[name] = Imaging(surface, FileType.PILIMAGE)
            return
        if save_type == FileType.SHADERATLAS:
            surface: pg.Surface = pg.image.load(path).convert_alpha()
            cls._textures[name] = Imaging(*ShaderHandler.add_texture(surface))

    @classmethod
    def link_texture(cls, image: "Imaging", occupation: str) -> None:
        cls._textures[occupation] = image

    @classmethod
    def get_texture(cls, name: str) -> "Imaging":
        return cls._textures[name]

class Imaging:
    def __init__(self, image: Draw, file_type: FileType, source: FileType=None, source_format: FileType=None, occupation:str=None) -> None:
        if occupation == None:
            occupation = uuid.uuid4().hex
        self.occupation = occupation
        self.set_image(image, file_type, source, source_format)
    
    def set_image(self, image: Draw, file_type: FileType, source: FileType=None, source_format: FileType=None) -> None:
        self._image = image
        self.file_type = file_type
        self.source = None
        self.source_format = None
        self.width: int
        self.height: int
    
        if self.file_type == FileType.SHADERATLAS:
            self.source = source
            self.source_format = source_format
            
            if source_format == FileType.PGSURF:
                self.width, self.height = source.get_size()
            elif source_format == FileType.PILIMAGE:
                self.width = source.width
                self.height = source.height

        elif file_type == FileType.PGSURF or source_format == FileType.PGSURF:
            self.width, self.height = image.get_size()

        elif file_type == FileType.PILIMAGE or source_format == FileType.PILIMAGE:
            self.width = image.width
            self.height = image.height

    def get_image(self) -> "Imaging":
        return self._image

    def get_occupation(self) -> str:
        return self.occupation

    def set_occupation(self, occupation: str) -> None:
        self.occupation = occupation
        Texture.link_texture(self, self.occupation)

    @staticmethod
    def pil_to_pg(pil: Image) -> pg.Surface:
        pil_image = pil.convert("RGBA")
        mode = pil_image.mode
        size = pil_image.size
        data = pil_image.tobytes()
        return pg.image.fromstring(data, size, mode)

    @staticmethod
    def pg_to_pil(surf: pg.Surface) -> Image:
        data = pg.image.tostring(surf, "RGBA", True)
        size = surf.get_size()
        return Image.frombytes("RGBA", size, data)

    def convert(self, file_type: FileType, remove: bool=False) -> Draw:
        if self.file_type == file_type:
            return
    
        if self.file_type == FileType.SHADERATLAS:
            if self.source_format == file_type:
                self._image = self.source
                self.file_type = self.source_format
                self.source = None
                self.source_format = None
            else:
                if file_type == FileType.PGSURF and self.source_format == FileType.PILIMAGE:
                    self._image = self.pil_to_pg(self.source)
                    self.file_type = FileType.PGSURF

                elif file_type == FileType.PILIMAGE and self.source_format == FileType.PGSURF:
                    self._image = self.pg_to_pil(self.source)
                    self.file_type = FileType.PILIMAGE

                if remove:
                    ShaderHandler.remove_texture(self.occupation)

            return

        if self.file_type == FileType.PGSURF:
            if file_type == FileType.PILIMAGE:
                self._image = self.pg_to_pil(self._image)
                self.file_type = FileType.PILIMAGE

            elif file_type == FileType.SHADERATLAS:
                data = ShaderHandler.add_texture(self._image,
                                                 save_type=FileType.PGSURF,
                                                 occupation=self.occupation)
                self._image = data[0]
                self.file_type = data[1]
                self.source = data[2]
                self.source_format = data[3]
                self.occupation = data[4]

            return

        if self.file_type == FileType.PILIMAGE:
            if file_type == FileType.PGSURF:
                self._image = self.pil_to_pg(self._image)
                self.file_type = FileType.PGSURF

            elif file_type == FileType.SHADERATLAS:
                data = ShaderHandler.add_texture(self._image,
                                                 save_type=FileType.PILIMAGE,
                                                 occupation=self.occupation)
                self._image = data[0]
                self.file_type = data[1]
                self.source = data[2]
                self.source_format = data[3]
                self.occupation = data[4]

    @staticmethod
    def set_saturation(img: "Imaging", factor: float) -> "Imaging":
        enhancer = ImageEnhance.Color(img)
        return Imaging(enhancer.enhance(factor), FileType.PILIMAGE)

    @staticmethod
    def set_opacity(img: "Imaging", alpha_factor: float) -> "Imaging":
        img = img.convert("RGBA")
        r, g, b, a = img.split()
        a = a.point(lambda p: int(p * alpha_factor))
        return Imaging(Image.merge("RGBA", (r, g, b, a)), FileType.PILIMAGE)

    @staticmethod
    def rescale(img: "Imaging", sx: float, sy: float) -> "Imaging":
        w, h = img.size
        return Imaging(img.resize((int(w * sx), int(h * sy)), Image.NEAREST), FileType.PILIMAGE)

    @staticmethod
    def rotate(img: "Imaging", angle: float) -> "Imaging":
        return Imaging(img.rotate(angle, expand=True), FileType.PILIMAGE)

    @staticmethod
    def resize_canvas(img: "Imaging", new_w: int, new_h: int) -> "Imaging":
        new_img = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
        new_img.paste(img, (0, 0))
        return Imaging(new_img, FileType.PILIMAGE)

    @staticmethod
    def translate(img: "Imaging", dx: int, dy: int) -> "Imaging":
        canvas = Image.new("RGBA", img.size, (0, 0, 0, 0))
        canvas.paste(img, (dx, dy))
        return Imaging(canvas, FileType.PILIMAGE)

    @staticmethod
    def apply_channels(img: "Imaging", fr, fg, fb, fa) -> "Imaging":
        img = img.convert("RGBA")
        r, g, b, a = img.split()

        r = r.point(fr)
        g = g.point(fg)
        b = b.point(fb)
        a = a.point(fa)

        return Imaging(Image.merge("RGBA", (r, g, b, a)), FileType.PILIMAGE)

    @staticmethod
    def paste_image(base: "Imaging", overlay: "Imaging", x: int, y: int) -> "Imaging":
        base = base.convert("RGBA")
        overlay = overlay.convert("RGBA")

        result = base.copy()
        result.paste(overlay, (x, y), overlay)
        return Imaging(result, FileType.PILIMAGE)