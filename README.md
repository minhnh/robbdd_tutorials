# RobBDD tutorials

Executable tutorials for specifying and evaluating robot acceptance tests with
RobBDD and BDDX.

The repository separates the shared acceptance-test contract from each system
under test:

- `models/pick_place/common` contains the BDD, Scene, and
  specification-only sorting extension shared by every
  implementation.
- `models/pick_place/mujoco_motion_spec` contains the first
  execution setup, including its BDDX, using motion-spec and MuJoCo.
- `bdd_bt_executor_ros2` provides a BehaviorTree.CPP/MoveIt smoke test
  in Isaac Sim; the full pick/place tutorial is still under development.

The published
[tutorials for automated Testing with RobBDD](https://minhnh.github.io/bdd-dsl/at-tutorial-scenarios.html)
contain the requirements and walks through the common models.

## Contents

<!-- mtoc-start -->

1. [Setting up the workspace](#setting-up-the-workspace)
    1. [Quick Start](#quick-start)
    1. [Dependencies](#dependencies)
    1. [Setup script](#setup-script)
        1. [`motion-spec` in MuJoCo](#motion-spec-in-mujoco)
        1. [`BehaviorTree.CPP` & MoveIt in Isaac Sim](#behaviortreecpp--moveit-in-isaac-sim)
1. [Test Execution](#test-execution)
    1. [With `motion-spec` in MuJoCo](#with-motion-spec-in-mujoco)
    1. [With MoveIt and `BehaviorTree.CPP` in Isaac Sim](#with-moveit-and-behaviortreecpp-in-isaac-sim)
    1. [Isaac acceptance observations](#isaac-acceptance-observations)

<!-- mtoc-end -->

## Setting up the workspace

### Quick Start

Clone this repository as a ROS package under `src` and run its setup script:

```sh
mkdir -p ~/ros_bdd_ws/src
git clone https://github.com/minhnh/robbdd_tutorials.git \
  ~/ros_bdd_ws/src/robbdd_tutorials
cd ~/ros_bdd_ws/src/robbdd_tutorials
export ROS_DIST=jazzy
```

For execution in MuJoCo with `motion-spec`:

```sh
./scripts/setup mujoco "$ROS_DIST"
```

For execution in Isaac Sim with MoveIt and `BehaviorTree.CPP`:

```sh
./scripts/setup isaacsim-bt "$ROS_DIST"
```

Source the generated file matching the current shell:

```sh
source ~/ros_bdd_ws/setup-robbdd-tutorials.bash   # bash
# source ~/ros_bdd_ws/setup-robbdd-tutorials.zsh  # zsh
```

The sourced environment loads `colcon_cd` and aliases it as `roscd`, so
`roscd robbdd_tutorials` jumps to this package. It also provides two maintenance commands:

```sh
bdd_ws pull   # update tutorial dependencies; fetch the NVIDIA checkout
bdd_ws build  # reinstall local Python packages and rebuild
```

### Dependencies

Common dependencies:

- **Required:** [ROS 2 Jazzy on Ubuntu 24.04](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html),
  with its apt repository configured before setup.
- **Required:** Git to clone repositories and Git LFS to fetch binary resources.
- **Required:** [vcs2l](https://github.com/ros-infrastructure/vcs2l) (`python3-vcs2l`)
  for managing repositories in `repos/*.repos` files.
- **Required:** `python3-colcon-common-extensions` to build ROS packages and provide `colcon_cd`.
- **Required:** `python3-rosdep` to install ROS package dependencies; initialize it once with `sudo rosdep init`.
- **Required:** `build-essential`, CMake, and `python3-venv` for compilation and the Python environment.
- **Optional:** [uv](https://docs.astral.sh/uv/) for Python package installation. Setup uses it when available, otherwise pip.

Execution-context dependencies:

- **MuJoCo only:** [Ant](https://ant.apache.org/) for the `motion-spec` setup.
- **Isaac Sim only:** Isaac Sim, installed separately. Setup builds matching
  [Isaac Sim ROS workspace](https://github.com/isaac-sim/IsaacSim-ros_workspaces)
  but does not install the simulator.

### Setup script

- Setup offers to install common prerequisites, adding Ant only for MuJoCo.
- It prints the exact `sudo apt install` command and asks before running it.
- Declining leaves prerequisite checks enabled.
- Noninteractive setup skips the prompt; use `--install-system-packages` to opt in.
- `--build` never installs system packages or prompts.

To install prerequisites manually after configuring the ROS apt repository:

```sh
sudo apt install git git-lfs build-essential cmake python3-vcs2l \
  python3-colcon-common-extensions python3-rosdep python3-venv
sudo apt install ant  # MuJoCo only
sudo rosdep init      # once per machine; skip if already initialized
```

The setup script:

- Uses `rosdep` for the selected packages' ROS dependencies afterward;
  `rosdep install` may also request sudo authentication.
- Uses `vcs2l` to clone repositories in `repos/*.repos` files.
  There are separate files for [common repositories](./repos/common.repos),
  execution setup with [`motion-spec` - MuJoCo](./repos/mujoco.repos),
  and with [`BehaviorTree.CPP` - Isaac Sim](./repos/isaacsim-bt.repos).
  This clones editable Python sources under `~/ros_bdd_ws/pydeps` and ROS packages
  under `~/ros_bdd_ws/src`.
- Creates `~/ros_bdd_ws/.venv` with access to system Python packages, including ROS.
- Installs common Python requirements and local projects in editable mode,
  using uv when available and pip otherwise.
- Writes `setup-robbdd-tutorials.bash` and `setup-robbdd-tutorials.zsh` after the build.

#### `motion-spec` in MuJoCo

- Imports [the MuJoCo manifest](./repos/mujoco.repos) alongside the common repositories.
- Clones `rec`, `motion-spec-dsl`, and `motion-spec` into `~/ros_bdd_ws/pydeps`
  and installs them in editable mode in the workspace virtual environment.
- Clones STSTv4, `orocos_kinematics_dynamics`, `coord2b`, and `mj_kdl_wrapper`
  under `~/ros_bdd_ws/src`.
- Invokes the motion-spec setup to build the compiled motion dependencies into
  `~/ros_bdd_ws/install`, with ROS support:
  ```sh
  motion-spec setup STSTv4 orocos_kinematics_dynamics coord2b mj_kdl_wrapper \
    --workspace ~/ros_bdd_ws --ros
  ```
- Sources the resulting install environment, then runs `colcon build` for the workspace.
- The generated environment activates the virtual environment, sources ROS and
  the workspace install, and configures motion-spec's workspace, generated-output,
  and install paths. Source it before running the commands in [Test Execution](#test-execution).
- `bdd_ws build` reinstalls the editable Python projects and repeats the
  motion-spec and colcon builds, without cloning repositories or installing system packages.

#### `BehaviorTree.CPP` & MoveIt in Isaac Sim

- Clones [the temporary Isaac workspace fork](https://github.com/minhnh/IsaacSim-ros_workspaces)
  beside the tutorial workspace, into `../IsaacSim-ros_workspaces`.
- Always uses the fork's `fix/jazzy-asyncio-sleep` branch; setup currently has no
  Isaac Sim version argument or tag selection.
- The branch fixes the gripper callback's `no running event loop` error reported
  in [upstream issue #27](https://github.com/isaac-sim/IsaacSim-ros_workspaces/issues/27).
  The fix uses a ROS timer/future so joint-command publishing continues during the wait.
- Builds the MoveIt dependency closure in `${ROS_DIST}_ws` (`jazzy_ws` in the example);
  the generated environment
  sources this underlay before the tutorial workspace.
- Override the selected ROS workspace with
  `ROBBDD_ISAAC_ROS_WS=/absolute/path/IsaacSim-ros_workspaces/${ROS_DIST}_ws`.
- Initial setup requires a clean checkout on `fix/jazzy-asyncio-sleep`.
  Setup does not switch or overwrite it.
- `--build` allows local edits on that branch, so the rebuild uses your current sources.
- Initializes only the selected distribution's MoveIt resource and topic-based
  control submodules.
- Setup and `bdd_ws build` explicitly pull the Panda world USD through Git LFS
  before installing `bdd_exec_ros2`, so the simulator receives the asset rather
  than an LFS text pointer.
- `bdd_ws build` preserves the context and underlay location.
- `bdd_ws pull` fetches the fork without switching or advancing the fix
  branch; update the checkout explicitly when adopting newer fixes.

## Test Execution

### With `motion-spec` in MuJoCo

Source the workspace environment in every terminal. If Isaac or another BDD
runtime is running, also set the same unused `ROS_DOMAIN_ID` in every terminal
(for example, `export ROS_DOMAIN_ID=138`).

1. Start the MuJoCo behavior:
   ```sh
   motion-spec run "$(ros2 pkg prefix --share robbdd_tutorials)/models/pick_place/mujoco_motion_spec/pick_place_single.robmot" --rtf 1
   ```
   Include `--headless` for skipping the GUI. `--rtf 1` keeps simulation paced to wall time,
   matching the coordinator's clock. Wait for the `S_WAIT` state before triggering.
2. Start the coordinator in another terminal:
   ```sh
   ros2 launch robbdd_tutorials pick_place_coordinator.launch.yaml
   ```
3. Starts the web visualizer in another terminal to monitor test results in the browser:
   ```sh
   ros2 run bdd_exec_ros2 web_visualizer
   ```
4. Start one test:
   ```sh
   ros2 topic pub --once /bdd/start std_msgs/msg/Empty '{}'
   ```

Expected results:

- The arm grasps, transfers, releases, and retreats; the behavior finishes with `TRUE`.
- The web visualizer should report `TRUE` for the scenario and each of
  its three policies: at-pick, not-dropped, and at-place.

### With MoveIt and `BehaviorTree.CPP` in Isaac Sim

The tutorial currently validates scene preparation and URI-based pose selection.
Full pick/place execution is still under development. It uses the standard
`bdd_bt_executor_ros2` server; the only tutorial C++ is one tree-wiring test.

- [config/isaac_pick_place.yaml](config/isaac_pick_place.yaml): simulator IDs,
  collision geometry, and variable-to-role bindings.
- [launch/isaac_prepare.launch.yaml](launch/isaac_prepare.launch.yaml): frames,
  service endpoints, timeout, and the expected Panda URI, supplied as `tree_inputs`.
- [behavior_trees/isaac_prepare.xml](behavior_trees/isaac_prepare.xml): resolves
  the goal, collects poses, computes offset targets, and applies the collision scene.
  Its default `InspectResolvedObject` tree removes the selected collision object
  for 10 seconds, reports its URI in feedback, then restores the scene.
- Generic node APIs are documented in the executor's
  [BT node reference](https://github.com/minhnh/bdd_bt_executor_ros2/blob/main/docs/bt_nodes.md).

The SceneX model uses one Panda agent for arm and gripper, the table from the
Panda world, and a spawned KLT bin. It includes all four pickable objects:

| Object | Isaac asset | Prim path |
| --- | --- | --- |
| Cube | Dex cube | `/spawned/cube` |
| Can | YCB tomato soup can | `/spawned/can` |
| Cereal box | YCB cracker box | `/spawned/cereal_box` |
| Bottle | YCB mustard bottle | `/spawned/bottle` |

MuJoCo uses robosuite's Hy-Vee cereal box; its semantic identity matches the Isaac
cracker box, but meshes and dimensions differ. Preparation includes all six
catalogue entities as obstacles; the robot uses MoveIt's robot model.

Offline checks, after sourcing the workspace:

```sh
bdd_ws build
colcon test --packages-select robbdd_tutorials --ctest-args -R "test_isaac_(bt|observations)" --return-code-on-test-failure
python3 src/robbdd_tutorials/scripts/test_setup.py
```

The C++ smoke test checks the shipped tree's URI -> pose -> offset -> scene-update
wiring. Generic node behavior is tested in the executor. The `.clang-format` and
pre-commit hook remain for this test.

To validate against live Isaac Sim, source the workspace in every terminal:

1. Build and load the scene with the ROS bridge and simulation interfaces enabled:
   ```sh
   bdd_ws build
   source setup-robbdd-tutorials.bash  # use .zsh for zsh
   TUTORIAL_SHARE="$(ros2 pkg prefix --share robbdd_tutorials)"
   ros2 run bdd_exec_ros2 sim_interface_test load-scene \
     --scene-model "$TUTORIAL_SHARE/models/pick_place/isaacsim/pick_place_single.scenex"
   ```
   The build pulls the Panda world through Git LFS. Loading resets the world and
   spawns the configured objects; keep simulation playing afterward.
2. Start MoveIt in another terminal, with RViz for visual inspection:
   ```sh
   LC_NUMERIC=en_US.UTF-8 ros2 launch robbdd_tutorials isaac_moveit.launch.xml start_rviz:=true
   ```
   RViz otherwise defaults to off. This launch matches the supplied Panda base at
   `(0, -0.64, 0)` m with +90-degree yaw (`robot_base_yaw` is configurable).
   Stop any previous MoveIt launch first to avoid duplicate controllers and TF publishers.
3. Start the preparation server:
   ```sh
   ros2 launch robbdd_tutorials isaac_prepare.launch.yaml
   ```
   Override `config_file` for different prim paths/geometry. Frames, service
   endpoints, and `timeout` are launch arguments; list them with `--show-args`.
4. Send the sample goal from another terminal:
   ```sh
   ros2 action send_goal /bdd/prepare bdd_ros2_interfaces/action/Behaviour \
     "$(cat "$(ros2 pkg prefix --share robbdd_tutorials)/config/isaac_prepare_goal.yaml")" \
     --feedback
   ```
   Expect `SUCCEEDED` and `TRUE`. In RViz, only the resolved object should disappear
   during the 10-second pause and return afterward. To test the bottle, change only
   the target object's `param_val_uris` to its catalogue URI; keep `variable_uri` unchanged.

Validation limits and calibration:

- Loading or resetting the scene can move `/clock` backward and stall the
  ros2_control loop until simulation time catches up. Controllers may still report
  active while arm joint states and TF stop updating; see
  [ros2_control issue #3697](https://github.com/ros-controls/ros2_control/issues/3697)
  for the Isaac/Gazebo reproduction. Workaround: load the scene first, then restart
  MoveIt before running preparation. A fixed delay is unreliable because the wait
  depends on the simulation time before reset.
- The default tree makes no arm/gripper requests and leaves Isaac objects in place.
  If interrupted after removal, submit the goal again to rebuild the collision scene.
  Restoration uses the poses captured at the start.
- The tree uses `override_frame_id="world"` because the tested Isaac service returns
  world coordinates labelled with entity names. Confirm that convention for your
  scene; otherwise preserve the headers and provide TF to `target_frame`.
  Stamp zero requests the latest TF and does not establish pose freshness.
- Check collision sizes and entity-local shape offsets against RViz. The table
  geometry uses a measured tabletop height of 0.7696 m above the legs origin.
- XML offsets retain the nominal cube grasp: absolute quaternion `[1,0,0,0]`,
  local tool offset `[0,0,-0.1]` m, 0.1 m reference-frame Z clearance, and 0.08 m
  bin-local release height. Other objects need grasp calibration before motion.
- For a calibrated target, the executor plans and executes through MoveIt:
  ```xml
  <MoveGroupAction group="panda_arm" target_pose="{approach_pose}" link_name="panda_hand"/>
  ```
  Pose targets use MoveIt's current collision scene. They do not require an SRDF
  on the executor; named targets do. Attachment/detachment update MoveIt's collision
  model, not the physical simulator grasp.

### Isaac acceptance observations

The observation launch runs the preparation tree and coordinator together. Stop
an existing preparation server before starting it; keep Isaac Sim playing and
MoveIt running as above.

This launch loads/resets the scene on `/bdd/start`, then starts BDD observations
and the preparation Behaviour. Its first steps resolve the goal and wait for
MoveIt readiness. `WaitForMoveItReady` requires
fresh Panda arm joint states, `world -> panda_hand` TF, and `/move_action`.

```sh
ros2 launch robbdd_tutorials isaac_observations.launch.yaml readiness_timeout:=30.0
# In another sourced terminal: resets/loads the scene, waits, then prepares it.
ros2 topic pub --once /bdd/start std_msgs/msg/Empty '{}'
```

- `readiness_timeout` defaults to 30 simulation seconds; `readiness_max_age` to 1.
  Action/topic, arm `group`, and frames are launch arguments (`--show-args`).
  Joints come from the `urdf` and `srdf` files; `srdf` defaults to the same file
  as the executor named-target example.
- Behaviour feedback reports the missing readiness requirement. A timeout fails
  the tree and aborts the Behaviour goal with `FALSE`, skipping scene preparation.
  The BDD scenario timing includes this wait. Pausing simulation pauses the timeout.
- Due to [ros2_control #3697](https://github.com/ros-controls/ros2_control/issues/3697),
  a reset can stall arm publication until the old simulation-time deadline.
  Readiness detects recovery; it does not accelerate it. For a single variation,
  restart Isaac and MoveIt and trigger soon after startup so the pre-reset clock
  is small enough for the configured wait. Restart before another test if needed.
- The application owning MoveIt can instead restart it after scene setup. The
  readiness node never starts or kills processes. For manual validation without
  another time reset, use the scene-loading and preparation flow above.

- `models/pick_place/isaacsim/pick_place.bdd` binds the common pick/place contract
  to one Panda agent and the cube/table/bin roles. The shared scene contains no
  invariant agents. `mujoco_agents` declares Kinova and Robotiq, while
  `panda_agents` declares Panda. The robot binding selects Kinova or Panda;
  sorting excludes the separately controlled Robotiq gripper.
- `pick_place.bddx` and `graph-models.yaml` configure the acceptance observations.
  `config/isaac_observations.yaml` selects only the Isaac user story.
- Cube and bin observations preserve full simulation poses. Panda grasp position
  comes from `world -> panda_hand` TF. The pick workspace uses the fixed `world`
  origin at the tabletop, rather than the table's legs-origin pose.
- The cube starts upright at `(0.1, -0.1, 0.1)` m. Other sampled objects can still
  overlap and need inspection before physical motion.
- The Isaac containment evaluator uses bin half-extents `(0.178, 0.277)` m and
  a 0.025 m inset for the upright cube. MuJoCo calibration is unchanged.
- Service timeouts, observation polling, and TF freshness follow the node clock.
  With simulation time enabled, pausing simulation also pauses service timeouts. Zero source stamps
  use receipt time for evaluation; they do not prove source freshness.
- This diagnostic sends no physical motion or pick/place boundary events.
  Overall BDD acceptance remains incomplete until the physical sequence is wired.
  Grasp/lift/release calibration and live attachment/detachment remain to validate.

The observation smoke test loads the shipped models and checks the Panda binding.
Live provider validation also checked
full cube/bin poses, Panda-hand TF, and a timestamp-aligned pre-pick condition.
