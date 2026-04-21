from PIL import Image, ImageEnhance
import uuid
from .shaders import ShaderHandler
from ..common import *
from pathlib import Path
import cv2
import imageio
from OpenGL.GL import *

class Texture:
    _atlas_size = ShaderHandler._atlas_size
    _textures: dict["Imaging"] = {}
    
    @classmethod
    def set_texture(cls, name: str, path: Path) -> None:
        if not cls._textures.get(path) == None:
            raise KeyError

        if path.suffix == '.mp4':
            cap = cv2.VideoCapture(path)
            fps = cap.get(cv2.CAP_PROP_FPS)

            cls._textures[name] = Video(name, cap, FileType.STREAM, GL_BGR, ConvertType.VIDEO, fps, uuid.uuid4().hex)

        elif path.suffix == '.gif':
            gif = imageio.mimread(path)

            if gif[0].shape[2] == 4:
                image_format = GL_RGBA
            else:
                image_format = GL_RGB
            
            file_type = FileType.BATCHLIST
            total_area = sum(f.shape[0] * f.shape[1] for f in gif)

            if total_area > cls._atlas_size * cls._atlas_size * 0.7:
                file_type = FileType.DYNAMIC
            
            cls._textures[name] = Video(name, gif, file_type, image_format, ConvertType.GIF, occupation=uuid.uuid4().hex)

        elif path.suffix in ['.png', '.jpg', '.jpeg']:
            surface: Image.Image = Image.open(path).convert("RGBA")

            file_type = FileType.BATCH
            if max(surface.width, surface.height) > 1024:
                file_type = FileType.BACKGROUND

            cls._textures[name] = Imaging(name, surface, file_type, GL_RGBA, uuid.uuid4().hex)
            
        else:
            raise FileNotFoundError

    @classmethod
    def link_texture(cls, image: "Imaging", name: str, new_name: str) -> None:
        cls.delete_texture(name)
        cls._textures[new_name] = image

    @classmethod
    def get_texture(cls, name: str) -> "Imaging | Video":
        return cls._textures[name]
    
    @classmethod
    def delete_texture(cls, name: str) -> None:
        del cls._textures[name]

class Video:
    def __init__(self, name: str, frames: Sequence[Draw], file_type: FileType, image_format: int, convert_type: ConvertType, fps: int=0, occupation:str = None) -> None:
        self.name = name
        self.occupation = occupation
        self.image_format = image_format
        self.file_type = file_type
        self.convert_type = convert_type
        self.uploadead = False
        self.uv = UVLocation()
        self.uv_list = []
        self.fps = fps
        self._current_frame = 0
        self.cap = None

        self.set_frames(frames)
    
    def set_frames(self, frames: Sequence[Draw], upload: bool=False) -> None:
        if self.convert_type == ConvertType.GIF:
            self._frames = frames
            self.total_frames = len(frames)
            if self.fps == 0:
                frame_time = 1 / 60
            else:
                frame_time = 1 / self.fps
            self.video_len = frame_time * self.total_frames
            self.image = self._frames[self._current_frame]

        else:
            self.cap = frames
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            frame_time = 1 / self.fps
            self.video_len = frame_time * self.total_frames

            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self._current_frame)
            ret, self.image = self.cap.read()

        if upload:
            self.upload()
        self.uploadead = upload

    def __del__(self) -> None:
        if not self.cap is None:
            self.cap.release()

    def get_frames(self) -> Sequence[Draw]:
        return self._frames

    def get_image(self) -> Draw:
        return self.image

    def get_tex_id(self) -> Draw:
        return self.uv.tex_id

    def upload(self) -> None:
        if self.occupation == None:
            raise ValueError("Sem ocupação definida")
        
        if self.file_type in [FileType.STREAM, FileType.DYNAMIC]:
            self.uv = ShaderHandler.add_texture(self.get_image(), self.convert_type, self.occupation)
        elif self.file_type == FileType.BATCHLIST:
            self.uv_list = ShaderHandler.add_texture_atlas_list(self.get_frames(), self.convert_type, self.uv_list)
            self.uv = self.uv_list[0]
        else:
            raise TypeError
        
    def next_frame(self) -> Draw:
        self._current_frame += 1
        if self._current_frame >= self.total_frames:
            self._current_frame = 0
        
        if self.convert_type == ConvertType.GIF:
            self._frames[self._current_frame]
        else:
            ret, self.image = self.cap.read()
            
            if self.image is None:
                self._current_frame == 0
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, self._current_frame)
                ret, self.image = self.cap.read()

        if self.file_type in [FileType.STREAM, FileType.DYNAMIC]:
            self.uv = ShaderHandler.add_texture(self.get_image(), self.convert_type, self.occupation)
        elif self.file_type == FileType.BATCHLIST:
            self.uv = self.uv_list[self._current_frame]

        return self.uv

    def get_occupation(self) -> str:
        return self.occupation

    def set_occupation(self, occupation: str) -> None:
        if not self.occupation == occupation:
            self.occupation = occupation

