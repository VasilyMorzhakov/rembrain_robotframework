import logging


class WsLogAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        """
        Websockets adds its own LoggingAdapter that adds an unpicklable websocket class,
        We have to get rid of it so we can pass log messages accross processes
        """
        if "websocket" in kwargs["extra"]:
            del kwargs["extra"]["websocket"]
        return msg, kwargs
