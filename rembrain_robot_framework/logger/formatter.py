import typing as T
from collections import OrderedDict
from logging import LogRecord

from pythonjsonlogger import jsonlogger


class JsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(
        self,
        log_record: T.Union[OrderedDict, dict],
        record: LogRecord,
        message_dict: dict,
    ) -> None:
        super(JsonFormatter, self).add_fields(log_record, record, message_dict)

        level: T.Optional[str] = log_record.get("level")
        log_record["level"] = level.upper() if level else record.levelname
        log_record["logger"] = record.name
