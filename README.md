# RobBDD tutorials

Models and runtime setups for robot acceptance tests with RobBDD and BDDX.
See the [RobBDD tutorials](https://minhnh.github.io/bdd-dsl/at-tutorial-scenarios.html)
for the specification walkthrough and the executor's
[BT node reference](https://github.com/minhnh/bdd_bt_executor_ros2/blob/main/docs/bt_nodes.md)
for reusable node APIs.

## Setup

Clone this package under a ROS workspace's `src` directory, then select one context:

```sh
mkdir -p ~/ros_bdd_ws/src
git clone https://github.com/minhnh/robbdd_tutorials.git ~/ros_bdd_ws/src/robbdd_tutorials
cd ~/ros_bdd_ws/src/robbdd_tutorials
./scripts/setup mujoco jazzy
# Or: ./scripts/setup isaacsim-bt jazzy
source ~/ros_bdd_ws/setup-robbdd-tutorials.bash  # .zsh for zsh
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
- The fork's `fix/jazzy-asyncio-sleep` branch fixes the gripper callback error in
  [Isaac workspace issue #27](https://github.com/isaac-sim/IsaacSim-ros_workspaces/issues/27).
  Initial setup requires a clean checkout; rebuilds allow local edits.
- Setup/build pulls the Panda world USD through Git LFS and sources the Isaac
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
The observation launch reuses the standalone server rather than duplicating its setup.

## MuJoCo execution

The motion-spec runtime performs pick/place; the coordinator evaluates the common
BDD contract. Use the same unused `ROS_DOMAIN_ID` in every terminal if another
simulation or BDD runtime is running.

```sh
# Terminal 1: wait for S_WAIT; add --headless to omit the GUI.
motion-spec run "$(ros2 pkg prefix --share robbdd_tutorials)/models/pick_place/mujoco_motion_spec/pick_place_single.robmot" --rtf 1
# Terminal 2:
ros2 launch robbdd_tutorials pick_place_coordinator.launch.yaml
# Terminal 3: optional result viewer.
ros2 run bdd_exec_ros2 web_visualizer
# Trigger one test:
ros2 topic pub --once /bdd/start std_msgs/msg/Empty '{}'
```

Expect the behavior and all three policies (at-pick, not-dropped, at-place) to
finish with `TRUE`. Keep `--rtf 1` to match the coordinator's wall clock.

## Isaac setup and execution

Keep Isaac playing. Load the scene before starting MoveIt to avoid a backward
clock reset underneath the controllers.

```sh
bdd_ws build
source setup-robbdd-tutorials.bash  # .zsh for zsh; run from the workspace root
export TUTORIAL_SHARE="$(ros2 pkg prefix --share robbdd_tutorials)"
ros2 run bdd_exec_ros2 sim_interface_test load-scene \
  --scene-model "$TUTORIAL_SHARE/models/pick_place/isaacsim/pick_place_single.scenex"
```

Start MoveIt in another sourced terminal. RViz defaults to off; this launch also
sets the supplied world's Panda base transform and controller tolerances.

```sh
LC_NUMERIC=en_US.UTF-8 ros2 launch robbdd_tutorials isaac_moveit.launch.xml start_rviz:=true
```

Start the BT server, choosing a tree from the list below. With no `tree_xml`
override it inspects the collision scene without moving the robot.

```sh
ros2 launch robbdd_tutorials isaac_prepare.launch.yaml
```

To execute pick/place, replace that server launch with:

```sh
ros2 launch robbdd_tutorials isaac_prepare.launch.yaml \
  tree_xml:="$(ros2 pkg prefix --share robbdd_tutorials)/behavior_trees/isaac_pick_place.xml"
```

Trigger the selected tree from another sourced terminal:

```sh
ros2 action send_goal /bdd/prepare bdd_ros2_interfaces/action/Behaviour \
  "$(cat "$(ros2 pkg prefix --share robbdd_tutorials)/config/isaac_prepare_goal.yaml")" --feedback
```

### Behavior trees

All three trees share preparation: resolve goal bindings, wait for fresh robot
state, query Isaac poses, compute offset targets, and apply the collision scene.

| `behavior_trees/` file | Behavior |
| --- | --- |
| [isaac_prepare.xml](behavior_trees/isaac_prepare.xml) | Remove the selected collision object for 10 seconds, then restore it; no physical motion. Also defines the shared `Prepare` subtree. |
| [isaac_plan_approach.xml](behavior_trees/isaac_plan_approach.xml) | Plan to pre-pick with `plan_only=true`; no physical motion. Select with `tree_xml` as above. |
| [isaac_pick_place.xml](behavior_trees/isaac_pick_place.xml) | Open -> pre-pick -> pick -> close/attach -> post-pick lift -> pre-place -> place -> open/detach -> post-place retreat. |

A complete physical cube pick/place has succeeded. Sampled scenes can still cause
collisions or unreachable targets; full BDD boundary-event wiring remains pending.

### Configuration

| File | Contents |
| --- | --- |
| [config/isaac_pick_place.yaml](config/isaac_pick_place.yaml) | Entity URI -> prim path mappings, collision geometry/offsets, and Behaviour variable bindings. |
| [config/isaac_prepare_goal.yaml](config/isaac_prepare_goal.yaml) | Sample object, destination, and robot parameters for `/bdd/prepare`. |
| [config/isaac_arm_controller.yaml](config/isaac_arm_controller.yaml) | Joint goal tolerances (0.02 rad), stopped velocity (0.01 rad/s), and settling allowance (2 s). |
| [config/isaac_observations.yaml](config/isaac_observations.yaml) | Isaac coordinator settings, action endpoint, and simulation timing. |
| [models/pick_place/isaacsim/pick_place_single.scenex](models/pick_place/isaacsim/pick_place_single.scenex) | Assets and sampled object poses; cube/box start upright, can/bottle also sample orientation. |
| [models/pick_place/isaacsim/pick_place.bdd](models/pick_place/isaacsim/pick_place.bdd) | Isaac scenario and Panda/object/workspace bindings for the shared contract. |
| [models/pick_place/isaacsim/pick_place.bddx](models/pick_place/isaacsim/pick_place.bddx) | Simulation-pose and Panda-hand TF observation providers and evaluators. |
| [models/pick_place/isaacsim/graph-models.yaml](models/pick_place/isaacsim/graph-models.yaml) | Models loaded by the Isaac coordinator. |

Main launch arguments:

- MoveIt: `start_rviz=false`, `robot_base_yaw`, `use_sim_time`, `arm_controller_config`.
- BT: `tree_xml`, `config_file`, `group=panda_arm`, `urdf`, `srdf`,
  `move_group_action`, `gripper_action`, `touch_links`, and frame/service endpoints.
- Offsets: `pick_clearance="0;0;0.1"`, `place_clearance="0;0;0.2"` m in the reference
  frame; pre/post poses share the corresponding offset. Tool/release offsets are in XML.
- Readiness: `readiness_timeout=30.0`, `readiness_max_age=1.0` simulation seconds.
- Observations: `config`, `graph_models`, and arguments inherited from the BT launch.

### Observation debugging

This launch checks observation wiring with the preparation tree; it does not yet
provide full physical pick/place acceptance. Stop the standalone BT server first.

```sh
ros2 launch robbdd_tutorials isaac_observations.launch.yaml readiness_timeout:=120.0
# Another sourced terminal:
ros2 topic pub --once /bdd/start std_msgs/msg/Empty '{}'
```

- `/bdd/start` resets the scene. This can stall ros2_control until its pre-reset
  time catches up; see [ros2_control #3697](https://github.com/ros-controls/ros2_control/issues/3697).
  Readiness detects recovery but cannot accelerate it. For standalone debugging,
  load the scene first, then restart MoveIt without another reset.
- Feedback identifies missing action servers, joint states, or TF. Readiness and
  simulation-observation timeouts pause when simulation time is paused.
- Inspect geometry in RViz against Isaac. The current service labels world poses
  with entity frames, so the tree uses `override_frame_id="world"`.
- Independent samples can overlap. Collision failures need geometry/grasp/scene
  inspection; successful planning or attachment alone does not prove a physical grasp.

## Offline checks

The tutorial checks shipped tree/config wiring and model bindings. Generic BT
node behavior is tested in the executor package.

```sh
colcon test --packages-select robbdd_tutorials \
  --ctest-args -R 'test_isaac_(bt|observations)' --return-code-on-test-failure
python3 src/robbdd_tutorials/scripts/test_setup.py
```