class Imaging:
    def __init__(self, name: str, image: Draw, file_type: FileType, image_format: int, occupation: str=None) -> None:
        self.name = name
        self.occupation = occupation
        self.image_format = image_format
        self.file_type = file_type
        self.uploadead = False
        self.uv = UVLocation()

        self.set_image(image)
    
    def set_image(self, image: Draw, upload: bool=False) -> None:
        self._image = image

        if upload:
            self.upload()
        self.uploadead = upload

    def get_image(self) -> "Imaging":
        return self._image
    
    def get_uv(self) -> dict:
        return self.uv
    
    def get_tex_id(self) -> int:
        return self.uv.tex_id

    def upload(self) -> None:
        if self.occupation == None:
            raise ValueError("Sem ocupação definida")
        if self.file_type in [FileType.DYNAMIC, FileType.BACKGROUND]:
            self.uv = ShaderHandler.add_texture(self.get_image(), ConvertType.IMAGE, self.occupation)
        elif self.file_type == FileType.BATCH:
            self.uv = ShaderHandler.add_texture_atlas(self.get_image(), ConvertType.IMAGE, self.uv)
        else:
            raise TypeError

    def get_occupation(self) -> str:
        return self.occupation

    def set_occupation(self, occupation: str) -> None:
        if not self.occupation == occupation:
            self.occupation = occupation

    @staticmethod
    def set_saturation(img: "Imaging", factor: float) -> Image.Image:
        enhancer = ImageEnhance.Color(img)
        return enhancer.enhance(factor)

    @staticmethod
    def set_opacity(img: "Imaging", alpha_factor: float) -> Image.Image:
        img = img.convert("RGBA")
        r, g, b, a = img.split()
        a = a.point(lambda p: int(p * alpha_factor))
        return Image.merge("RGBA", (r, g, b, a))

    @staticmethod
    def rescale(img: "Imaging", sx: float, sy: float) -> Image.Image:
        w, h = img.size
        return img.resize((int(w * sx), int(h * sy)), Image.NEAREST)

    @staticmethod
    def rotate(img: "Imaging", angle: float) -> Image.Image:
        return img.rotate(angle, expand=True)

    @staticmethod
    def resize_canvas(img: "Imaging", new_w: int, new_h: int) -> Image.Image:
        new_img = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
        new_img.paste(img, (0, 0))
        return new_img

    @staticmethod
    def translate(img: "Imaging", dx: int, dy: int) -> Image.Image:
        canvas = Image.new("RGBA", img.size, (0, 0, 0, 0))
        canvas.paste(img, (dx, dy))
        return canvas

    @staticmethod
    def apply_channels(img: "Imaging", fr, fg, fb, fa) -> Image.Image:
        img = img.convert("RGBA")
        r, g, b, a = img.split()

        r = r.point(fr)
        g = g.point(fg)
        b = b.point(fb)
        a = a.point(fa)

        return Image.merge("RGBA", (r, g, b, a))

    @staticmethod
    def paste_image(base: "Imaging", overlay: Image.Image, x: int, y: int) -> Image.Image:
        base = base.convert("RGBA")
        overlay = overlay.convert("RGBA")

        result = base.copy()
        result.paste(overlay, (x, y), overlay)
        return result