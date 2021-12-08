import numpy as np
from pydantic import BaseModel


class Image(BaseModel):
    rgb: np.ndarray
    depth: np.ndarray
    camera: dict

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def get_data(cls):
        x = 100
        y = 100
        camera = {
            "fx": 1000,
            "fy": 1000,
            "ppx": 640,
            "ppy": 360,
            "width": 1280,
            "height": 720,
        }

        color_image: np.ndarray = np.zeros((720, 1280, 3))
        color_image[y : y + 100, x : x + 100, 2] = 1
        color_image = (color_image * 255).astype(np.uint8)

        depth_image: np.ndarray = np.zeros((360, 640), dtype=np.uint16)
        depth_image[y // 2 : y // 2 + 50, x // 2 : x // 2 + 50] = 2000

        return Image(rgb=color_image, depth=depth_image, camera=camera)
