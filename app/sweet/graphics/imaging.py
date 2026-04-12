from PIL import Image, ImageEnhance
from ..common import FileType, Draw
import uuid
from .shaders import ShaderHandler
import pygame as pg

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

    def get_image(self):
        return self._image

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
    def set_saturation(img: Image, factor: float) -> Image:
        enhancer = ImageEnhance.Color(img)
        return enhancer.enhance(factor)

    @staticmethod
    def set_opacity(img: Image, alpha_factor: float) -> Image:
        img = img.convert("RGBA")
        r, g, b, a = img.split()
        a = a.point(lambda p: int(p * alpha_factor))
        return Image.merge("RGBA", (r, g, b, a))

    @staticmethod
    def rescale(img: Image, sx: float, sy: float) -> Image:
        w, h = img.size
        return img.resize((int(w * sx), int(h * sy)), Image.NEAREST)

    @staticmethod
    def rotate(img: Image, angle: float) -> Image:
        return img.rotate(angle, expand=True)

    @staticmethod
    def resize_canvas(img: Image, new_w: int, new_h: int) -> Image:
        new_img = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
        new_img.paste(img, (0, 0))
        return new_img

    @staticmethod
    def translate(img: Image, dx: int, dy: int) -> Image:
        canvas = Image.new("RGBA", img.size, (0, 0, 0, 0))
        canvas.paste(img, (dx, dy))
        return canvas

    @staticmethod
    def apply_channels(img: Image, fr, fg, fb, fa) -> Image:
        img = img.convert("RGBA")
        r, g, b, a = img.split()

        r = r.point(fr)
        g = g.point(fg)
        b = b.point(fb)
        a = a.point(fa)

        return Image.merge("RGBA", (r, g, b, a))

    @staticmethod
    def paste_image(base: Image, overlay: Image, x: int, y: int) -> Image:
        base = base.convert("RGBA")
        overlay = overlay.convert("RGBA")

        result = base.copy()
        result.paste(overlay, (x, y), overlay)
        return result