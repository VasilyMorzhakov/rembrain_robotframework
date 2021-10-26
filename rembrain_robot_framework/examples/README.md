# Robotframework examples

This folder contains example projects that can help you get acquainted with how robotframework works and how you can 
start writing your own applications utilizing it

The `local` folder contains a project consisting of three processes, defined in `config/processes_config.yaml`:

- `image_capture` process that pushes an image (currently static) to a `image_orig` queue for processing
- `processor` process that gets image from the `image_orig` queue and runs YOLO feature recognition on it and then pushes the processed image to the `image_processed` queue
- `gui` process that gathers both the original and processed image from the queues and shows them to the user

The `external` folder **(TODO)** contains a similar project, except this time processor is separated from the other processes in a separate executable.
This way the processes communicate via the Rembrain message broker using websockets.

This allows the processor to be run on an external machine that is able to process more computationally intensive workloads

## Running examples

First make sure to install the requirements file by running this command in the repository root

Tk is required in order to run PySimpleGUI for the gui process, so make sure it is also installed in your system

```shell
pip3 install -r config/requirements/examples.txt
```

After that each project can be run via running the `main.py` file