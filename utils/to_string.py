from utils.gst import GObject, GLib, Gst
import utils.gstapp as gstapp
from utils.logger import logger

def _gst_elements_filter_sources(elements: "list[Gst.Element]"):
    return [element for element in elements if len(element.sinkpads) <= 0]

def gst_bin_get_sources(bin: "Gst.Bin") -> "list[Gst.Element]":
    return _gst_elements_filter_sources(reversed(bin.children))

def gst_element_get_next(element: "Gst.Element") -> "list[Gst.Element]":
    srcpads: "list[Gst.Pad]" = element.srcpads
    destpads: "list[Gst.Pad]" = [pad.peer for pad in srcpads]
    return [pad.get_parent() for pad in destpads]

def gst_element_is_muxer(element: "Gst.Element"):
    return len(element.sinkpads) > 1

def gst_bin_to_string(bin: "Gst.Bin"):
    # elements = bin.get_by_interface(Gst.Element.__gtype__)
    # elements = bin.children
    sources = gst_bin_get_sources(bin)
    sequences: "list[list[Gst.Element]]" = []
    seen = {}
    while True:
        try:
            current = sources.pop(0)
        except:
            break
        sequence = [current]
        while True:
            steps = gst_element_get_next(current)
            if len(steps) != 1:
                break
            sequence.append(steps[0])
            current = steps[0]
            if gst_element_is_muxer(current):
                was_seen = seen.get(current.name, None)
                seen[current.name] = True
                if was_seen:
                    sources.append(current)
                break
        sequences.append(sequence)
    pipe = ""
    for sequence in sequences:        
        for i, element in enumerate(sequence):
            is_muxer = gst_element_is_muxer(element)
            if i == 0 or not is_muxer:
                factory: "Gst.ElementFactory" = element.get_factory()
                pipe += factory.name
                if is_muxer:
                    pipe += f" name={element.name}"
                for prop in element.list_properties():
                    prop: "GObject.ParamSpec"
                    # print(prop)
            else:
                pipe += element.name + "."
            if i < len(sequence) - 1:
                pipe += " ! "
        pipe += " "
    return pipe


def test_1():
    pipeline = gstapp.Pipeline()
    pipe = "videotestsrc pattern=0 ! capsfilter caps=\"video/x-raw, format=I420\" ! x264enc tune=zerolatency ! h264parse config-interval=-1 ! mpegtsmux. "
    pipe += "fakesrc ! capsfilter caps=\"meta/x-klv\" ! mpegtsmux. "
    pipe += "mpegtsmux name=mpegtsmux ! fakesink"
    pipeline.parse_launch(pipe)


    logger.info(gst_bin_to_string(pipeline.pipeline))
    pass

if __name__ == "__main__":
    test_1()