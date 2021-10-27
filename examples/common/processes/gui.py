import numpy as np

from rembrain_robot_framework import RobotProcess
import PySimpleGUI as sg
from PIL import ImageTk, Image
import typing as T


class GUIProcess(RobotProcess):
    def __init__(self, *args, **kwargs):
        super(GUIProcess, self).__init__(*args, **kwargs)

        # Required for persistence of images, because if they go out of scope, they disappear from the canvas
        self.tk_images: T.Dict[str, T.Optional[ImageTk.PhotoImage]] = {
            "image_orig": None,
            "image_processed": None
        }

    def run(self) -> None:
        self.log.info("HI!")

        canvas_orig = sg.Canvas(size=(533, 400))
        canvas_processed = sg.Canvas(size=(533, 400))

        layout = [
            [sg.Text("Original", size=(76, 1)), sg.Text("Processed")],
            [canvas_orig, canvas_processed]
        ]
        window = sg.Window("Local example", layout, location=(0, 0))

        while True:
            event, values = window.read(timeout=10)

            if event in (sg.WIN_CLOSED, 'Exit'):
                break

            self.try_redraw_image("image_orig", canvas_orig)
            self.try_redraw_image("image_processed", canvas_processed)

        window.close()
        self.shared.exit_flag.value = True

    def try_redraw_image(self, queue_name: str, canvas_elem: sg.Canvas) -> None:
        if self.is_empty(queue_name):
            return
        raw_image: np.ndarray = self.consume(queue_name)
        img = Image.fromarray(raw_image)
        img = img.resize(canvas_elem.get_size())
        self.tk_images[queue_name] = ImageTk.PhotoImage(img)

        canvas_elem.TKCanvas.delete("all")
        canvas_elem.TKCanvas.create_image(0, 0, image=self.tk_images[queue_name], anchor="nw")
