#!/usr/bin/python3
import asyncio
import enum
import functools
import json
import logging
import os
import re
import signal
import sys
import threading
import typing
from datetime import datetime
from io import TextIOWrapper
from pathlib import Path
from random import sample
import os.path

import numpy as np
import sanic.response as response
import sanic.request as request
from google.protobuf.json_format import MessageToDict, MessageToJson
from sanic import Sanic
from sanic.server.websockets.impl import WebsocketImplProtocol

import utils.sanic_utils as sanic_utils
import utils.gstapp as gstapp
import utils.logger as LOGGER
from utils.config import Config, path_make
from utils.event import Event
from utils.gst import GLib, Gst, GstSdp, GstWebRTC
from utils.logger import XT, Logger, get_logger, load_package_logger


class WebRTCBin:
    def __init__(self, webrtcbin: "Gst.Element" = None) -> None:
        self.webrtcbin: "Gst.Element" = None

        self.on_negotiation_needed: "Event[typing.Callable[[],]]" = Event("on_negotiation_needed")
        self.on_ice_candidate: "Event[typing.Callable[[int, str],]]" = Event("on_ice_candidate")

        self.on_create_offer: "Event[typing.Callable[[GstWebRTC.WebRTCSessionDescription],]]" = Event("on_create_offer")
        self.on_create_answer: "Event[typing.Callable[[GstWebRTC.WebRTCSessionDescription],]]" = Event("on_create_answer")
        self.on_set_local_description: "Event[typing.Callable[[GstWebRTC.WebRTCSessionDescription],]]" = Event("on_set_local_description")
        self.on_set_remote_description: "Event[typing.Callable[[GstWebRTC.WebRTCSessionDescription],]]" = Event("on_set_remote_description")

        self.__on_negotiation_needed_handler_id = None
        self.__on_ice_candidate_handler_id = None

        self.__create_offer_promise: "Gst.Promise" = None
        self.__create_answer_promise: "Gst.Promise" = None

        self.on_negotiation_needed += lambda *a, **kw: self.logger.debug(f"on_negotiation_needed")
        self.on_create_offer += lambda *a, **kw: self.logger.debug(f"on_create_offer")
        self.on_create_answer += lambda *a, **kw: self.logger.debug(f"on_create_answer")
        self.on_set_local_description += lambda *a, **kw: self.logger.debug(f"on_set_local_description")
        self.on_set_remote_description += lambda *a, **kw: self.logger.debug(f"on_set_remote_description")

        self.on_negotiation_needed += self.create_offer
        self.on_create_offer += self.set_local_description
        self.on_create_answer += self.set_local_description

        self.logger = get_logger()

        if webrtcbin != None:
            self.start(webrtcbin)

    def __del__(self):
        self.clear()
        # self.logger.warning("del WebRTCBin", stacklevel=2)

    def clear(self):
        self.stop()
        self.on_negotiation_needed.clear()
        self.on_ice_candidate.clear()
        self.on_create_offer.clear()
        self.on_create_answer.clear()
        self.on_set_local_description.clear()
        self.on_set_remote_description.clear()
        if self.__create_offer_promise:
            self.__create_offer_promise.expire()
        self.__create_offer_promise = None
        if self.__create_answer_promise:
            self.__create_answer_promise.expire()
        self.__create_answer_promise = None

    def stop(self):
        if self.webrtcbin != None:
            if self.__on_negotiation_needed_handler_id != None:
                self.webrtcbin.disconnect(self.__on_negotiation_needed_handler_id)
            if self.__on_ice_candidate_handler_id != None:
                self.webrtcbin.disconnect(self.__on_ice_candidate_handler_id)

        self.__on_negotiation_needed_handler_id = None
        self.__on_ice_candidate_handler_id = None
        self.webrtcbin = None

    def start(self, webrtcbin: "Gst.Element"):
        self.stop()
        self.webrtcbin = webrtcbin
        if self.webrtcbin:
            self.__on_negotiation_needed_handler_id = self.webrtcbin.connect("on-negotiation-needed", self.__on_negotiation_needed)
            self.__on_ice_candidate_handler_id = self.webrtcbin.connect("on-ice-candidate", self.__on_ice_candidate)

    def __on_negotiation_needed(self, webrtcbin: "Gst.Element", user_data=None):
        self.on_negotiation_needed()

    def __on_ice_candidate(self, webrtcbin: "Gst.Element", sdpMLineIndex: "int", candidate: "str", user_data=None):
        self.on_ice_candidate(sdpMLineIndex, candidate)

    def create_offer(self, options: "Gst.Structure" = None):
        self.__create_offer_promise = promise = Gst.Promise.new_with_change_func(self.__on_create_offer)
        return self.webrtcbin.emit("create-offer", options, promise)

    def __on_create_offer(self, promise: "Gst.Promise"):
        reply: "Gst.Structure" = promise.get_reply()
        try:
            sdp: "GstWebRTC.WebRTCSessionDescription" = reply["offer"]
        except:
            sdp: "GstWebRTC.WebRTCSessionDescription" = reply.get_value("offer")
        self.on_create_offer(sdp)

    def create_answer(self, options: "Gst.Structure" = None):
        self.__create_answer_promise = promise = Gst.Promise.new_with_change_func(self.__on_create_answer)
        return self.webrtcbin.emit("create-answer", options, promise)

    def __on_create_answer(self, promise: "Gst.Promise"):
        reply: "Gst.Structure" = promise.get_reply()
        sdp: "GstWebRTC.WebRTCSessionDescription" = reply["answer"]
        self.on_create_answer(sdp)

    def set_local_description(self, sdp):
        _promise = Gst.Promise.new()
        self.webrtcbin.emit("set-local-description", sdp, _promise)
        _promise.interrupt()
        self.on_set_local_description(sdp)

    def set_remote_description(self, sdp: "GstWebRTC.WebRTCSessionDescription"):
        _promise = Gst.Promise.new()
        self.webrtcbin.emit('set-remote-description', sdp, _promise)
        _promise.interrupt()
        self.on_set_remote_description(sdp)

    def add_ice_candidate(self, sdpMLineIndex, candidate):
        self.webrtcbin.emit('add-ice-candidate', sdpMLineIndex, candidate)

    def create_datachannel(self, name: "str", options: "Gst.Structure" = None) -> GstWebRTC.WebRTCDataChannel:
        datachannel: GstWebRTC.WebRTCDataChannel = self.webrtcbin.emit("create-data-channel", name, options)
        return datachannel


