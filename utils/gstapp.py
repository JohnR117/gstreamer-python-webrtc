from re import A
import typing
from .gst import Gst, GLib
import math
import os
import numpy as np
import json
from .logger import get_logger, Logger


from .ringbuffer import RingBuffer
from .event import Event

T = typing.TypeVar("T")


class Pipe:
    @staticmethod
    def appsrc(n): return f"appsrc name={n} emit-signals=true format=time is-live=true"
    @staticmethod
    def appsink(n): return f"appsink name={n} emit-signals=true async=false"
    @staticmethod
    def split_end(t, *branches, indent=""): return f"tee name={t} " + " ".join(f"{indent}{t}. ! queue max-size-buffers=1 ! {b}" for b in branches)
    @staticmethod
    def split(t, *branches, indent=""): return Pipe.split_end(t, *branches, "", indent=indent)

    class Split:
        def __init__(self, tee, indent="") -> None:
            self.tee = tee
            self.indent = indent
            self.branches = []

        def __setitem__(self, index, value):
            current_length = len(self.branches)
            diff = index + 1 - current_length
            if diff > 0:
                self.branches += [""] * diff
            self.branches[index] = value

        def __getitem__(self, index):
            if index < 0:
                raise IndexError(index)
            current_length = len(self.branches)
            diff = index + 1 - current_length
            if diff > 0:
                self.branches += [""] * diff
            return self.branches[index]

        def resolve(self):
            branches = list(filter(lambda s: s != "", self.branches))
            if len(branches) <= 0:
                return ""
            elif len(branches) == 1:
                return branches[0]
            return Pipe.split_end(self.tee, *branches, indent=self.indent)


DEFAULT_QUEUE = "queue max-size-buffers=1 leaky=downstream ! "


class Pipe:
    @staticmethod
    def appsrc(n): return f"appsrc name={n} emit-signals=true format=time is-live=true"
    @staticmethod
    def appsink(n): return f"appsink name={n} emit-signals=true async=false max-buffers=1 drop=true"
    # def appsink(n): return f"appsink name={n} emit-signals=true async=false"
    @staticmethod
    def split_end(t, *branches, queue=DEFAULT_QUEUE, indent=""): return f"tee name={t} " + " ".join(f"{indent}{t}. ! {queue}{b}" for b in branches)
    @staticmethod
    def split(t, *branches, indent=""): return Pipe.split_end(t, *branches, "", indent=indent)

    class Split:
        def __init__(self, tee, queue=DEFAULT_QUEUE, indent="") -> None:
            self.tee = tee
            self.queue = queue
            self.indent = indent
            self.branches = []

        def __setitem__(self, index, value):
            current_length = len(self.branches)
            diff = index + 1 - current_length
            if diff > 0:
                self.branches += [""] * diff
            self.branches[index] = value

        def __getitem__(self, index):
            if index < 0:
                raise IndexError(index)
            current_length = len(self.branches)
            diff = index + 1 - current_length
            if diff > 0:
                self.branches += [""] * diff
            return self.branches[index]

        def resolve(self):
            branches = list(filter(lambda s: s != "", self.branches))
            if len(branches) <= 0:
                return ""
            elif len(branches) == 1:
                return branches[0]
            return Pipe.split_end(self.tee, *branches, indent=self.indent, queue=self.queue)


