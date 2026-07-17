FROM osrf/ros:humble-desktop

# Hindari interaksi selama instalasi apt
ENV DEBIAN_FRONTEND=noninteractive

# Install utilitas dasar + dependensi development
RUN apt-get update && apt-get install -y \
    git \
    python3-pip \
    sudo \
    curl \
    udev \
    gosu \
    bash-completion \
    htop \
    vim \
    nano \
    ros-humble-rmw-cyclonedds-cpp \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/YDLidar/YDLidar-SDK.git /tmp/YDLidar-SDK && \
    mkdir -p /tmp/YDLidar-SDK/build && \
    cd /tmp/YDLidar-SDK/build && \
    cmake .. && \
    make -j$(nproc) && \
    make install && \
    rm -rf /tmp/YDLidar-SDK

# Copy workspace package lists dan resolve dependensi via rosdep
COPY src/ /tmp/amr_ws/src/
RUN apt-get update && \
    rosdep update && \
    rosdep install --from-paths /tmp/amr_ws/src --ignore-src -y -r && \
    rm -rf /tmp/amr_ws /var/lib/apt/lists/*

# Install python packages tambahan yang tidak terdaftar di package.xml
RUN pip3 install minimalmodbus keyboard

# Setup User Development (dev) agar UID & GID match dengan host (1000)
ARG USERNAME=dev
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# Tambahkan user ke group dialout dan plugdev untuk akses serial port
RUN usermod -aG dialout,plugdev,video,render $USERNAME

# Copy & Setup Entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Sourcing otomatis di shell interaktif (.bashrc)
RUN echo "source /opt/ros/humble/setup.bash" >> /home/$USERNAME/.bashrc \
    && echo "if [ -f /home/$USERNAME/amr_ws/install/setup.bash ]; then source /home/$USERNAME/amr_ws/install/setup.bash; fi" >> /home/$USERNAME/.bashrc \
    && echo "export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp" >> /home/$USERNAME/.bashrc \
    && echo "export CYCLONEDDS_URI=/home/$USERNAME/amr_ws/cyclonedds.xml" >> /home/$USERNAME/.bashrc

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/bin/bash"]
