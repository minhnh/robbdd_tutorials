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
ISAAC_VERSION=6.1.0
./scripts/setup isaacsim-bt "$ROS_DIST" "$ISAAC_VERSION"
```

Source the generated file matching the current shell:

```sh
source ~/ros_bdd_ws/setup-robbdd-tutorials.bash   # bash
# source ~/ros_bdd_ws/setup-robbdd-tutorials.zsh  # zsh
```

The sourced environment loads `colcon_cd` and aliases it as `roscd`, so
`roscd robbdd_tutorials` jumps to this package. It also provides two maintenance commands:

```sh
bdd_tutorial pull   # update tutorial dependencies; fetch the NVIDIA checkout
bdd_tutorial build  # reinstall local Python packages and rebuild
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

- Uses `rosdep` for the selected packages’ ROS dependencies afterward;
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
- `bdd_tutorial build` reinstalls the editable Python projects and repeats the
  motion-spec and colcon builds, without cloning repositories or installing system packages.

#### `BehaviorTree.CPP` & MoveIt in Isaac Sim

- Uses the `ISAAC_VERSION` passed in the sample command to select NVIDIA's
  `IsaacSim-${ISAAC_VERSION}` tag, cloning the repository beside the tutorial workspace,
  into `../IsaacSim-ros_workspaces`.
- Builds the MoveIt dependency closure in `${ROS_DIST}_ws` (`jazzy_ws` in the example);
  the generated environment
  sources this underlay before the tutorial workspace.
- Override the selected ROS workspace with
  `ROBBDD_ISAAC_ROS_WS=/absolute/path/IsaacSim-ros_workspaces/${ROS_DIST}_ws`.
- Existing checkouts must be clean and already at the selected version. Setup
  does not switch or overwrite them.
- Initializes only the selected distribution's MoveIt resource and topic-based
  control submodules.
- `bdd_tutorial build` preserves the context, version, and underlay location.
- `bdd_tutorial pull` fetches NVIDIA updates without changing the pinned version.

## Test Execution

### With `motion-spec` in MuJoCo

1. Start test web visualization:
   ```sh
   ros2 run bdd_exec_ros2 web_visualizer
   ```
2. Start MuJoCo pick-place behaviour:
   ```sh
   # optional: skip GUI with --headless
   motion-spec run "$(ros2 pkg prefix --share robbdd_tutorials)/models/pick_place/mujoco_motion_spec/pick_place_single.robmot"
   ```
3. Launch test coordinator:
   ```sh
   ros2 launch robbdd_tutorials pick_place_coordinator.launch.yaml
   ```
4. Trigger test start:
   ```sh
   ros2 topic pub --once /bdd/start std_msgs/msg/Empty '{}'
   ```

Execution and validation:

- The motion-spec process owns the simulator and waits for a
  `bdd_ros2_interfaces/action/Behaviour` goal.
- The YAML launch starts the BDD coordinator.
- The model provides the Behaviour action server, BDD boundary events, and direct
  scene-pose observations used by the coordinator.

### With MoveIt and `BehaviorTree.CPP` in Isaac Sim

TODO(minhnh)
