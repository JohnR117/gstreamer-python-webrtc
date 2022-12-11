FROM nvcr.io/nvidia/deepstream-l4t:6.1.1-samples
# ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y \
    wget \
    curl \
    zip \
    nasm \
    git \
    pkg-config \
    flex \
    bison \
    \
    python3 \
    python3-dev \
    python3-pip \
    \
    libavc1394-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavfilter-dev \
    libavformat-dev \
    libavutil-dev \
    \
    libssl-dev \
    libgnutls28-dev \
    \
    libunistring-dev \
    \
    libpciaccess-dev \
    \
    libsrtp2-dev \
    \
    libx264-dev \
    libx265-dev \
    libde265-dev \
    \
    libssl-dev \
    libgnutls28-dev \
    \
    g++-9 \
    gcc-9 \
    \    
    libuv1-dev \
    \
    net-tools \
    iputils-ping \
    avahi-daemon \
    avahi-utils \
    libnss-mdns \
    && \
    python3 -m pip install --upgrade pip && \
    python3 -m pip install --upgrade cmake && \
    python3 -m pip install --upgrade meson && \
    python3 -m pip install --upgrade ninja && \
    python3 -m pip install --upgrade numpy
    
    
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

ENV PATH=$PATH:/root/.cargo/bin

RUN cargo install cargo-c && \
    python3 -m pip install --upgrade tomli
    
RUN (rm -r /usr/include/glib-2.0 || echo) && \
    (mkdir -p /opts || echo) && cd /opts && \
    git clone https://gitlab.gnome.org/GNOME/glib --depth 1 --branch 2.72.0 -o glib && cd glib && \
    mkdir build && cd build && \
    meson .. --prefix /usr && \
    meson compile && \
    meson install

RUN (mkdir -p /opts || echo) && cd /opts && \
    git clone https://gitlab.gnome.org/GNOME/glib-networking --depth 1 --branch 2.72.0 -o glib-networking && cd glib-networking && \
    mkdir build && cd build && \
    meson .. --prefix /usr && \
    meson compile && \
    meson install

RUN (mkdir -p /opts || echo) && cd /opts && \
    git clone https://gitlab.gnome.org/GNOME/gobject-introspection --depth 1 --branch 1.72.0 -o gobject-introspection && cd gobject-introspection && \
    mkdir build && cd build && \
    meson .. --prefix /usr && \
    meson compile && \
    meson install


RUN apt-get install nano
RUN pip3 install sanic
RUN apt-get remove --purge -y libavc1394-dev libavcodec-dev libavdevice-dev libavfilter-dev libavformat-dev libavutil-dev

RUN (mkdir -p /opts || echo) && cd /opts && \
    git clone https://gitlab.freedesktop.org/gstreamer/gstreamer --branch 1.20 --depth 1  && cd gstreamer && \
    mkdir build && cd build && \
    meson .. --prefix /usr -Dgpl=enabled -Dgst-plugins-ugly:x264=enabled -Drs=enabled && \
    meson compile && \
    meson install

RUN mkdir -p /app
WORKDIR /app