class Pipeline:
    def __init__(self, pipeline: "Gst.Pipeline" = None):
        self.pipeline: "Gst.Pipeline" = None
        self.on_bus: "Event[typing.Callable[[Gst.Message],]]" = Event("on_bus")
        self.on_eos: "Event[typing.Callable[[],]]" = Event("on_eos")
        self.on_warning: "Event[typing.Callable[[GLib.Error, str],]]" = Event("on_warning")
        self.on_error: "Event[typing.Callable[[GLib.Error, str],]]" = Event("on_error")

        self.__bus_enabled = True
        self.__bus_handle_id = None
        self.__bus: "Gst.Bus" = None

        self.__is_owner = False

        self.enable_default()

        self.logger = get_logger()

        if self.pipeline:
            self.start(pipeline)

    def __del__(self):
        self.clear()
        # self.logger.warning("del Pipeline", stacklevel=2)
        self.on_eos.clear()
        self.on_warning.clear()
        self.on_error.clear()

    def clear(self):
        self.stop()

    def stop(self):
        self.__stop_bus()
        if self.__is_owner:
            # self.logger.warning("disown Pipeline", stacklevel=2)
            self.__disown()
        self.pipeline = None

    def _start(self, pipeline: "Gst.Pipeline"):
        self.pipeline = pipeline
        if self.pipeline:
            if self.__bus_enabled:
                self.__start_bus()

    def start(self, pipeline: "Gst.Pipeline"):
        self.stop()
        self._start(pipeline)

    def own(self, pipeline: "Gst.Pipeline"):
        self.stop()
        self.__is_owner = True
        self._start(pipeline)

    def __stop_bus(self):
        if self.__bus != None:
            if self.__bus_handle_id:
                self.__bus.disconnect(self.__bus_handle_id)
            self.__bus.remove_signal_watch()
        self.__bus_handle_id = None
        self.__bus = None

    def __start_bus(self):
        self.__bus: "Gst.Bus" = self.pipeline.get_bus()
        self.__bus.add_signal_watch()
        self.__bus_handle_id = self.__bus.connect("message", self.__on_bus_message)

    def __disown(self):
        # logger.error("disown")
        bus: "Gst.Bus" = self.pipeline.get_bus()
        bus.set_flushing(True)
        if self.pipeline != None:
            self.pipeline.set_state(Gst.State.NULL)
        self.pipeline = None
        self.__is_owner = False

    def __on_bus_message(self, bus: "Gst.Bus", message: "Gst.Message", user_data=None):
        self.on_bus(message)
        t = message.type
        if t == Gst.MessageType.EOS:
            self.on_eos()
        elif t == Gst.MessageType.WARNING:
            err, debug = message.parse_warning()
            self.on_warning(err, debug)
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            self.on_error(err, debug)

    def __default_on_eos(self):
        self.logger.info("EOS")

    def __default_on_warning(self, err, debug):
        self.logger.warning(f"{err}: {debug}")

    def __default_on_error(self, err, debug):
        self.logger.error(f"{err}: {debug}")

    def disable_default(self):
        try:
            self.on_eos -= self.__default_on_eos
        except:
            pass
        try:
            self.on_warning -= self.__default_on_warning
        except:
            pass
        try:
            self.on_error -= self.__default_on_error
        except:
            pass

    def enable_default(self):
        self.disable_default()
        self.on_eos += self.__default_on_eos
        self.on_warning += self.__default_on_warning
        self.on_error += self.__default_on_error

    def parse_launch(self, pipeline_description: "str", stacklevel=1):
        self.logger.pipeline(pipeline_description, stacklevel=stacklevel + 1)
        pipeline = Gst.parse_launch(pipeline_description)
        if pipeline.__gtype__ != Gst.Pipeline.__gtype__:
            __pipeline: "Gst.Pipeline" = Gst.Pipeline.new()
            __pipeline.add(pipeline)
            pipeline = __pipeline
        self.own(pipeline)

    def play(self):
        return self.pipeline.set_state(Gst.State.PLAYING)

    def pause(self):
        return self.pipeline.set_state(Gst.State.PAUSED)

    def null(self):
        return self.pipeline.set_state(Gst.State.NULL)

    # @property
    # def set_state(self):
    #     return self.pipeline.set_state

    # @property
    # def get_by_name(self):
    #     return self.pipeline.get_by_name


def parse_launch(pipeline_description, logger=get_logger()):
    pipeline = Pipeline()
    pipeline.logger = logger
    pipeline.parse_launch(pipeline_description)
    return pipeline


class Timeout:
    def __init__(self) -> None:
        self.__timeout: "GLib.Source" = None
        self.on_timeout: "Event[typing.Callable[[],]]" = Event("on_timeout")

    def __del__(self):
        # self.logger.warning("del Timeout")
        self.clear()

    def clear(self):
        self.stop()
        self.on_timeout.clear()

    def stop(self):
        if self.__timeout:
            self.__timeout.destroy()
        self.__timeout = None

    def _on_timeout(self, used_data=None):
        self.on_timeout()
        return False

    def start(self, interval):
        self.__timeout = GLib.timeout_source_new(interval)
        self.__timeout.set_callback(self._on_timeout)
        self.__timeout.attach()


