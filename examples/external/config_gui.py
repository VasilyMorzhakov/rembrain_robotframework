import os
import sys
from typing import Dict, List

import PySimpleGUI as sg


def query_env_vars(required_vars: List[str]) -> bool:
    """
    Checks that all env vars in required_vars are set
    If they aren't, show user a window and ask for them, after which update env vars
    Returns false if user didn't submit anything
    """
    current_env_vars = {k: os.environ.get(k) for k in required_vars}

    # build layout
    layout = [
        [sg.Text("Some required env variables aren't assigned, please input them:", pad=(0, 10))],
    ]
    for k in current_env_vars.keys():
        layout.append([
            [sg.Text(k, size=(30, 1), justification="right"),
             sg.InputText(key=f"-{k}", enable_events=True,
                          password_char="*" if "password" in k.lower() else "")]
        ])
    layout.append(
        [sg.Exit(pad=((0, 430), (10, 0))), sg.Submit(disabled=True, pad=((0, 0), (10, 0)))]
    )

    if all((v for v in current_env_vars.values())):
        return True
    else:
        window = sg.Window("Input configuration values", layout, location=(10, 10))
        window.finalize()

        for k, v in current_env_vars.items():
            window[f"-{k}"].update(v)

        got_values = False

        while True:
            event, values = window.read()

            if event == "Exit" or event == sg.WIN_CLOSED:
                break

            has_values = all((i for i in values.values()))
            window["Submit"].update(disabled=not has_values)

            if event == "Submit":
                updated = {}
                for k in current_env_vars:
                    updated[k] = values[f"-{k}"]
                os.environ.update(updated)
                got_values = True
                break

        window.close()
        return got_values
