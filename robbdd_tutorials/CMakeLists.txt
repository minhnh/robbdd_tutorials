cmake_minimum_required(VERSION 3.8)
project(robbdd_tutorials)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY config launch models
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