class RestartTimeout:
    def __init__(self):
        self.__timeout: "GLib.Source" = None
        self.logger = get_logger()

        self.step_interval: "int" = 1000
        self.on_restart: "Event[typing.Callable[[],]]" = Event("on_restart")

    def __del__(self):
        # self.logger.warning("del RestartTimeout")
        self.clear()

    def clear(self):
        self.stop()
        self.on_restart.clear()

    def stop(self):
        if self.__timeout:
            self.__timeout.destroy()
        self.__timeout = None

    def start(self, interval):
        self.stop()
        steps = interval / self.step_interval
        countdown = steps
        step_time = int(interval / steps)
        self.logger.info(f"starting restart timeout, {interval / 1000} sec")
        self.__timeout = GLib.timeout_source_new(step_time)

        def _restart(user_data=None):
            nonlocal countdown
            if countdown <= 0:
                self.logger.warning("restarting.")
                self.on_restart()
                return False
            self.logger.info(f"will restart in {(countdown * step_time) / 1000} sec...")
            countdown -= 1
            return True
        self.__timeout.set_callback(_restart)
        self.__timeout.attach()


class DataCheck:
    def __init__(self, interval: "int"):
        self.__timeout: "GLib.Source" = None
        self.logger = get_logger()

        self.has_data = False
        self.on_data_start: "Event[typing.Callable[[],]]" = Event("on_data_start")
        self.on_data_stop: "Event[typing.Callable[[],]]" = Event("on_data_stop")
        self.interval = interval

    def __del__(self):
        # self.logger.warning("del DataCheck")
        self.clear()

    def clear(self):
        self.stop()
        self.on_data_start.clear()
        self.on_data_stop.clear()

    def stop(self):
        if self.__timeout:
            self.__timeout.destroy()
        self.__timeout = None

    def feed(self):
        self.stop()
        had_data = self.has_data
        if not had_data:
            self.on_data_start()
        self.has_data = True
        self.__timeout = GLib.timeout_source_new(self.interval)

        def _mark_no_data(user_data=None):
            self.has_data = False
            self.on_data_stop()
            return False
        self.__timeout.set_callback(_mark_no_data)
        self.__timeout.attach()


class Object:
    def __init__(self) -> None:
        pass


class IStart:
    start: "typing.Callable[[],]"
    stop: "typing.Callable[[],]"
    # def start(self, *args, **kwargs) -> "any":
    #     raise Exception("\"start\" not implemented")
    # def stop(self, *args, **kwargs) -> "any":
    #     raise Exception("\"stop\" not implemented")


class AppSrc():
    def __init__(self, appsrc: "Gst.Element" = None) -> None:
        self.appsrc: "Gst.Element" = None
        self.__need_data_handler_id: "int" = None
        self.__enough_data_handler_id: "int" = None
        self.on_need_data: "Event[typing.Callable[[Gst.Element, int], None]]" = Event("on_need_data")
        self.on_enough_data: "Event[typing.Callable[[Gst.Element], None]]" = Event("on_enough_data")
        self.on_push_sample: "Event[typing.Callable[[Gst.Sample], None]]" = Event("on_push_sample")

        self._appsink: "AppSink" = None

        if appsrc != None:
            self.start(appsrc)

        self.logger = get_logger()

    @property
    def appsink(self):
        return self._appsink

    @appsink.setter
    def appsink(self, appsink: "AppSink"):
        if self._appsink != None:
            self.appsink.on_pulled_sample -= self.push_sample
        self._appsink = appsink
        if self._appsink:
            self._appsink.on_pulled_sample += self.push_sample

    def __on_need_data(self, appsrc: "Gst.Element", length, user_data=None):
        self.on_need_data(appsrc, length)

    def __on_enough_data(self, appsrc, user_data=None):
        self.on_enough_data(appsrc)

    def __del__(self):
        self.clear()
        # self.logger.warning("del AppSrc", stacklevel=2)

    def clear(self):
        self.appsink = None
        self.stop()
        self.on_need_data.clear()
        self.on_enough_data.clear()
        self.on_push_sample.clear()

    def stop(self):
        if self.appsrc != None:
            if self.__need_data_handler_id != None:
                self.appsrc.disconnect(self.__need_data_handler_id)
            if self.__enough_data_handler_id != None:
                self.appsrc.disconnect(self.__enough_data_handler_id)
        self.__need_data_handler_id = None
        self.__enough_data_handler_id = None
        self.appsrc = None

    def start(self, appsrc: "Gst.Element"):
        self.stop()
        self.appsrc = appsrc
        if self.appsrc:
            self.__need_data_handler_id = self.appsrc.connect("need-data", self.__on_need_data)
            self.__enough_data_handler_id = self.appsrc.connect("enough-data", self.__on_enough_data)

    def push_sample(self, sample: "Gst.Sample"):
        # logger.info(f"push sample {sample}")
        self.on_push_sample(sample)
        return self.appsrc.emit("push-sample", sample)

    def push_buffer(self, buffer: "Gst.Buffer"):
        return self.appsrc.emit("push-buffer", buffer)


