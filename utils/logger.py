import logging
import re
import typing
from .xterm import XTERM_COLORS as XT

BIN = logging.INFO - 4
PIPELINE = logging.INFO - 3
BIT = logging.INFO - 2
COMMAND = logging.INFO - 1

# PIPELINE = logging.INFO + 1
# BIT = logging.INFO + 2


class CustomFormatter(logging.Formatter):

    def __init__(self, name=None, order=[], version=None, color=True, datefmt=None):
        if color:
            def wrap_color(str, color):
                return f"{color}{str}{XT.RESET}"
        else:
            def wrap_color(str, color):
                return f"{str}"

        _time = "%(asctime)s"
        _order = f"""{"/".join((f"{step}" for step in order))}""" if len(order) > 0 else None
        _level = "%(levelname)s"
        _message = "%(message)s"
        _location = wrap_color("(%(filename)s:%(lineno)d)", XT.DIM)

        def _common_format(_time, _order, _level, _message, _location):
            cl = wrap_color("[", XT.DIM)
            cr = wrap_color("]", XT.DIM)
            __time = f"{cl}{wrap_color(_time, XT.Blue1)}{cr}" if _time and len(_time) > 0 else ""
            __order = f"{cl}{wrap_color(_order, XT.Chartreuse1)}{cr}" if _order and len(_order) > 0 else ""
            __level = f"{cl}{_level}{cr}" if _level and len(_level) > 0 else ""
            __name = f"{cl}{wrap_color(name, XT.Blue2)}{cr}" if name else ""
            __version = f"{cl}{wrap_color(version, XT.Blue3)}{cr}" if version else ""

            return f"{__time}{__name}{__version}{__order}{__level} {_message} {_location}"

        def _debug_format(_time, _order, _level, _message, _location):
            _level = wrap_color(_level, XT.Green)
            _message = wrap_color(_message, f"{XT.Green}{XT.DIM}")
            return _common_format(_time, _order, _level, _message, _location)

        def _info_format(_time, _order, _level, _message, _location):
            return _common_format(_time, _order, "", _message, _location)

        def _warning_format(_time, _order, _level, _message, _location):
            _level = wrap_color(_level, XT.Yellow)
            _message = wrap_color(_message, f"{XT.Yellow}{XT.DIM}")
            return _common_format(_time, _order, _level, _message, _location)

        def _error_format(_time, _order, _level, _message, _location):
            _level = wrap_color(_level, XT.Red)
            _message = wrap_color(_message, f"{XT.Red}{XT.DIM}")
            return _common_format(_time, _order, _level, _message, _location)

        def _critical_format(_time, _order, _level, _message, _location):
            _level = wrap_color(_level, XT.Red)
            _message = wrap_color(_message, f"{XT.Red}{XT.DIM}")
            return _common_format(_time, _order, _level, _message, _location)

        def _bin_format(_time, _order, _level, _message, _location):
            _level = "BIN"
            _level = wrap_color(_level, XT.DeepPink6)
            _message = wrap_color(_message, f"{XT.DeepPink6}{XT.DIM}")
            return _common_format(_time, _order, _level, _message, _location)

        def _pipeline_format(_time, _order, _level, _message, _location):
            _level = "PIPELINE"
            _level = wrap_color(_level, XT.Magenta1)
            _message = wrap_color(_message, f"{XT.Magenta1}{XT.DIM}")
            return _common_format(_time, _order, _level, _message, _location)

        def _bit_format(_time, _order, _level, _message, _location):
            _level = "BIT"
            _level = wrap_color(_level, XT.Magenta1)
            _message = wrap_color(_message, f"{XT.Magenta1}{XT.DIM}")
            return _common_format(_time, _order, _level, _message, _location)

        def _command_format(_time, _order, _level, _message, _location):
            _level = "COMMAND"
            _level = wrap_color(_level, XT.SkyBlue2)
            _message = wrap_color(_message, f"{XT.SkyBlue2}{XT.DIM}")
            return _common_format(_time, _order, _level, _message, _location)

        # datefmt = '%Y-%m-%d %H:%M:%S %s,%03d'
        # datefmt = '%Y-%m-%d %H:%M:%S %03d'

        self.formatters = {}
        self.formatters[logging.DEBUG] = logging.Formatter(_debug_format(_time, _order, _level, _message, _location), datefmt=datefmt)
        self.formatters[logging.INFO] = logging.Formatter(_info_format(_time, _order, _level, _message, _location), datefmt=datefmt)
        self.formatters[logging.WARNING] = logging.Formatter(_warning_format(_time, _order, _level, _message, _location), datefmt=datefmt)
        self.formatters[logging.ERROR] = logging.Formatter(_error_format(_time, _order, _level, _message, _location), datefmt=datefmt)
        self.formatters[logging.CRITICAL] = logging.Formatter(_critical_format(_time, _order, _level, _message, _location), datefmt=datefmt)
        self.formatters[BIN] = logging.Formatter(_bin_format(_time, _order, _level, _message, _location), datefmt=datefmt)
        self.formatters[PIPELINE] = logging.Formatter(_pipeline_format(_time, _order, _level, _message, _location), datefmt=datefmt)
        self.formatters[BIT] = logging.Formatter(_bit_format(_time, _order, _level, _message, _location), datefmt=datefmt)
        self.formatters[COMMAND] = logging.Formatter(_command_format(_time, _order, _level, _message, _location), datefmt=datefmt)

    def format(self, record):
        identifier = record.levelno
        formatter = self.formatters.get(identifier, None)
        return formatter.format(record)


