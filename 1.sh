#!/bin/bash

width=400
height=430

# echo ${width}
# echo sink_0::xpos=$((1*width))

gst-launch-1.0 \
  compositor name=comp \
    sink_0::xpos=$((0*width)) sink_0::ypos=$((0*height)) \
    sink_1::xpos=$((1*width)) sink_1::ypos=$((0*height)) \
    sink_2::xpos=$((2*width)) sink_2::ypos=$((0*height)) \
    sink_3::xpos=$((3*width)) sink_3::ypos=$((0*height)) \
    sink_4::xpos=$((0*width)) sink_4::ypos=$((1*height)) \
    sink_5::xpos=$((1*width)) sink_5::ypos=$((1*height)) \
    sink_6::xpos=$((2*width)) sink_6::ypos=$((1*height)) \
    sink_7::xpos=$((3*width)) sink_7::ypos=$((1*height)) ! \
      videoconvert ! autovideosink \
  multifilesrc location=\"outputs/00/frame%d.png\" index=1 caps=\"image/png,framerate=30/1\" ! decodebin ! videoscale ! capsfilter caps=\"video/x-raw, width=640, height=420\" ! queue2 ! comp.sink_0 \
  multifilesrc location=\"outputs/01/frame%d.png\" index=1 caps=\"image/png,framerate=30/1\" ! decodebin ! videoscale ! capsfilter caps=\"video/x-raw, width=640, height=420\" ! queue2 ! comp.sink_1 \
  multifilesrc location=\"outputs/02/frame%d.png\" index=1 caps=\"image/png,framerate=30/1\" ! decodebin ! videoscale ! capsfilter caps=\"video/x-raw, width=640, height=420\" ! queue2 ! comp.sink_2 \
  multifilesrc location=\"outputs/03/frame%d.png\" index=1 caps=\"image/png,framerate=30/1\" ! decodebin ! videoscale ! capsfilter caps=\"video/x-raw, width=640, height=420\" ! queue2 ! comp.sink_3 \
  multifilesrc location=\"outputs/10/frame%d.png\" index=1 caps=\"image/png,framerate=30/1\" ! decodebin ! videoscale ! capsfilter caps=\"video/x-raw, width=640, height=420\" ! queue2 ! comp.sink_4 \
  multifilesrc location=\"outputs/11/frame%d.png\" index=1 caps=\"image/png,framerate=30/1\" ! decodebin ! videoscale ! capsfilter caps=\"video/x-raw, width=640, height=420\" ! queue2 ! comp.sink_5 \
  multifilesrc location=\"outputs/12/frame%d.png\" index=1 caps=\"image/png,framerate=30/1\" ! decodebin ! videoscale ! capsfilter caps=\"video/x-raw, width=640, height=420\" ! queue2 ! comp.sink_6 \
  multifilesrc location=\"outputs/13/frame%d.png\" index=1 caps=\"image/png,framerate=30/1\" ! decodebin ! videoscale ! capsfilter caps=\"video/x-raw, width=640, height=420\" ! queue2 ! comp.sink_7




# sink_0::alpha=1 sink_0::xpos={0*${width}} sink_0::ypos={0*${height}} \
#     sink_1::alpha=1 sink_1::xpos={1*${width}} sink_1::ypos={0*${height}} \
#     sink_2::alpha=1 sink_2::xpos={2*${width}} sink_2::ypos={0*${height}} \
#     sink_3::alpha=1 sink_3::xpos={3*${width}} sink_3::ypos={0*${height}} \
#     sink_4::alpha=1 sink_4::xpos={0*${width}} sink_4::ypos={1*${height}} \
#     sink_5::alpha=1 sink_5::xpos={1*${width}} sink_5::ypos={1*${height}} \
#     sink_6::alpha=1 sink_6::xpos={2*${width}} sink_6::ypos={1*${height}} \
#     sink_7::alpha=1 sink_7::xpos={3*${width}} sink_7::ypos={1*${height}} !