class AppSink:
    def __init__(self, appsink: "Gst.Element" = None) -> None:
        self.appsink: "Gst.Element" = None
        self.on_new_sample: "Event[typing.Callable[[self],Gst.FlowReturn]]" = Event("on_new_sample")
        self.on_pulled_sample: "Event[typing.Callable[[Gst.Sample],]]" = Event("on_pulled_sample")
        self.__new_sample_handler_id: "int" = None

        self.__on_new_sample_pull: "typing.Callable[[self],Gst.FlowReturn]" = None
        self.__on_new_sample_timeout: "GLib.Source" = None
        self.__on_pulled_sample_modify_dts_pts: "typing.Callable[[Gst.Sample],]" = None

        self.last_sample: "Gst.Sample" = None

        if appsink != None:
            self.start(appsink)

        self.logger = get_logger()

    def __del__(self):
        self.clear()
        # self.logger.warning("del AppSink", stacklevel=2)

    def clear(self):
        self.disable_auto_pull()
        self.disable_auto_pull_ring()
        self.disable_const_pull()
        self.disable_clear_dts_pts()
        self.on_new_sample.clear()
        self.on_pulled_sample.clear()
        self.stop()

    def stop(self):
        if self.appsink != None:
            if self.__new_sample_handler_id != None:
                self.appsink.disconnect(self.__new_sample_handler_id)
        self.__new_sample_handler_id = None
        if self.__on_new_sample_timeout != None:
            self.__on_new_sample_timeout.destroy()
        self.__on_new_sample_timeout = None
        self.appsink = None

    def start(self, appsink: "Gst.Element"):
        self.stop()
        self.appsink = appsink
        if self.appsink:
            self.appsink.set_property("emit-signals", True)
            self.__new_sample_handler_id = self.appsink.connect("new-sample", self.__on_new_sample)

    def _try_pull_sample(self, timeout: int) -> "Gst.Sample":
        return self.appsink.emit("try-pull-sample", timeout)

    def try_pull_sample(self, timeout: int) -> "Gst.Sample":
        sample = self._try_pull_sample(timeout)
        self.last_sample = sample
        self.on_pulled_sample(sample)
        return sample

    def __on_new_sample(self, _appsink):
        if len(self.on_new_sample) > 0:
            return self.on_new_sample(self)
        return Gst.FlowReturn.OK

    def disable_clear_dts_pts(self):
        if self.__on_pulled_sample_modify_dts_pts:
            self.on_pulled_sample -= self.__on_pulled_sample_modify_dts_pts
        self.__on_pulled_sample_modify_dts_pts = None

    def enable_clear_dts_pts(self, clear_dts=True, clear_pts=False):
        self.disable_clear_dts_pts()

        def __on_pulled_sample_clear_dts_pts(sample: "Gst.Sample"):
            # self.logger.debug(f"clear dts")
            buffer: "Gst.Buffer" = sample.get_buffer()
            if clear_dts:
                buffer.dts = 0
            if clear_pts:
                buffer.pts = 0
            return Gst.FlowReturn.OK
        self.__on_pulled_sample_modify_dts_pts = __on_pulled_sample_clear_dts_pts
        self.on_pulled_sample.insert(0, self.__on_pulled_sample_modify_dts_pts, False)

    def disable_const_duration(self):
        if self.__on_pulled_sample_modify_dts_pts:
            self.on_pulled_sample -= self.__on_pulled_sample_modify_dts_pts
        self.__on_pulled_sample_modify_dts_pts = None

    def enable_const_duration(self, duration: "int" = Gst.SECOND / 30):
        self.disable_const_duration()
        running_time = 0

        def __on_pulled_sample_const_duration(sample: "Gst.Sample"):
            nonlocal running_time
            buffer: "Gst.Buffer" = sample.get_buffer()
            buffer.dts = 0
            buffer.pts = running_time
            buffer.duration = duration
            running_time += duration
            return Gst.FlowReturn.OK
        self.__on_pulled_sample_modify_dts_pts = __on_pulled_sample_const_duration
        self.on_pulled_sample.insert(0, self.__on_pulled_sample_modify_dts_pts, False)

    def disable_auto_pull(self):
        if self.__on_new_sample_pull:
            self.on_new_sample -= self.__on_new_sample_pull
        self.__on_new_sample_pull = None

    def enable_auto_pull(self, timeout=Gst.USECOND):
        self.disable_auto_pull()

        def __on_new_sample_pull(_self):
            # self.logger.debug("auto pull")
            self.try_pull_sample(timeout)
            return Gst.FlowReturn.OK
        self.__on_new_sample_pull = __on_new_sample_pull
        self.on_new_sample += self.__on_new_sample_pull

    def disable_auto_pull_ring(self):
        if self.__on_new_sample_pull:
            self.on_new_sample -= self.__on_new_sample_pull
        self.__on_new_sample_pull = None

    def enable_auto_pull_ring(self, size: "int", timeout=Gst.USECOND):
        self.disable_auto_pull_ring()
        ring: "RingBuffer[Gst.Sample]" = RingBuffer(size)

        def __on_new_sample_pull(_self):
            sample = self._try_pull_sample(timeout)
            # self.logger.debug(f"auto pull ring")
            self.last_sample = sample
            new_on_pulled_sample = self.on_pulled_sample.get_new()
            if len(new_on_pulled_sample) > 0:
                samples = tuple(ring)
                for on_pulled_sample in new_on_pulled_sample:
                    for _sample in samples:
                        on_pulled_sample(_sample)
            ring.push(sample)
            self.on_pulled_sample(sample)
            # self.try_pull_sample(timeout)
            return Gst.FlowReturn.OK
        self.__on_new_sample_pull = __on_new_sample_pull
        self.on_new_sample += self.__on_new_sample_pull

    def disable_const_pull(self):
        if self.__on_new_sample_pull:
            self.on_new_sample -= self.__on_new_sample_pull
        self.__on_new_sample_pull = None

        if self.__on_new_sample_timeout != None:
            self.__on_new_sample_timeout.destroy()
        self.__on_new_sample_timeout = None

    def enable_const_pull(self, timeout=30 * Gst.MSECOND):
        self.disable_const_pull()

        def __on_new_sample_pull(_self):
            if self.__on_new_sample_timeout == None:
                # self.logger.info("start")
                self.__on_new_sample_timeout: "GLib.Source" = GLib.timeout_source_new(int(timeout / Gst.MSECOND))
                # self.__on_new_sample_timeout: "GLib.Source" = GLib.timeout_source_new(100)

                def pull_push(user_data=None):
                    # self.logger.info("pull_push")
                    try:
                        sample = self.try_pull_sample(timeout)
                    except:
                        sample = None
                    if sample == None:
                        self.__on_new_sample_timeout = None
                        return False
                    return True
                self.__on_new_sample_timeout.set_callback(pull_push)
                self.__on_new_sample_timeout.attach()
                # pull_push()
            # GLib.idle_add(add_timeout)
            return Gst.FlowReturn.OK
        self.__on_new_sample_pull = __on_new_sample_pull
        self.on_new_sample += self.__on_new_sample_pull


