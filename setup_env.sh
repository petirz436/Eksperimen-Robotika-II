#!/bin/bash
# Script Konfigurasi Otomatis Network ROS Noetic (Local / Network)

# Default: Local Simulation Mode (localhost / 127.0.0.1)
export ROS_MASTER_URI=http://localhost:11311
export ROS_IP=127.0.0.1
unset ROS_HOSTNAME

# Detect active local IP if needed for network ROS (ESP32/ESP32-CAM)
ACTIVE_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
if [ -n "$ACTIVE_IP" ] && [ "$1" == "network" ]; then
    export ROS_IP=$ACTIVE_IP
    export ROS_MASTER_URI=http://$ACTIVE_IP:11311
    echo "[ROS ENV] Mode Network Aktif - ROS_IP: $ROS_IP | ROS_MASTER_URI: $ROS_MASTER_URI"
else
    echo "[ROS ENV] Mode Lokal Simulation Aktif - ROS_IP: $ROS_IP | ROS_MASTER_URI: $ROS_MASTER_URI"
fi

# Source Catkin Workspace
source /opt/ros/noetic/setup.bash
if [ -f "/home/fathir/eksbot2/catkin_ws/devel/setup.bash" ]; then
    source /home/fathir/eksbot2/catkin_ws/devel/setup.bash
    echo "[ROS ENV] Catkin Workspace eksbot2 berhasil di-source!"
fi
