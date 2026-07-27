import io
from PIL import Image as PILImage
from PIL.Image import Transpose
from ..resources.assets.import_data import TextureData
import numpy as np
from .common import ConvertedImage

class ImageConversion:
    @staticmethod
    def convert_moderngl(texture_data: TextureData) -> ConvertedImage:
        raw_array: np.ndarray = texture_data.source.data
        
        raw_bytes = raw_array.tobytes()
        
        pil_img = PILImage.open(io.BytesIO(raw_bytes))
        
        if pil_img.mode != "RGBA":
            pil_img = pil_img.convert("RGBA")
            
        pil_img = pil_img.transpose(Transpose.FLIP_TOP_BOTTOM)
        
        width, height = pil_img.size
        final_rgba_bytes = pil_img.tobytes()
        components = 4
        
        final_image = ConvertedImage(final_rgba_bytes, (width, height), components)
        return final_image