class Sample():
    def __init__(self, sample: "Gst.Sample") -> None:
        self.sample: "Gst.Sample" = sample
        self.mapinfo: "Gst.MapInfo" = None

    @property
    def buffer(self) -> "Gst.Buffer":
        return self.sample.get_buffer()

    def __del__(self):
        self.clear()
        # logger.warning("del Sample", stacklevel=2)

    def clear(self):
        self.unmap()

    def unmap(self):
        if self.mapinfo != None:
            self.buffer.unmap(self.mapinfo)
        self.mapinfo = None

    def map(self, flags: "Gst.MapFlags"):
        self.unmap()
        ret, mapinfo = self.buffer.map(flags)
        if ret:
            self.mapinfo = mapinfo
        return ret

    def read(self):
        return self.map(Gst.MapFlags.READ)

    def as_mat(self):
        caps: "Gst.Caps" = self.sample.get_caps()
        st: "Gst.Structure" = caps.get_structure(0)
        ret, width = st.get_int("width")
        ret, height = st.get_int("height")
        bbp = 3
        size = width * height * bbp
        data = np.frombuffer(self.mapinfo.data, np.uint8, size)
        data = np.reshape(data, (height, width, bbp))
        return data

    def as_bytes(self):
        return self.mapinfo.data

    def as_string(self):
        data = str(self.mapinfo.data, encoding="utf-8")
        return data

    def as_json(self):
        data = json.loads(str(self.mapinfo.data, encoding="utf-8"))
        return data

    def get_caps(self) -> "Gst.Caps":
        return self.sample.get_caps()