class DataChannel:
    def __init__(self):

        self.datachannel: "GstWebRTC.WebRTCDataChannel" = None
        self.as_text = False
        self.name: "str" = None

        self.logger = get_logger()

    def __del__(self):
        self.clear()

    def clear(self):
        self.datachannel = None


PROTO = typing.TypeVar("PROTO")


class DataChannelProtobuf(DataChannel):

    def __init__(self) -> None:
        super().__init__()
        self._event: "Event[typing.Callable[[PROTO],]]" = None

    def __del__(self):
        super().__del__()

    def clear(self):
        self.event = None
        super().clear()

    @property
    def event(self):
        return self._event

    @event.setter
    def event(self, event: "Event[typing.Callable[[PROTO],]]"):
        if self._event:
            self._event -= self.on_protobuf
        self._event = event
        if self._event:
            self._event += self.on_protobuf

    def on_protobuf(self, proto: "PROTO"):
        # logger.error(f"on_protobuf()")
        datachannel = self.datachannel
        if not datachannel:
            return
        ready_state: "GstWebRTC.WebRTCDataChannelState" = datachannel.get_property("ready-state")
        if ready_state != GstWebRTC.WebRTCDataChannelState.OPEN:
            return
        if self.as_text:
            datachannel.send_string(MessageToJson(proto))
        else:
            datachannel.send_data(proto.SerializeToString())


