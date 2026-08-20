# Astro-Nex Python 3 - Entorno de desarrollo
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Mexico_City

ENV DISPLAY=:0
ENV LIBGL_ALWAYS_INDIRECT=1

ARG USERNAME=astronex
ARG USER_UID=1000
ARG USER_GID=1000

# Ubuntu 24.04 trae usuario 'ubuntu' con UID 1000, lo eliminamos primero
RUN userdel -r ubuntu 2>/dev/null || true \
    && groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m -s /bin/bash $USERNAME

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    python3-venv \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y \
    wget \
    curl \
    fonts-dejavu \
    fontconfig \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gtk-3.0 \
    libgtk-3-0 \
    libcairo2 \
    libcairo2-dev \
    libgirepository1.0-dev \
    libpango-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libatk1.0-0 \
    libglib2.0-0 \
    pkg-config \
    x11-apps \
    xauth \
    nano \
    git \
    xdg-utils \
    evince \
    eog \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir --break-system-packages \
    configobj \
    tzdata \
    pillow \
    pycairo \
    PyGObject \
    pyswisseph

USER $USERNAME
WORKDIR /home/$USERNAME

RUN mkdir -p /home/$USERNAME/.Astronex /home/$USERNAME/.fonts

WORKDIR /home/$USERNAME/app

CMD ["python3", "nex.py"]