class Demux():
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.__pad_added_handler_id: "int" = None
        self.__pad_removed_handler_id: "int" = None
        self.__no_more_pads_handler_id: "int" = None
        self.on_pad_added: "Event[typing.Callable[[Gst.Element, Gst.Pad],]]" = Event("on_pad_added")
        self.on_pad_removed: "Event[typing.Callable[[Gst.Element, Gst.Pad],]]" = Event("on_pad_removed")
        self.on_no_more_pads: "Event[typing.Callable[[Gst.Element],]]" = Event("on_no_more_pads")
        self.demux: "Gst.Element" = None

    def __del__(self):
        self.clear()

    def clear(self):
        self.stop()
        self.on_pad_added.clear()
        self.on_pad_removed.clear()
        self.on_no_more_pads.clear()

    def stop(self):
        if self.demux != None:
            if self.__pad_added_handler_id != None:
                self.demux.disconnect(self.__pad_added_handler_id)
            if self.__pad_removed_handler_id != None:
                self.demux.disconnect(self.__pad_removed_handler_id)
            if self.__no_more_pads_handler_id != None:
                self.demux.disconnect(self.__no_more_pads_handler_id)
        self.__pad_added_handler_id = None
        self.__pad_removed_handler_id = None
        self.__no_more_pads_handler_id = None
        self.demux = None

    def start(self, demux, *args, **kwargs):
        self.stop()
        self.demux = demux
        self.pad_added_handler_id = self.demux.connect("pad-added", self.__on_pad_added)
        self.pad_removed_handler_id = self.demux.connect("pad-removed", self.__on_pad_removed)
        self.no_more_pads_handler_id = self.demux.connect("no-more-pads", self.__on_no_more_pads)

    def __on_pad_added(self, demux: "Gst.Element", pad: "Gst.Pad", user_data=None):
        return self.on_pad_added(demux, pad)

    def __on_pad_removed(self, demux: "Gst.Element", pad: "Gst.Pad", user_data=None):
        return self.on_pad_removed(demux, pad)

    def __on_no_more_pads(self, demux: "Gst.Element", user_data=None):
        return self.on_no_more_pads(demux)