class DataChannelAppSink(DataChannel):

    def __init__(self) -> None:
        super().__init__()
        self._appsink: "gstapp.AppSink" = None
        self._event: "Event[typing.Callable[[Gst.Sample],Gst.FlowReturn]]" = None

    def __del__(self):
        # self.logger.warning("del DataChannelAppSink", stacklevel=2)
        super().__del__()

    def clear(self):
        self.event = None
        self.appsink = None
        super().clear()

    @property
    def event(self):
        return self._event

    @event.setter
    def event(self, event: "Event[typing.Callable[[Gst.Sample],Gst.FlowReturn]]"):
        if self._event:
            self._event -= self.on_sample
        self._event = event
        if self._event:
            self._event += self.on_sample

    @property
    def appsink(self):
        return self._appsink

    @appsink.setter
    def appsink(self, appsink: "gstapp.AppSink"):
        if self._appsink:
            self._appsink.on_pulled_sample -= self.on_sample
        self._appsink = appsink
        if self._appsink:
            self._appsink.on_pulled_sample += self.on_sample

    @property
    def event(self):
        return self._event

    @event.setter
    def event(self, event: "Event[typing.Callable[[Gst.Sample],Gst.FlowReturn]]"):
        if self._event:
            self._event -= self.on_sample
        self._event = event
        if self._event:
            self._event += self.on_sample

    def on_sample(self, _sample: "Gst.Sample"):
        sample = gstapp.Sample(_sample)
        sample.read()
        datachannel = self.datachannel
        ready_state: "GstWebRTC.WebRTCDataChannelState" = datachannel.get_property("ready-state")
        if ready_state != GstWebRTC.WebRTCDataChannelState.OPEN:

            return Gst.FlowReturn.OK
        if self.as_text:
            datachannel.send_string(sample.as_string())
        else:
            datachannel.send_data(sample.as_bytes())
        return Gst.FlowReturn.OK


class Branch:
    def __init__(self):
        self.appsrc: "gstapp.AppSrc" = None
        self.bin: "Gst.Bin" = None

        self._appsink: "gstapp.AppSink" = None
        self.target: "Gst.Element" = None

        self.logger = get_logger()

    @property
    def appsink(self):
        return self._appsink

    @appsink.setter
    def appsink(self, appsink: gstapp.AppSink):
        if self._appsink:
            self._appsink.on_pulled_sample -= self.on_pulled_sample
        self._appsink = appsink
        if self._appsink:
            self._appsink.on_pulled_sample += self.on_pulled_sample

    def on_pulled_sample(self, _sample: "Gst.Sample"):
        _buffer: "Gst.Buffer" = _sample.get_buffer()
        buffer: "Gst.Buffer" = _buffer.copy()
        buffer.dts = 0
        buffer.pts = 0
        sample = Gst.Sample.new(buffer, _sample.get_caps(), _sample.get_segment(), _sample.get_info())


        if self.appsrc:
            self.appsrc.push_sample(sample)

    def __del__(self):
        self.clear()

    def clear(self):
        self.stop()
        self.appsink = None
        self.target = None

    def stop(self):
        if self.appsrc:
            self.appsrc.clear()
        self.appsrc = None
        if self.bin:
            if self.target != None:
                self.bin.unlink(self.target)
                pipeline: "Gst.Bin" = self.target.parent
                if pipeline and self.bin:
                    pipeline.remove(self.bin)
        self.bin = None
        self.target = None

    def start(self, target: "Gst.Element"):
        self.stop()
        pipe = ""
        pipe += gstapp.Pipe.appsrc("appsrc")

        self.logger.bin(pipe)
        self.bin: "Gst.Bin" = Gst.parse_bin_from_description(pipe, True)
        self.appsrc = gstapp.AppSrc(self.bin.get_by_name("appsrc"))
        pipeline: "Gst.Bin" = target.parent
        pipeline.add(self.bin)
        self.bin.link(target)
        self.bin.sync_state_with_parent()


