import os
import json
from pathlib import Path

from .logger import logger, XT


def path_make(path: "str | Path", logger=logger, stacklevel=1):
    path = Path(path)
    if not path.exists():
        logger.info(f"creating \"{path}\"", stacklevel=stacklevel + 1)
        os.makedirs(path)
    return path


class Config:
    def __init__(self, config=None, logger=logger) -> None:
        self.parent: "Config" = None
        self.config_file: "Path" = None
        self.config: "dict | list" = config
        self.logger = logger

    def resolve_path(self, path: "str | Path", required=True, quiet=False, stacklevel=1) -> Path:
        path: "Path" = Path(path)
        if path.is_absolute():
            return path
        if path.exists():
            return path

        current = self
        while current != None:
            if current.config_file:
                candidate = current.config_file.parent / path
                if candidate.exists():
                    if not quiet:
                        self.logger.warning(f"using \"{candidate}\" instead of \"{path}\"", stacklevel=stacklevel + 1)
                    return candidate
            current = current.parent

        error = f"using path=\"{path}\" which does not exist"
        if not quiet:
            self.logger.error(error)
        if required:
            raise Exception(error)
        return path

    def get(self, key: "str", _default=None, required=True, quiet=False, silent=False, get=None, stacklevel=1):
        ret_value = _default
        missing_exception = None
        try:
            ret_value = self.config[key]
        except BaseException as e:
            missing_exception = e
        if missing_exception:
            if required:
                self.logger.error(f"\"{key}\" is missing", stacklevel=stacklevel + 1)
                raise missing_exception
            ret_value = _default
        if get != None:
            try:
                ret_value = get(ret_value)
            except BaseException as e:
                self.logger.exception(e, stacklevel=stacklevel + 1)
                raise e
        if missing_exception:  # was defaulted
            # self.logger.info(f"using default \"{key}\" = {ret_value}", stacklevel=stacklevel+1)
            if not silent:
                self.logger.info(f"using {XT.Green}default{XT.RESET} \"{key}\" = {XT.Green}{ret_value}{XT.RESET}", stacklevel=stacklevel + 1)
        else:
            if not quiet:
                self.logger.info(f"using \"{key}\" = {XT.Cyan3}{ret_value}{XT.RESET}", stacklevel=stacklevel + 1)
        return ret_value

    def __setitem__(self, key, value):
        if self.config == None:
            self.config = {}
        self.config[key] = value

    def load(self, config_file: "str | Path", stacklevel=1):
        config_file: "Path" = Path(config_file)
        self.config: "dict" = None
        self.config_file = config_file
        if not config_file.exists():
            self.logger.error(f"config file \"{config_file}\" does not exist", stacklevel=stacklevel + 1)
            return
        _, ext = os.path.splitext(config_file)
        if ext == ".json":
            with open(config_file, "r") as f:
                self.config = json.load(f)
        # elif ext == ".yaml":
        #     import yaml
        #     with open(config_file, "r") as f:
        #         config = yaml.load(f)
        else:
            error = f"unrecognized config file \"{config_file}\""
            self.logger.error(error, stacklevel=stacklevel + 1)
            raise Exception(error)

    def save(self, config_file: "str | Path" = None, stacklevel=1):
        if config_file == None:
            config_file = self.config_file
        if config_file == None:
            return None
        config_file: "Path" = Path(config_file)
        self.config_file = config_file
        _, ext = os.path.splitext(config_file)
        if ext == ".json":
            with open(config_file, "w") as f:
                json.dump(self.config, f)
        # elif ext == ".yaml":
        #     import yaml
        #     with open(config_file, "r") as f:
        #         config = yaml.load(f)
        else:
            error = f"unrecognized config file \"{config_file}\""
            self.logger.error(error, stacklevel=stacklevel + 1)
            raise Exception(error)

    def sub(self, key: "str | int", _default=None, required=True, quiet=True, silent=False, get=None, stacklevel=1, name=None):
        if name == None:
            name = f"{key}"
        value = self.get(key, _default=_default, required=required, quiet=quiet, silent=silent, get=get, stacklevel=stacklevel + 1)
        config = Config(value, logger=self.logger.sub(name))
        config.parent = self
        return config

    def __bool__(self):
        return self.config

    def __len__(self):
        return len(self.config)

    def __iter__(self):
        # def gen():
        if type(self.config) == dict:
            for key in self.config:
                yield self.sub(key)
        elif type(self.config) == list:
            for i, key in enumerate(self.config):
                yield self.sub(i)
