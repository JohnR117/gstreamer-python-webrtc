import gi
import sys
gi.require_version('GLib', '2.0')
gi.require_version('Gst', '1.0')
from gi.repository import GObject, GLib, Gst

try:
    gi.require_version('GstWebRTC', '1.0')
    from gi.repository import GstWebRTC
except:
    pass

try:
    gi.require_version('GstSdp', '1.0')
    from gi.repository import GstSdp
except:
    pass
try:
    gi.require_version('GstRtspServer', '1.0')
    from gi.repository import GstRtspServer
except:
    pass


Gst.init(sys.argv)