def get_sdp_type(data: typing.Any):
    if type(data) == str:
        if data == "offer":
            return GstWebRTC.WebRTCSDPType.OFFER
        elif data == "pranswer":
            return GstWebRTC.WebRTCSDPType.PRANSWER
        elif data == "answer":
            return GstWebRTC.WebRTCSDPType.ANSWER
        elif data == "rollback":
            return GstWebRTC.WebRTCSDPType.ROLLBACK
    elif type(data) == int:
        if data in [
            GstWebRTC.WebRTCSDPType.OFFER,
            GstWebRTC.WebRTCSDPType.PRANSWER,
            GstWebRTC.WebRTCSDPType.ANSWER,
            GstWebRTC.WebRTCSDPType.ROLLBACK
        ]:
            return data
    return None


def get_sdp_message(data: typing.Any) -> GstSdp.SDPMessage:
    if type(data) != str:
        return None
    try:  # added in 1.16
        sdp_result, sdp_message = GstSdp.SDPMessage.new_from_text(data)
        if sdp_result == GstSdp.SDPResult.OK:
            return sdp_message
    except:
        pass
    sdp_result, sdp_message = GstSdp.SDPMessage.new()
    sdp_result = GstSdp.SDPMessage.parse_buffer(bytes(data, "utf8"), sdp_message)
    return sdp_message
    # answer = GstWebRTC.WebRTCSessionDescription.new(GstWebRTC.WebRTCSDPType.ANSWER, sdp_message)


def sdp_from_dict(data: "dict") -> GstWebRTC.WebRTCSessionDescription:
    sdp_type = get_sdp_type(data.get("type", None))
    sdp_message = get_sdp_message(data.get("sdp", None))
    if sdp_type == None or sdp_message == None:
        return None
    return GstWebRTC.WebRTCSessionDescription.new(sdp_type, sdp_message)


def sdp_to_dict(sdp: GstWebRTC.WebRTCSessionDescription) -> dict:
    return {
        "type": GstWebRTC.webrtc_sdp_type_to_string(sdp.type),
        "sdp": sdp.sdp.as_text(),
    }


