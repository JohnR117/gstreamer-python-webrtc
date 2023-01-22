#!/bin/bash

xhost +
echo -e "Running webrtc docker ..\nOpen browser : localhost:5555"

sudo docker run -d --rm --net=host --runtime nvidia  -e DISPLAY=$DISPLAY -w /app -v /home/dspip/Desktop/webrtc_python/gstreamer-python-webrtc/webrtc_code:/app --device /dev/video0 --device /dev/video2 --device /dev/video4 -v /tmp/.X11-unix/:/tmp/.X11-unix webrtc python3 webrtc_cameras.py