class Pad:
    def __init__(self, pad: "Gst.Pad" = None):
        self.pad: "Gst.Pad" = None

        # data count
        self.__data_count_enabled = False
        self.__data_count_probe_id: "int" = None
        self.__data_count = 0

        # data count pull
        self.__data_count_auto_pull_enabled = False
        self.__timeout: "GLib.Source" = None
        self.__interval: "int" = 1000  # 1 sec
        self.on_data_count: "Event[typing.Callable[[int],]]" = Event("on_data_count")

        self.__eos_enabled = False
        self.__eos_probe_id: "int" = None
        self.on_eos: "Event[typing.Callable[[],]]" = Event("on_eos")

        if pad != None:
            self.start(pad)

    @property
    def data_count(self):
        return self.__data_count

    def __del__(self):
        self.clear()
        get_logger().warning("del Pad", stacklevel=2)

    def clear(self):
        self.stop()
        self.on_data_count.clear()
        self.on_eos.clear()

    def stop(self):
        self.__stop_data_count_auto_pull()
        self.__stop_data_count()
        self.pad = None

    def start(self, pad: "Gst.Pad"):
        self.stop()
        self.pad = pad
        if self.pad:
            if self.__data_count_enabled:
                self.__start_data_count()
                if self.__data_count_auto_pull_enabled:
                    self.__start_data_count_auto_pull()
            if self.__eos_enabled:
                self.__start_eos()

    def __data_count_on_pad_probe(self, pad: "Gst.Pad", info: "Gst.PadProbeInfo", user_data=None):
        self.__data_count += 1
        return Gst.PadProbeReturn.OK

    def __eos_on_pad_probe(self, pad: "Gst.Pad", info: "Gst.PadProbeInfo", user_data=None):
        event = info.get_event()
        if event.type == Gst.EventType.EOS:
            # logger.info("EOS ~~~~~ PROBE")
            # self.on_eos()
            # GLib.idle_add(lambda: self.on_eos())
            GLib.idle_add(self.on_eos)
        return Gst.PadProbeReturn.OK

    def __data_count_auto_pull_timeout_callback(self, user_data=None):
        data_count = self.pad.data_count
        self.on_data_count(data_count)
        return True

    # data_count
    def __stop_data_count(self):
        if self.pad:
            if self.__data_count_probe_id:
                self.pad.remove_probe(self.__data_count_probe_id)
        self.__data_count_probe_id = None
        self.__data_count = 0

    def __start_data_count(self):
        self.__data_count_probe_id = self.pad.add_probe(Gst.PadProbeType.BUFFER, self.__data_count_on_pad_probe)

    def disable_data_count(self):
        self.__data_count_enabled = False
        self.__stop_data_count()

    def enable_data_count(self):
        self.__data_count_enabled = True

    # data_count_auto_pull
    def __stop_data_count_auto_pull(self):
        if self.__timeout != None:
            self.__timeout.destroy()
        self.__timeout = None

    def __start_data_count_auto_pull(self):
        self.__timeout = GLib.timeout_source_new(self.__interval)
        self.__timeout.add_callback(self.__data_count_auto_pull_timeout_callback)
        self.__timeout.attach()

    def disable_data_count_auto_pull(self):
        self.__data_count_auto_pull_enabled = False
        self.__stop_data_count_auto_pull()

    def enable_data_count_auto_pull(self, interval: "int"):
        self.__interval = interval
        self.__data_count_auto_pull_enabled = True

    # eos
    def __stop_eos(self):
        if self.pad:
            if self.__eos_probe_id:
                self.pad.remove_probe(self.__eos_probe_id)
        self.__eos_probe_id = None
        self.__eos = 0

    def __start_eos(self):
        self.__eos_probe_id = self.pad.add_probe(Gst.PadProbeType.EVENT_DOWNSTREAM, self.__eos_on_pad_probe)

    def disable_eos(self):
        self.__eos_enabled = False
        self.__stop_eos()

    def enable_eos(self):
        self.__eos_enabled = True


import enum


@enum.unique
class GST_FORMAT(str, enum.Enum):
    GRAY16_LE = "GRAY16_LE"
    GRAY16_BE = "GRAY16_BE"
    RGBx = "RGBx"
    xRGB = "xRGB"
    BGRx = "BGRx"
    xBGR = "xBGR"
    RGBA = "RGBA"
    ARGB = "ARGB"
    BGRA = "BGRA"
    ABGR = "ABGR"
    RGB = "RGB"
    BGR = "BGR"
    GRAY8 = "GRAY8"

    def __str__(self):
        return str(self.value)


