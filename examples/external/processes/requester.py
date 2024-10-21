from websockets.legacy.async_timeout import timeout

from rembrain_robot_framework import RobotProcess
import time

class Requester(RobotProcess):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def run(self):

        while True:
            time.sleep(5.0)

            s=time.time()
            uid=self.send_request({'op':'function'},'commands',through_websocket=True)
            response=self.wait_response(uid,timeout=20.0)
            if not response is None:
                self.log.info(str(time.time() - s)+ ' response '+ str(response))
            else:
                self.log.warning('timeout in wait_response')

        return