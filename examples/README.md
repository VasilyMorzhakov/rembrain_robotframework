## Rembrain Robot Framework Examples

This folder contains an example projects that can help you
to get acquainted how Rembrain Robot Framework (RRF) works,
how you can start writing your own applications with it.

## Running examples

`Tk` and `git` are required for installation (git to get the framework package from GitHub, Tk for PySimpleGUI)
```shell
pip3 install -r requirements.txt
```

## Local example

The `local` folder contains a project consisting of three processes, defined in `config/processes_config.yaml`:

- `image_capture` process pushes an image (currently static)
to a `image_orig` queue for processing;
- `processor` process gets the image from the `image_orig` queue,
runs [YOLOV5](https://github.com/ultralytics/yolov5)
feature recognition on it and pushes the processed
image to the `image_processed` queue;
- `gui` process gathers both the original and the processed image from the queues
and shows to the user.

#### Running the local example
To run this example run the `main.py` file

```shell
python3 examples/local/main.py
```

## External example
The `external` folder contains a similar project, except this time processor is separated from the other processes in a separate executable.
This way the processes communicate via the Rembrain message broker using websockets.

This allows the processor to be run on an external machine
that is able to process more computationally intensive workloads.

You have to specify `ROBOT_NAME`, `RRF_USERNAME` and `RRF_PASSWORD` variables as well as `WEBSOCKET_GATE_URL`
(rembrain's ws broker url is supplied by default) in order for the two programs to communicate.

#### Running the external example
To run this example first start the processor, which will start running in your shell,
and then start the robot process in another shell

```shell
ROBOT_NAME=test RRF_USERNAME=test RRF_PASSWORD python3 examples/external/run_processor.py
# in another shell (the robot name/password should be the same)
ROBOT_NAME=test RRF_USERNAME=test RRF_PASSWORD python3 examples/external/run_robot.py
```