def mat_to_formats(mat: np.ndarray):
    w, h, c = mat.shape
    if c == 1:
        if mat.dtype == np.uint16:
            return ["GRAY16_BE", "GRAY16_LE"]
        elif mat.dtype == np.uint8:
            return ["GRAY8"]
    elif c == 3:
        return ["BGR", "RGB"]
    elif c == 4:
        return ["RGBA", "BGRA", "RGBx", "xRGB", "BGRx", "xBGR", "ARGB", "ABGR"]
    return []


def mat_to_caps(mat: "np.ndarray", framerate: "int", format: "GST_FORMAT" = None) -> "Gst.Caps":
    h, w, c = mat.shape
    if format == None:
        format = mat_to_formats(mat)[0]
    return Gst.caps_from_string(f"video/x-raw, width={w}, height={h}, format={format}, framerate={framerate}/1")


def mat_to_buffer(mat: "np.ndarray", dts=0, pts=0) -> "Gst.Buffer":
    buffer: "Gst.Buffer" = Gst.Buffer.new_wrapped(mat.tobytes())
    buffer.dts = dts
    buffer.pts = pts
    return buffer


def mat_to_sample(mat: "np.ndarray", dts: int, pts: int, caps: "Gst.Caps") -> "Gst.Sample":
    return Gst.Sample.new(mat_to_buffer(mat, dts, pts), caps)


class AppSrcMatSender:
    def __init__(self, framerate: "int" = 0) -> None:
        super().__init__()
        self.caps = None
        self.framerate = framerate
        self.running_time = 0
        self.appsrc = AppSrc()

    @property
    def framerate(self):
        return self._framerate

    @framerate.setter
    def framerate(self, framerate):
        self._framerate = framerate
        self._diff = Gst.SECOND / framerate
        self.caps = None

    def __del__(self):
        self.clear()

    def clear(self):
        self.stop()

        self.appsrc.clear()

    def stop(self) -> "any":
        self.appsrc.stop()
        self.caps = None
        self.running_time = 0

    def start(self, appsrc) -> "any":
        self.stop()
        self.appsrc.start(appsrc)

    def push_mat(self, mat: "np.ndarray"):
        if self.caps == None:
            self.caps = mat_to_caps(mat, self.framerate)
        sample = mat_to_sample(mat, 0, self.running_time, self.caps)
        self.running_time += self._diff
        # self.appsrc.on_data(sample)
        self.appsrc.push_sample(sample)

    @property
    def push_sample(self):
        return self.appsrc.push_sample

    @property
    def push_buffer(self):
        return self.appsrc.push_buffer

    @property
    def on_need_data(self):
        return self.appsrc.on_need_data

    @on_need_data.setter
    def on_need_data(self, on_need_data):
        self.appsrc.on_need_data = on_need_data

    @property
    def on_enough_data(self):
        return self.appsrc.on_enough_data

    @on_enough_data.setter
    def on_enough_data(self, on_enough_data):
        self.appsrc.on_enough_data = on_enough_data

    @property
    def appsink(self):
        return self.appsrc.appsink

    @appsink.setter
    def appsink(self, appsink):
        self.appsrc.appsink = appsink


class Display():
    def __init__(self, framerate) -> None:
        self.appsrc = AppSrcMatSender(framerate)
        self.pipeline = Pipeline()

        self.logger = get_logger()

    @property
    def framerate(self):
        return self.appsrc.framerate

    @framerate.setter
    def framerate(self, framerate):
        self.appsrc.framerate = framerate

    def __del__(self):
        self.clear()
        self.logger.warning("del Display", stacklevel=2)

    def clear(self):
        self.stop()

    def stop(self):
        self.appsrc.stop()
        self.pipeline.stop()

    def start(self, *args, **kwargs) -> "any":
        self.stop()
        pipe = ""
        pipe += "appsrc"
        pipe += " name=appsrc"
        pipe += " is-live=true"
        pipe += " ! "
        pipe += "videoconvert ! "
        # pipe += "identity dump=true ! "
        # pipe += "nveglglessink sync=false"
        pipe += "autovideosink sync=false"
        # pipe += "fakesink dump=true"
        # pipe += "gtksink sync=false"
        self.pipeline.parse_launch(pipe)
        self.appsrc.start(self.pipeline.pipeline.get_by_name("appsrc"))
        self.pipeline.play()