class Viewer:
    def __init__(self):
        # self.websocket = websocket
        self.websocket: "WebsocketImplProtocol" = None
        self.event_loop: "asyncio.AbstractEventLoop" = None

        self.pipeline = gstapp.Pipeline()
        self.webrtcbin = WebRTCBin()
        self.webrtcbin.on_ice_candidate += self.on_ice_candidate
        self.webrtcbin.on_set_local_description += self.on_set_local_description

        self.branches: "list[Branch]" = []
        self.datachannels: "dict[str, DataChannel]" = {}

        self.__delayed_add_branch: "list[Branch]" = []
        self.__delayed_add_datachannel: "list[DataChannel]" = []

        self._logger: "Logger" = None
        self.logger = get_logger()

    @property
    def logger(self):
        return self._logger

    @logger.setter
    def logger(self, logger):
        self._logger = logger
        self.webrtcbin.logger = logger
        self.pipeline.logger = logger

    async def _send(self, *a, **kw):
        # self.logger.debug(f"_send({a}, {kw})")
        try:
            if self.websocket != None:
                await self.websocket.send(*a, **kw)
            # self.websocket.send(*a, **kw)
        except BaseException as e:
            self.logger.exception(e)

    def send(self, *a, **kw):
        # self.logger.debug(f"send({a}, {kw})")
        asyncio.run(self._send(*a, **kw))
        # async def _send(): await
        # self.event_loop.call_soon(lambda: self._send(*a, **kw))
        # asyncio.run_coroutine_threadsafe(self._send(*a, **kw), self.event_loop)

    def __del__(self):
        self.clear()
        # self.logger.warning("del Viewer", stacklevel=2)

    def clear(self):
        self.stop()
        for branch in self.__delayed_add_branch:
            branch.clear()
        self.__delayed_add_branch.clear()
        for datachannel in self.__delayed_add_datachannel:
            datachannel.clear()
        self.__delayed_add_datachannel.clear()
        self.webrtcbin.clear()
        self.websocket = None

    def stop(self):
        for branch in self.branches:
            branch.clear()
            branch = None
        self.branches = []
        for name, datachannel in self.datachannels.items():
            datachannel.datachannel = None
            datachannel.clear()
            datachannel = None
        self.datachannels.clear()
        # self.datachannels = {}
        self.webrtcbin.stop()
        self.pipeline.stop()

    def start(self):
        self.stop()
        # self.pipeline.parse_launch("webrtcbin name=webrtcbin latency=0 stun-server=\"stun://l.google.com:19302\"")
        self.pipeline.parse_launch("webrtcbin name=webrtcbin latency=0")
        self.webrtcbin.start(self.pipeline.pipeline.get_by_name("webrtcbin"))
        for branch in self.__delayed_add_branch:
            self.__add_branch(branch)
            branch = None
        self.__delayed_add_branch.clear()
        ret = self.pipeline.play()
        for datachannel in self.__delayed_add_datachannel:
            self.__add_datachannel(datachannel)
            datachannel = None
        self.__delayed_add_datachannel.clear()
        # self.webrtcbin.on_negotiation_needed()

    def __add_branch(self, branch: "Branch"):
        branch.start(self.webrtcbin.webrtcbin)
        self.branches.append(branch)

    def add_branch(self, branch: "Branch"):
        if self.pipeline.pipeline != None:
            self.__add_branch(branch)
        else:
            self.__delayed_add_branch.append(branch)

    def __add_datachannel(self, datachannel: "DataChannel"):
        datachannel.datachannel = self.webrtcbin.create_datachannel(datachannel.name)
        self.datachannels[datachannel.name] = datachannel

    def add_datachannel(self, datachannel: "DataChannel"):
        if self.pipeline.pipeline != None:
            self.__add_datachannel(datachannel)
        else:
            self.__delayed_add_datachannel.append(datachannel)

    def on_set_local_description(self, sdp: "GstWebRTC.WebRTCSessionDescription"):
        self.logger.debug(f"on_set_local_description: {sdp}")
        self.send(json.dumps({
            "type": "sdp",
            "data": sdp_to_dict(sdp)
        }))

    def on_ice_candidate(self, sdpMLineIndex: "int", candidate: "str"):
        self.logger.debug(f"on_ice_candidate: {sdpMLineIndex}, {candidate}")
        self.send(json.dumps({
            "type": "ice",
            "data": {
                "sdpMLineIndex": sdpMLineIndex,
                "candidate": candidate,
            }
        }))

    def handle(self, message):
        try:
            message = json.loads(message)
            _type = message.get("type", None)
            if _type != None:
                data = message.get("data", None)
                # assert data != None
                if _type == "sdp":
                    self.handle_sdp(data)
                elif _type == "ice":
                    self.handle_ice(data)
        except BaseException as e:
            self.logger.exception(e)

    def handle_ice(self, data):
        self.logger.debug(f"handle_ice: {data}")
        if data == None:
            return
        sdpMLineIndex = data['sdpMLineIndex']
        candidate = data['candidate']
        self.webrtcbin.add_ice_candidate(sdpMLineIndex, candidate)

    def handle_sdp(self, data):
        self.logger.debug(f"handle_sdp: {data}")
        remote_description = sdp_from_dict(data)
        if remote_description == None:
            self.logger.warning(f"failed to handle_sdp, {data}")
            return
        sdp_string = remote_description.sdp.as_text().replace('\r', '').split('\n')
        self.logger.debug(f"sdp: {sdp_string}")
        self.webrtcbin.set_remote_description(remote_description)

    def test(self):
        self.stop()
        self.pipeline.parse_launch("videotestsrc ! video/x-raw, format=I420 ! x264enc tune=zerolatency ! rtph264pay config-interval=-1 ! webrtcbin name=webrtcbin latency=0")
        self.webrtcbin.start(self.pipeline.pipeline.get_by_name("webrtcbin"))
        self.pipeline.play()


