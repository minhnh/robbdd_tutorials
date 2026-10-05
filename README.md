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
[tutorials for automated Testing with RobBDD](https://minhnh.github.io/bdd-dsl/at-tutorial-scenarios.html)
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
git lfs install
# Optional: motion-spec setup
# sudo apt install ant
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

The setup uses `vcs2l` to clone repositories in `repos/*.repos` files.
There are separate files for [common repositories](./repos/common.repos),
execution setup with [`motion-spec` - MuJoCo](./repos/mujoco.repos),
and with [`BehaviorTree.CPP` - Isaac Sim](./repos/isaacsim-bt.repos) (WIP).
This clones editable Python sources under `~/ros_bdd_ws/pydeps` and ROS packages
under `~/ros_bdd_ws/src`.

The setup script also creates a Python vitual environment `~/ros_bdd_ws/.venv`
for installing Python dependencies.
Motion-spec manages STST and the compiled motion dependencies under
`~/ros_bdd_ws/.ms-sources`; `mj_kdl_wrapper` is installed
non-editably because it contains a compiled Python extension.

Source the generated file matching the current shell:

```bash
source ~/ros_bdd_ws/setup-robbdd-tutorials.bash   # bash
# source ~/ros_bdd_ws/setup-robbdd-tutorials.zsh  # zsh
```

The sourced environment loads `colcon_cd` and aliases it as `roscd`, so
`roscd robbdd_tutorials` jumps to this package. It also provides two maintenance commands:

```bash
bdd_tutorial pull   # call vcs pull on all *.repos
bdd_tutorial build  # install
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

The pipeline currently produces a complete verdict, but the MuJoCo nominal run
still reports `object-at-place` as false: the released cube remains about 0.47 m
from the bin observation point. Aligning the placement controller and scene is
the remaining behavior-model issue.

### 2. `BehaviorTree.CPP` in Isaac Sim

TODO(minhnh)
