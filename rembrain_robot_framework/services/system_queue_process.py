import os
import time
from multiprocessing import Queue
from threading import Thread
import json
from rembrain_robot_framework.models.request import Request
import logging

class SystemQueueProcess:
    EXCHANGE: str = "system"

    def __init__(self, queue: Queue,dispatcher) -> None:
        from rembrain_robot_framework.processes import WsRobotProcess

        if 'RRF_USERNAME' in os.environ.keys():
            self.input_queue = dispatcher.mp_context.Queue(maxsize=dispatcher.DEFAULT_QUEUE_SIZE)
            self.th=Thread(target=self.th_func,args=(self.input_queue,))
            self.th.daemon=True
            self.th.start()

            dispatcher.add_process('system_pusher',WsRobotProcess,consume_queues={'system_push':queue},
                                   command_type='push_loop',exchange=self.EXCHANGE)
            dispatcher.add_process('system_puller',WsRobotProcess,publish_queues={'system_pull':[self.input_queue]},
                                   command_type='pull',exchange=self.EXCHANGE)
            self.dispatcher=dispatcher
        else:
            self.log.info('RRF_USERNAME does not exist, cross application RPC is not engaged')

        return

    def th_func(self,q):
        while True:
            if not q.empty():
                message=q.get()
                request = json.loads(message.decode('utf-8'))
                # the request can be received along with other usual commands, to check - use model validation
                if Request.model_validate(request):
                    request = Request(**request)
                    if request.username==os.environ['RRF_USERNAME']:
                        if request.client_process in self.dispatcher.system_queues.keys():
                            self.dispatcher.system_queues[request.client_process].put(request)
                        else:
                            logging.error('there is no client_process among processes, should be so in RPC')

            time.sleep(0.001)
        return