class CameraToWebRTC:
    def __init__(self) -> None:
        self._camera: "Camera" = None
        self.__viewers: "list[Viewer]" = []
        self.running_number = 0
        self.logger = get_logger()

    @property
    def camera(self):
        return self._camera

    @camera.setter
    def camera(self, camera: "Camera"):

        current_viewers = list(self.__viewers)
        for viewer in current_viewers:
            self.remove(viewer)
        self._camera = camera
        if self._camera != None:
            self.logger = self._camera.logger
        for viewer in current_viewers:
            self.add(viewer)

    def remove(self, viewer: Viewer):
        try:
            self.__viewers.remove(viewer)
            viewer.stop()
            viewer.logger.info("removed")
        except BaseException as ex:
            pass


    def add(self, viewer: Viewer):
        self.remove(viewer)
        self.__viewers.append(viewer)
        try:
            branch = Branch()
            branch.logger = viewer.logger.sub("video")
            branch.appsink = self.camera.webrtc_appsink
            viewer.add_branch(branch)

            viewer.start()
        except BaseException as ex:
            self.logger.exception(ex)
        
    async def handle(self, request, websocket: WebsocketImplProtocol):
        viewer = Viewer()
        viewer.event_loop = asyncio.get_event_loop()
        viewer.websocket = websocket
        running_number = self.running_number
        viewer.logger = self.logger.sub(f"{running_number}")
        self.running_number += 1
        try:
            self.add(viewer)
            # viewer.test()
            while True:
                message = await websocket.recv()
                if message == None:
                    break
                viewer.handle(message)
        except asyncio.exceptions.CancelledError:
            pass
        except BaseException as e:
            self.logger.exception(e)
        viewer.websocket = None
        # TODO consider implementing logger destructor
        self.remove(viewer)
        viewer.clear()
        viewer = None


class Camera:
    def __init__(self) -> None:
        self.pipeline = gstapp.Pipeline()
        self.pipeline.on_error += self.on_error
        self.pipeline.on_eos += self.on_eos
        self.restart = gstapp.RestartTimeout()
        self.restart.on_restart += self.start

        self.webrtc_appsink = gstapp.AppSink()
        self.webrtc_appsink.enable_auto_pull_ring(60)

        self.uri: "str" = None
        self.uri2: "str" = None
        self.uri3: "str" = None
        self.uri4: "str" = None

        self._logger: "Logger" = None
        self.logger = get_logger()

    @property
    def logger(self):
        return self._logger

    @logger.setter
    def logger(self, logger):
        self._logger = logger
        self.restart.logger = logger
        self.pipeline.logger = logger

    def __del__(self):
        self.clear()
        self.logger.warning("del Camera", stacklevel=2)

    def clear(self):
        self.stop()
        self.restart.clear()
        self.webrtc_appsink.clear()
        self.pipeline.clear()

    def stop(self):
        self.restart.stop()
        self.webrtc_appsink.stop()
        self.pipeline.stop()

    def start(self):
        self.stop()
        width = 800
        height = 600

        a = os.path.exists("/dev/video0") 
        b = os.path.exists("/dev/video2")
        c = os.path.exists("/dev/video4") 
        d = os.path.exists("/dev/video6") 
        pipe = ""

        if a:
            pipe += f"v4l2src device=\"/dev/video0\" ! capsfilter caps=\"image/jpeg, width=800, height=600\" ! jpegdec ! videoscale method=0 add-borders=false ! videoconvert ! compositor.sink_0 "
        if b:
            pipe += f"v4l2src device=\"/dev/video2\" ! capsfilter caps=\"image/jpeg, width=800, height=600\" ! jpegdec ! videoscale method=0 add-borders=false ! videoconvert ! compositor.sink_1 "
        if c:
            pipe += f"v4l2src device=\"/dev/video4\" ! capsfilter caps=\"image/jpeg, width=800, height=600\" ! jpegdec ! videoscale method=0 add-borders=false ! videoconvert ! compositor.sink_2 "
        if d:
            pipe += f"v4l2src device=\"/dev/video6\" ! capsfilter caps=\"image/jpeg, width=800, height=600\" ! jpegdec ! videoscale method=0 add-borders=false ! videoconvert ! compositor.sink_3 "

        pipe += "compositor name=compositor "
        if a:
            pipe += f" sink_0::xpos={0 * width} sink_0::ypos={0 * height}"
        if b:
            pipe += f" sink_1::xpos={1 * width} sink_1::ypos={0 * height}"
        if c:
            pipe += f" sink_2::xpos={1 * width} sink_2::ypos={1 * height}"
        if d:
        # pipe += f" sink_3::xpos={3 * width} sink_3::ypos={0 * height}"
            pipe += f" sink_3::xpos={0 * width} sink_3::ypos={1 * height}"
        # pipe += f" sink_5::xpos={1 * width} sink_5::ypos={1 * height}"
        # pipe += f" sink_6::xpos={2 * width} sink_6::ypos={1 * height}"
        # pipe += f" sink_7::xpos={3 * width} sink_7::ypos={1 * height}"
        pipe += " ! "


        #### Run with H264

        pipe += "capsfilter caps=\"video/x-raw, format=I420\" ! "
        # pipe += "videoscale ! capsfilter caps=\"video/x-raw, width=1920, height=1080\" ! "

        pipe += "x264enc tune=zerolatency key-int-max=30 ! "
        pipe += "h264parse config-interval=-1 ! "
        pipe += "rtph264pay config-interval=-1 pt=96 ! "


        #### Run with AV1

        # pipe += "rav1enc low-latency=true error-resilient=true max-key-frame-interval=30 speed-preset=10  ! "
        # pipe += "av1parse ! "
        # pipe += "rtpav1pay pt=96 ! "
        # pipe += "identity dump=true ! "
        pipe += gstapp.Pipe.appsink("webrtc_appsink")

        self.pipeline.parse_launch(pipe)
        self.webrtc_appsink.start(self.pipeline.pipeline.get_by_name("webrtc_appsink"))
        self.pipeline.play()

    def on_error(self, err, debug):
        self.restart.start(5000)

    def on_eos(self):
        self.restart.start(100)


