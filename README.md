# RobBDD tutorials

Executable tutorials for specifying and evaluating robot acceptance tests with
RobBDD and BDDX.

The repository separates the shared acceptance-test contract from each system
under test:

- `robbdd_tutorials/models/pick_place/common` contains the BDD, Scene, and
  specification-only sorting extension shared by every
  implementation.
- `robbdd_tutorials/models/pick_place/mujoco_motion_spec` contains the first
  execution setup, including its BDDX, using motion-spec and MuJoCo.
- A BehaviorTree.CPP and Isaac Sim setup is planned but not runnable yet.

The published
[Scenarios and Variations tutorial](https://minhnh.github.io/bdd-dsl/at-tutorial-scenarios.html)
contains the requirements and walks through the common models.

## Create the workspace

Common dependencies:

- [ROS 2 Jazzy on Ubuntu 24.04](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)
- [Git LFS](https://git-lfs.com/) for pulling binary resources
- [vcs2l](https://github.com/ros-infrastructure/vcs2l#how-to-install-vcs2l)
  provides the `vcs` command used by the setup script.
- [`python3-colcon-common-extensions`](https://colcon.readthedocs.io/en/released/user/installation.html#quick-directory-changes)
  provides `/usr/share/colcon_cd/function/colcon_cd.sh` for the generated environment scripts.
- (optional) [uv](https://docs.astral.sh/uv/getting-started/installation/) for managing Python
  virtual environments. Setup uses `uv` when it is already available, otherwise the
  virtual environment's `python -m pip`.

`motion-spec` dependencies:

- [Ant](https://ant.apache.org/manual/install.html)

After configuring the ROS apt repository above, install these together:

```bash
sudo apt update
sudo apt install git git-lfs python3-vcs2l python3-colcon-common-extensions
sudo apt install ant  # motion-spec setup
git lfs install
sudo rosdep init  # once per machine; skip if already initialized
```

Then clone this repository as a ROS package under `src` and run its setup script:

```bash
mkdir -p ~/ros_bdd_ws/src
git clone https://github.com/minhnh/robbdd_tutorials.git \
  ~/ros_bdd_ws/src/robbdd_tutorials
cd ~/ros_bdd_ws/src/robbdd_tutorials
./scripts/setup mujoco jazzy
```

The setup imports `repos/common.repos` and `repos/mujoco.repos`, keeps the
editable Python sources under `~/ros_bdd_ws/pydeps`, creates
`~/ros_bdd_ws/.venv`, and puts all build artifacts in the workspace root.
Motion-spec manages STST and the compiled motion dependencies under
`~/ros_bdd_ws/.ms-sources`; `mj_kdl_wrapper` is installed
non-editably because it contains a compiled Python extension.

Source the generated file matching the current shell:

```bash
source ~/ros_bdd_ws/setup-robbdd-tutorials.zsh  # zsh
# source ~/ros_bdd_ws/setup-robbdd-tutorials.bash  # Bash
```

The sourced environment loads `colcon_cd` and aliases it as `roscd`, so
`roscd robbdd_tutorials` jumps to this package. It also provides two maintenance commands:

```bash
bdd_tutorial pull
bdd_tutorial build
```

The repository keeps the colcon defaults next to the tutorial sources as an
input, but setup copies them to the workspace root. Generated `build`,
`install`, and `log` directories never belong inside `robbdd_tutorials`.

## Dependency manifests

`repos/isaacsim-bt.repos` currently imports the WIP generic behavior-tree
executor only. It deliberately does not claim to install Isaac Sim or provide
a runnable setup.

## Process layout

Execution is intentionally limited to the `nominal-pick-place` scenario.
`sorting.bdd` is not loaded by the graph manifest because set execution is
still work in progress.

The MuJoCo walkthrough keeps each long-lived process in its own terminal:

1. `ros2 run bdd_exec_ros2 web_visualizer`
2. `motion-spec run "$(ros2 pkg prefix --share robbdd_tutorials)/models/pick_place/mujoco_motion_spec/pick_place_single.robmot" --headless`
3. `ros2 launch robbdd_tutorials pick_place_coordinator.launch.yaml`
4. `ros2 topic pub --once /bdd/start std_msgs/msg/Empty '{}'`

The motion-spec process owns the simulator and waits for a
`bdd_ros2_interfaces/action/Behaviour` goal. The YAML launch starts only the
BDD coordinator. The model provides the behavior action server, BDD boundary events, and
direct scene-pose observations used by the coordinator.

The pipeline currently produces a complete verdict, but the MuJoCo nominal run
still reports `object-at-place` as false: the released cube remains about 0.47 m
from the bin observation point. Aligning the placement controller and scene is
the remaining behavior-model issue.
