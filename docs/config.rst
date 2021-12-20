Process configuration
======================

Here is an example configuration from the `examples` folder. Specifically the local example.
This config file is parsed at the start and passed to the :class:`~rembrain_robot_framework.RobotDispatcher` constructor


.. literalinclude:: ../examples/local/config/processes_config.yaml
    :language: yaml

.. note::
    We recommend using YAML for configuration, but any format that is parsable into Python dicts is fine.

Processes
----------

The `processes` section describes the processes that RobotDispatcher will start after calling the `run()` method

The key of each section (`gui`/`image_capture`/`processor`) is the name of the process.

.. note:: Specifying which process class should be used for each process is up to the user.
    The dispatcher accepts a `processes` argument that should have this mapping.
    See the examples folder of the repo for an example of how to generate the process map.

Process arguments
^^^^^^^^^^^^^^^^^^

Inside of the process section is the process's configuration. Every process has following arguments:
    consume: List of names of the consume queues

    publish: List of names of the publish queues

    .. note:: At runtime RobotDispatcher checks that there are no queues that don't have any consuming
        or publishing processes and throws an error if any are found.

    keep_alive: Whether the process should reboot in case it closes (expectedly OR unexpectedly). Default value is true.

    log_level: Log level that will be set on the root logger of the process. If it isn't specified, the level is INFO

    monitoring: Turns on a stack sampling profiler utilizing :class:`~rembrain_robot_framework.services.StackMonitor`.
    The stack monitor samples the stack and writes it out in an interval. Useful for debugging and finding deadlocks in
    stuck processes. Turned off by default, use True to enable

All other arguments are passed to the constructor of the process's class in its `kwargs`.
This way you can add arguments specific to your process class in the config file

Shared objects
---------------

Here you can specify objects that will be shared between processes.
Each process can access them via `self.shared` NamedTuple

Available types (case sensitive):
    - dict
    - list
    - Lock
    - Value:bool
    - Value:int
    - Value:float
    - Value:string

Description
--------------

This section contains miscelaneous information about the project.
This information is primarily used for logging purposes.