def main():
    logger = load_package_logger(level=logging.DEBUG)

    main_loop = GLib.MainLoop()
    glib_thread = threading.Thread(target=lambda: main_loop.run(), daemon=True)
    glib_thread.start()

    app = Sanic(__name__)
    logging.getLogger("sanic.root").propagate = False
    logging.getLogger("sanic.error").propagate = False
    logging.getLogger("sanic.access").propagate = False
    logging.getLogger("sanic.server").propagate = False
    app.register_listener(sanic_utils.setup_options, "before_server_start")
    app.register_middleware(sanic_utils.add_cors_headers, "response")
    app.static("/", f"{Path()/ 'public'}", name="static")
    app.static("/", f"{Path()/ 'public' / 'index.html'}", name="index")

    camera_to_webrtc = CameraToWebRTC()

    def switch_camera(file1, file2,file3, file4):
        if camera_to_webrtc.camera != None:
            camera_to_webrtc.camera.clear()
        camera = Camera()
        camera.uri = file1
        camera.uri2 = file2
        camera.uri3 = file3
        camera.uri4 = file4

        camera.start()
        camera_to_webrtc.camera = camera

    switch_camera(None, None, None, None)


    #### Send post ####

    # @app.route("/rtsp", methods=["GET", "POST"])
    # def api_rtsp(request: "request.Request"):
    #     file1 = request.json["file1"]
    #     file2 = request.json["file2"]
    #     file3 = request.json["file3"]
    #     file4 = request.json["file4"]

    #     print("file1:",file1) 
    #     print("file2:",file2)       
    #     switch_camera(file1, file2, file3, file4)

        # return response.json({})

    app.add_websocket_route(camera_to_webrtc.handle, "/ws")

    try:
        port = int(os.environ.get("PORT", 5555))
        app.run("0.0.0.0", port=port, single_process=True)
    except:
        pass


if __name__ == "__main__":
    main()
