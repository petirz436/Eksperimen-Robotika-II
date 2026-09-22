cmake_minimum_required(VERSION 3.0.2)
project(eksbot_simulation)

find_package(catkin REQUIRED COMPONENTS
  rospy
  sensor_msgs
  geometry_msgs
  std_msgs
  cv_bridge
  gazebo_ros
  urdf
  xacro
)

catkin_package()

catkin_install_python(PROGRAMS
  scripts/visionTarget.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY launch worlds models urdf scripts
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
