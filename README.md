# RobBDD tutorials

Models and runtime setups for robot acceptance tests with RobBDD and BDDX.
This README covers setup, running tests, configuration, and debugging. For the
modeling and observation walkthrough, see the
[acceptance-testing tutorials](https://minhnh.github.io/bdd-dsl/at-tutorial-scenarios.html).

## Contents

<!-- mtoc-start -->

1. [Setup](#setup)
    1. [Dependencies and setup options](#dependencies-and-setup-options)
1. [Launch files](#launch-files)
1. [Run the MuJoCo acceptance test](#run-the-mujoco-acceptance-test)
1. [Run the Isaac acceptance test](#run-the-isaac-acceptance-test)
    1. [Standalone Isaac debugging](#standalone-isaac-debugging)
1. [Configuration](#configuration)
1. [Offline checks](#offline-checks)

<!-- mtoc-end -->

## Setup

Clone this package under a ROS workspace's `src` directory, then select one context:

```sh
mkdir -p ~/ros_bdd_ws/src
git clone https://github.com/minhnh/robbdd_tutorials.git ~/ros_bdd_ws/src/robbdd_tutorials
cd ~/ros_bdd_ws/src/robbdd_tutorials
./scripts/setup mujoco jazzy
# Or: ./scripts/setup isaacsim-bt jazzy
source ~/ros_bdd_ws/setup-robbdd-tutorials.bash  # or .zsh
```

Source the generated environment in every terminal. It activates the Python
virtual environment and ROS overlays and provides:

- `roscd robbdd_tutorials`: open the package directory.
- `bdd_ws build`: reinstall editable Python packages and rebuild the selected context.
- `bdd_ws pull`: update dependency repositories; fetch the Isaac fork without advancing its branch.

### Dependencies and setup options

- **Required:** ROS 2 Jazzy on Ubuntu 24.04, with the ROS apt repository configured.
- **Required:** Git, Git LFS, `build-essential`, CMake, `python3-vcs2l`,
  `python3-colcon-common-extensions`, `python3-rosdep`, and `python3-venv`.
- **MuJoCo only:** Ant.
- **Isaac only:** Isaac Sim, installed separately with ROS bridge and simulation interfaces enabled.
- **Optional:** uv; setup otherwise uses pip.

Setup offers to install prerequisites with `sudo apt install`, then uses rosdep
for ROS dependencies. Initialize rosdep once with `sudo rosdep init` if needed.

- `--install-system-packages`: opt in during noninteractive setup.
- `--build`: rebuild without cloning repositories or installing system packages.
- Repository lists: [common](repos/common.repos), [MuJoCo](repos/mujoco.repos),
  [Isaac](repos/isaacsim-bt.repos). Python sources go under `pydeps`, ROS packages under `src`.
- MuJoCo setup builds the motion-spec dependencies with ROS support and configures
  their workspace, generated-output, and install paths in the sourced environment.
- Isaac setup clones [the workspace fork](https://github.com/minhnh/IsaacSim-ros_workspaces)
  into sibling `../IsaacSim-ros_workspaces` and builds its matching `${ROS_DIST}_ws`.
  Override that path with `ROBBDD_ISAAC_ROS_WS`.
  + The fork's `fix/jazzy-asyncio-sleep` branch fixes the gripper callback error in
    [Isaac workspace issue #27](https://github.com/isaac-sim/IsaacSim-ros_workspaces/issues/27).
    Initial setup requires a clean checkout; rebuilds allow local edits.
  + Setup/build pulls the Panda world USD through Git LFS and sources the Isaac
    underlay before the tutorial workspace. There is no Isaac version-selection argument.

## Launch files

Each launch has a separate role; run only one Isaac BT server at a time.

| Launch | Purpose |
| --- | --- |
| [pick_place_coordinator.launch.yaml](launch/pick_place_coordinator.launch.yaml) | MuJoCo BDD coordinator; the motion-spec runtime starts separately. |
| [isaac_moveit.launch.xml](launch/isaac_moveit.launch.xml) | MoveIt, controllers, robot TF, gripper bridge, and optional RViz. |
| [isaac_prepare.launch.yaml](launch/isaac_prepare.launch.yaml) | Standalone BT server at `/bdd/prepare`; select inspection, planning-only, or motion through `tree_xml`. |
| [isaac_observations.launch.yaml](launch/isaac_observations.launch.yaml) | Includes the BT server and Isaac BDD coordinator; `/bdd/start` loads/resets the scene and starts evaluation. |

Use `ros2 launch robbdd_tutorials <launch-file> --show-args` for all arguments.

## Run the MuJoCo acceptance test

The `motion-spec` command runs the simulator and behavior; the coordinator evaluates
the test. Source the generated workspace environment in every terminal. If another
runtime is running, use the same unused `ROS_DOMAIN_ID` in all test terminals.

```sh
# Terminal 1: wait for S_WAIT; add --headless to omit the GUI.
motion-spec run "$(ros2 pkg prefix --share robbdd_tutorials)/models/pick_place/mujoco_motion_spec/pick_place_single.robmot" --rtf 1
# Terminal 2:
ros2 launch robbdd_tutorials pick_place_coordinator.launch.yaml
# Terminal 3: optional viewer at http://127.0.0.1:8080.
ros2 run bdd_exec_ros2 web_visualizer
# Terminal 4: subscribe before triggering.
ros2 topic echo /bdd/status
# Terminal 5: trigger one test.
ros2 topic pub --once /bdd/start std_msgs/msg/Empty '{}'
```

Expect the Behaviour result and all three policies (at-pick, held, at-place) to
finish with `TRUE`. Keep `--rtf 1` to match the coordinator's wall clock.
See the [MuJoCo integration guide](https://minhnh.github.io/bdd-dsl/at-tutorial-execution-mujoco.html)
for the model and evidence wiring.

## Run the Isaac acceptance test

Start Isaac Sim with the ROS bridge and simulation interfaces enabled. Source
the generated environment in every terminal. Load the positive-case scene once
before starting MoveIt so Panda exists and publishes joint states; keep Isaac playing.
Reusable `BehaviourTree.CPP` node APIs are described in the executor's
[BT node reference](https://github.com/minhnh/bdd_bt_executor_ros2/blob/main/docs/bt_nodes.md).

```sh
# Terminal 1: run from the workspace root.
bdd_ws build
source setup-robbdd-tutorials.bash  # .zsh for zsh
ros2 run bdd_exec_ros2 sim_interface_test load-scene \
  --scene-model "$(ros2 pkg prefix --share robbdd_tutorials)/models/pick_place/isaacsim/pick_place_positive.scenex"
```

```sh
# Terminal 2: RViz is optional and defaults to off.
LC_NUMERIC=en_US.UTF-8 ros2 launch robbdd_tutorials isaac_moveit.launch.xml start_rviz:=true
# Terminal 3: includes the BT server; stop any standalone server first.
ros2 launch robbdd_tutorials isaac_observations.launch.yaml readiness_timeout:=120.0
# Terminal 4: subscribe before triggering.
ros2 topic echo /bdd/status
# Terminal 5: optional viewer at http://127.0.0.1:8080.
ros2 run bdd_exec_ros2 web_visualizer --ros-args -p use_sim_time:=true
# Terminal 6: trigger one test.
ros2 topic pub --once /bdd/start std_msgs/msg/Empty '{}'
```

- `/bdd/start` loads/resets the positive-case scene again and triggers physical
  motion after setup/readiness. The scene separates the cube from clutter with
  sampled poses; collisions and unreachable targets are still possible.
- Expect a successful Behaviour result and `TRUE` for at-pick, held, and at-place.
  Inspect `/bdd/status` or the viewer for individual verdicts and failure reasons.
- Resetting time can stall ros2_control until its pre-reset time catches up;
  see [ros2_control #3697](https://github.com/ros-controls/ros2_control/issues/3697).
  A larger readiness timeout allows more recovery time but cannot fix the stall.
- Keep the simulation playing. Readiness and simulation-observation timeouts use
  simulation time. A clock reset after scenario start fails the run; restart the coordinator.

See the [Isaac integration guide](https://minhnh.github.io/bdd-dsl/at-tutorial-execution-isaac.html)
for agent bindings, sampled scenes, observation policies, and event timing.

### Standalone Isaac debugging

Use the standalone server to inspect collision geometry or isolate motion failures
without running BDD evaluation. Stop the observation launch first; both expose `/bdd/prepare`.
Load a scene and start MoveIt using the sequence above before starting this server.

```sh
# Default: temporarily remove the selected collision object, then restore it.
ros2 launch robbdd_tutorials isaac_prepare.launch.yaml
# Another sourced terminal: trigger the selected tree.
ros2 action send_goal /bdd/prepare bdd_ros2_interfaces/action/Behaviour \
  "$(cat "$(ros2 pkg prefix --share robbdd_tutorials)/config/isaac_prepare_goal.yaml")" --feedback
```

Select a different tree by replacing the server launch with:

```sh
ros2 launch robbdd_tutorials isaac_prepare.launch.yaml \
  tree_xml:="$(ros2 pkg prefix --share robbdd_tutorials)/behavior_trees/isaac_plan_approach.xml"
```

| Tree | Check |
| --- | --- |
| [isaac_prepare.xml](behavior_trees/isaac_prepare.xml) | Inspect the collision scene; remove the selected object for 10 seconds and restore it, without arm motion. |
| [isaac_plan_approach.xml](behavior_trees/isaac_plan_approach.xml) | Plan to pre-pick without execution. |
| [isaac_pick_place.xml](behavior_trees/isaac_pick_place.xml) | Execute physical cube pick/place; a successful action alone does not establish BDD acceptance. |

- Compare collision geometry in RViz with Isaac when planning fails.
- Feedback identifies missing action servers, joint states, or TF.
- For reset-related stalls, load the scene and restart MoveIt before sending a
  standalone goal; avoid another scene reset underneath MoveIt.

## Configuration

These files select the models, geometry, controllers, and coordinator settings.
Use `ros2 launch robbdd_tutorials <launch-file> --show-args` for all launch arguments.

| File | Contents |
| --- | --- |
| [config/pick_place.yaml](config/pick_place.yaml) | MuJoCo coordinator and wall-clock settings. |
| [config/isaac_pick_place.yaml](config/isaac_pick_place.yaml) | BT entity URI -> prim path mappings, collision shapes/offsets, and Behaviour variable bindings. |
| [config/isaac_prepare_goal.yaml](config/isaac_prepare_goal.yaml) | Standalone goal with object, destination, and robot parameters. |
| [config/isaac_arm_controller.yaml](config/isaac_arm_controller.yaml) | Joint tolerances and settling allowance. |
| [config/isaac_observations.yaml](config/isaac_observations.yaml) | Isaac coordinator, endpoints, and simulation timing. |
| [pick_place_positive.scenex](models/pick_place/isaacsim/pick_place_positive.scenex) | Default acceptance scene with separate sampled cube/clutter regions. |
| [pick_place_single.scenex](models/pick_place/isaacsim/pick_place_single.scenex) | Alternative scene with shared-region sampling; load manually for standalone tests. |
| [Isaac models](models/pick_place/isaacsim) / [MuJoCo models](models/pick_place/mujoco_motion_spec) | Backend stories, SceneX/BDDX bindings, and graph manifests. |

Main launch arguments:

- MoveIt: `start_rviz=false`, `robot_base_yaw`, `use_sim_time`, `arm_controller_config`.
- BT: `tree_xml`, `config_file`, `group=panda_arm`, `urdf`, `srdf`,
  `move_group_action`, `gripper_action`, `touch_links`, and frame/service endpoints.
- Clearances: `pick_clearance="0;0;0.1"`, `place_clearance="0;0;0.2"` m.
- Readiness: `readiness_timeout=30.0`, `readiness_max_age=1.0` simulation seconds.
- Observations: `config`, `graph_models`, and arguments inherited from the BT launch.

## Offline checks

The package checks shipped tree/config wiring and model bindings. Generic node
behavior is tested in the executor package. The Isaac checks require a build
configured with `ROBBDD_BUILD_ISAAC_BT=ON`, as selected by `isaacsim-bt` setup.

```sh
colcon test --packages-select robbdd_tutorials \
  --ctest-args -R 'test_isaac_(bt|observations)' --return-code-on-test-failure
python3 src/robbdd_tutorials/scripts/test_setup.py
```
