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
- A BehaviorTree.CPP and Isaac Sim setup is planned but not runnable yet.

The published
[tutorials for automated Testing with RobBDD](https://minhnh.github.io/bdd-dsl/at-tutorial-scenarios.html)
contains the requirements and walks through the common models.

## Create the workspace

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
- **Isaac Sim only:** Isaac Sim, installed separately. Setup builds matching [Isaac Sim ROS workspace](https://github.com/isaac-sim/IsaacSim-ros_workspaces)
  but does not install the simulator.

Setup offers to install common system prerequisites and adds Ant only for MuJoCo.
It prints the exact `sudo apt install` command and asks before running it.
Declining leaves the prerequisite checks enabled. Noninteractive setup skips the
prompt; use `--install-system-packages` to opt in explicitly. `--build` never
installs system packages or prompts.

To install prerequisites manually after configuring the ROS apt repository:

```bash
sudo apt install git git-lfs build-essential cmake python3-vcs2l \
  python3-colcon-common-extensions python3-rosdep python3-venv
sudo apt install ant  # MuJoCo only
sudo rosdep init      # once per machine; skip if already initialized
```

Setup uses `rosdep` for the selected packages’ ROS dependencies afterward;
`rosdep install` may also request sudo authentication.

Then clone this repository as a ROS package under `src` and run its setup script:

```bash
mkdir -p ~/ros_bdd_ws/src
git clone https://github.com/minhnh/robbdd_tutorials.git \
  ~/ros_bdd_ws/src/robbdd_tutorials
cd ~/ros_bdd_ws/src/robbdd_tutorials
./scripts/setup mujoco jazzy
```

The setup uses `vcs2l` to clone repositories in `repos/*.repos` files.
There are separate files for [common repositories](./repos/common.repos),
execution setup with [`motion-spec` - MuJoCo](./repos/mujoco.repos),
and with [`BehaviorTree.CPP` - Isaac Sim](./repos/isaacsim-bt.repos).
This clones editable Python sources under `~/ros_bdd_ws/pydeps` and ROS packages
under `~/ros_bdd_ws/src`.

The setup script also creates a Python virtual environment `~/ros_bdd_ws/.venv`
for installing Python dependencies.
The setup manifest clones STST and the compiled motion dependencies under
`~/ros_bdd_ws/src`; `motion-spec setup` builds them into `~/ros_bdd_ws/install`.

For the Isaac context:

```bash
./scripts/setup isaacsim-bt jazzy 6.1.0
```

This clones NVIDIA’s pinned `IsaacSim-6.1.0` repository beside the tutorial
workspace, into `../IsaacSim-ros_workspaces`, and builds the MoveIt dependency
closure in its `jazzy_ws`. The generated environment sources this underlay before
the tutorial workspace. Override the selected ROS workspace with
`ROBBDD_ISAAC_ROS_WS=/absolute/path/IsaacSim-ros_workspaces/jazzy_ws`.
Existing checkouts must be clean and already at the selected version; setup does
not switch or overwrite them. Only the selected distribution’s MoveIt resource
and topic-based control submodules are initialized.

`bdd_tutorial build` preserves the context, version, and underlay location.
`bdd_tutorial pull` fetches NVIDIA updates without changing its pinned version.
To change versions, select an appropriate clean checkout and rerun setup with
that version. The Isaac pick/place behavior is still under development; setup
alone does not make it runnable.

Source the generated file matching the current shell:

```bash
source ~/ros_bdd_ws/setup-robbdd-tutorials.bash   # bash
# source ~/ros_bdd_ws/setup-robbdd-tutorials.zsh  # zsh
```

The sourced environment loads `colcon_cd` and aliases it as `roscd`, so
`roscd robbdd_tutorials` jumps to this package. It also provides two maintenance commands:

```bash
bdd_tutorial pull   # update tutorial dependencies; fetch the NVIDIA checkout
bdd_tutorial build  # reinstall local Python packages and rebuild
```

## Test Execution

### 1. `motion-spec` in MuJoCo

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

The motion-spec process owns the simulator and waits for a
`bdd_ros2_interfaces/action/Behaviour` goal. The YAML launch starts only the
BDD coordinator. The model provides the behavior action server, BDD boundary events, and
direct scene-pose observations used by the coordinator.

Before introducing sampled placements, the MuJoCo nominal run produced a complete
verdict but reported `object-at-place` as false: the released cube remained about
0.47 m from the bin observation point. Placement behavior still needs validation
after the execution blockers above are resolved.

### 2. `BehaviorTree.CPP` in Isaac Sim

TODO(minhnh)