class Logger(logging.Logger):
    sub: "typing.Callable[[str], Logger]"
    bin: "typing.Callable[[typing.Any], None]"
    pipeline: "typing.Callable[[typing.Any], None]"
    bit: "typing.Callable[[typing.Any], None]"
    command: "typing.Callable[[typing.Any], None]"


def create_logger(name=None, title=None, order=[], version=None, color=True) -> Logger:
    if name != None:
        order = order[:] + [name]

    def sub(name):
        _sub = create_logger(name, title, order, version=version, color=color)
        _sub.parent = logger
        return _sub

    def bin(msg, *a, **kw):
        kw["stacklevel"] = kw.get("stacklevel", 1) + 1
        return logger.log(BIN, msg, *a, **kw)

    def pipeline(msg, *a, **kw):
        kw["stacklevel"] = kw.get("stacklevel", 1) + 1
        return logger.log(PIPELINE, msg, *a, **kw)

    def bit(msg, *a, **kw):
        kw["stacklevel"] = kw.get("stacklevel", 1) + 1
        return logger.log(BIT, msg, *a, **kw)

    def command(msg, *a, **kw):
        kw["stacklevel"] = kw.get("stacklevel", 1) + 1
        return logger.log(COMMAND, msg, *a, **kw)

    logger_name = "/".join(order)
    logger: "Logger" = logging.getLogger(logger_name)
    logger.sub = sub
    logger.bin = bin
    logger.pipeline = pipeline
    logger.bit = bit
    logger.command = command

    logger.propagate = False
    if not logger.hasHandlers():
        ch = logging.StreamHandler()
        ch.setFormatter(CustomFormatter(name=title, order=order, version=version, color=color))
        logger.addHandler(ch)

    # logger.info(f"{logger_name}", stacklevel=3)
    return logger


def load_package_json() -> "dict":
    import os
    import json
    package_path = "./package.json"
    package = None
    if os.path.isfile(package_path):
        with open(package_path, "r") as f:
            package = json.load(f)
    return package


logger: "Logger" = create_logger()
logger.setLevel(BIN)

def set_logger(_logger: "Logger"):
    global logger
    logger = _logger


def get_logger():
    global logger
    return logger


def create_package_logger(name=None, version=None, level=BIN):
    try:
        package = load_package_json()
        if package:
            version = package.get("version", version)
            name = package.get("name", name)
    except:
        pass

    logger = create_logger(None, name, version=version)
    if level != None:
        logger.setLevel(level)
    return logger


def load_package_logger(name=None, version=None, level=BIN):
    set_logger(create_package_logger(name=name, version=version, level=level))
    return get_logger()
