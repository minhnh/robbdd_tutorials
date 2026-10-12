cmake_minimum_required(VERSION 3.8)
project(robbdd_tutorials)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
ament_python_install_package(${PROJECT_NAME})

install(
  DIRECTORY config launch models behavior_trees
  DESTINATION share/${PROJECT_NAME}
)

option(ROBBDD_BUILD_ISAAC_BT "Build the Isaac tree integration test" OFF)
if(ROBBDD_BUILD_ISAAC_BT AND BUILD_TESTING)
  find_package(bdd_bt_executor_ros2 REQUIRED)
  find_package(ament_cmake_gtest REQUIRED)
  ament_add_gtest(test_isaac_bt test/test_isaac_bt.cpp)
  target_compile_features(test_isaac_bt PRIVATE cxx_std_17)
  ament_target_dependencies(test_isaac_bt bdd_bt_executor_ros2)
  target_compile_definitions(test_isaac_bt PRIVATE
    TUTORIAL_CONFIG="${CMAKE_CURRENT_SOURCE_DIR}/config/isaac_pick_place.yaml"
    TUTORIAL_TREE="${CMAKE_CURRENT_SOURCE_DIR}/behavior_trees/isaac_prepare.xml")
endif()

ament_package()
