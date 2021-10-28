## Rembrain Robot Framework Examples

This folder contains an example projects that can help you 
to get acquainted how Rembrain Robot Framework(RRF) works, 
how you can start writing your own applications with it.

The `local` folder contains a project consisting of three processes, 
defined in `config/processes_config.yaml`:

- `image_capture` process pushes an image (currently static) 
to a `image_orig` queue for processing;
- `processor` process gets the image from the `image_orig` queue, 
runs [YOLOV5](https://github.com/ultralytics/yolov5) 
feature recognition on it and pushes the processed 
image to the `image_processed` queue;
- `gui` process gathers both the original and the processed image from the queues 
and shows to the user.

The `external` folder **(TODO)** contains a similar project, 
except this time processor is separated from the other processes 
in a separate executable.
This way the processes communicate via the Rembrain message broker 
with websockets.

This allows the processor to be run on an external machine 
that is able to process more computationally intensive workloads.

#### Running
***
`Tk` and `git` are required for installation 
(`git` to get the framework package from `GitHub`, `Tk` for `PySimpleGUI`)
```shell
pip3 install -r requirements.txt
```

After that each project can be run via the `main.py` file.