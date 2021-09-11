import json
import logging
import typing as T

from rembrain_robotframework import RobotProcess


# todo it does not need for this realization ?
class CommandReceiver(RobotProcess):
    def run(self) -> None:
        return
        logging.info(f"{self.__class__.__name__} started, name: {self.name}.")

        while True:
            response_data: T.Union[str, bytes] = self.consume()
            try:
                if isinstance(response_data, bytes):
                    decoded_command: str = response_data.decode("utf-8")
                    logging.info(f"Received command: {decoded_command}")
                    self.publish(json.loads(decoded_command), queue_name="websocket_to_robot")
                else:
                    logging.error(
                        f"{self.__class__.__name__}: WS response is not bytes! "
                        f"Received: {response_data}, type={type(response_data)}."
                    )
                    break

            except (UnicodeDecodeError, json.JSONDecodeError):
                logging.warning("UnicodeDecodeError or JSONDecoderError was received.")
