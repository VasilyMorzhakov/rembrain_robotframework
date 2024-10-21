from rembrain_robot_framework import RobotProcess
from rembrain_robot_framework.models.request import Request
import json

class Responder(RobotProcess):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def run(self):
        index=0
        while True:
            request=json.loads(self.consume('commands').decode('utf-8'))
            #the request can be received along with other usual commands, to check - use model validation
            if Request.model_validate(request):
                request = Request(**request)
                request.data={'result':True,'index':index}
                index+=1
                self.respond_to(request)

        return