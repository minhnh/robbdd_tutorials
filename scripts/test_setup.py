"""Offline installer selection check: python3 scripts/test_setup.py."""
import json
import os
from pathlib import Path
import subprocess
import tempfile


setup = Path(__file__).with_name("setup").read_text()
install = setup[setup.index("install_python_packages() {"):setup.index("write_environment() {")]
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    bin_dir = root / "venv with spaces" / "bin"
    bin_dir.mkdir(parents=True)
    log = root / "calls.jsonl"
    mock = """#!/usr/bin/python3
import json, os, sys
with open(os.environ['CALL_LOG'], 'a') as log:
    log.write(json.dumps(sys.argv) + '\\n')
if sys.argv[1:] == ['-m', 'pip', '--version']:
    sys.exit(int(os.environ['MISSING_PIP']))
"""
    python = bin_dir / "python"
    python.write_text(mock)
    python.chmod(0o755)
    for use_uv, missing_pip in [(True, True), (False, False), (False, True)]:
        uv = bin_dir / "uv"
        if use_uv:
            uv.write_text(mock)
            uv.chmod(0o755)
        else:
            uv.unlink(missing_ok=True)
        log.write_text("")
        subprocess.run(
            ["/bin/bash", "-c", 'set -eu; VENV="$1"; WS="$2"; CONTEXT=mujoco\n'
             + install + '\ninstall_python_packages', "check", str(bin_dir.parent), str(root)],
            env={**os.environ, "PATH": str(bin_dir), "CALL_LOG": str(log),
                 "MISSING_PIP": str(int(missing_pip))}, check=True,
        )
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        prefix = ([str(uv), "pip", "install", "--python", str(python)] if use_uv
                  else [str(python), "-m", "pip", "install"])
        installs = [call for call in calls if call[:len(prefix)] == prefix]
        assert len(installs) == 9, calls
        assert "zstandard" in installs[0]
        assert installs[-1][len(prefix):] == ["--no-deps", "-e", str(root / "pydeps/motion-spec")]
        assert ([str(python), "-m", "ensurepip", "--upgrade"] in calls) == (missing_pip and not use_uv)
print("PASS: uv, pip, and pip bootstrap for an existing uv-created venv")

# Exercise the real setup script end to end, without installing or downloading.
import pty
import shutil

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    ws = root / "tutorial workspace"
    repo = ws / "src/robbdd_tutorials"
    repo.mkdir(parents=True)
    original = Path(__file__).resolve().parent.parent
    shutil.copytree(original / "scripts", repo / "scripts")
    shutil.copytree(original / "repos", repo / "repos")
    shutil.copy(original / "colcon_defaults.yaml", repo)
    venv = ws / ".venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin/activate").write_text("")
    (venv / "pyvenv.cfg").write_text("include-system-site-packages = true\n")
    nvidia = root / "IsaacSim-ros_workspaces"
    ros_ws = nvidia / "jazzy_ws"
    (ros_ws / "src/moveit/isaac_moveit").mkdir(parents=True)
    (ros_ws / "install").mkdir()
    for ext in ("bash", "zsh"):
        (ros_ws / f"install/local_setup.{ext}").write_text("")
    commands = root / "bin"
    commands.mkdir()
    log = root / "commands.jsonl"
    mock = '''#!/usr/bin/python3
import json, os, sys
from pathlib import Path
name = Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ['CALL_LOG'], 'a') as stream:
    stream.write(json.dumps([name, args, os.getcwd()]) + '\\n')
if name == 'git':
    if 'rev-parse' in args:
        if '--show-toplevel' in args:
            print(args[args.index('-C') + 1])
    elif 'branch' in args:
        print(os.environ.get('MOCK_BRANCH', 'fix/jazzy-asyncio-sleep'))
    elif 'status' in args:
        print(os.environ.get('MOCK_DIRTY', ''), end='')
    elif 'clone' in args:
        root = Path(args[-1]) / 'jazzy_ws'
        (root / 'src/moveit/isaac_moveit').mkdir(parents=True)
        (root / 'install').mkdir()
        (root / 'install/local_setup.bash').write_text('')
if name == 'colcon' and args[0] == 'list':
    print('src/moveit/isaac_moveit')
'''
    for name in ("sudo", "git", "colcon", "rosdep", "vcs", "ant", "uv"):
        command = commands / name
        command.write_text(mock)
        command.chmod(0o755)
    env = {**os.environ, "PATH": f"{commands}:/usr/bin:/bin",
           "CALL_LOG": str(log), "ROBBDD_ISAAC_ROS_WS": str(ros_ws)}
    # Tests assume the supported ROS distro is installed, but never touch it.
    assert Path('/opt/ros/jazzy/setup.bash').exists()

    def run_setup(context="isaacsim-bt", options=(), answer=None, extra=None):
        log.write_text("")
        args = ["bash", str(repo / "scripts/setup"), *options, context, "jazzy"]
        if answer is None:
            result = subprocess.run(args, env={**env, **(extra or {})},
                                    stdin=subprocess.DEVNULL, capture_output=True, text=True)
        else:
            master, slave = pty.openpty()
            try:
                process = subprocess.Popen(args, env={**env, **(extra or {})}, stdin=slave,
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                os.write(master, (answer + "\n").encode())
                stdout, stderr = process.communicate(timeout=30)
                result = subprocess.CompletedProcess(args, process.returncode, stdout, stderr)
            finally:
                os.close(master)
                os.close(slave)
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        return result, calls

    for context, options, answer, expect_apt in (
        ("isaacsim-bt", (), None, False),
        ("isaacsim-bt", (), "n", False),
        ("isaacsim-bt", (), "y", True),
        ("isaacsim-bt", ("--install-system-packages",), None, True),
        ("isaacsim-bt", ("--build", "--install-system-packages"), "y", False),
    ):
        result, calls = run_setup(context, options, answer)
        assert result.returncode == 0, result.stderr
        apt = [args for name, args, cwd in calls if name == "sudo"]
        assert bool(apt) == expect_apt, calls
        if apt:
            assert apt[0][:2] == ["apt", "install"] and "ant" not in apt[0], apt
            assert "sudo apt install" in result.stdout
        builds = [(args, cwd) for name, args, cwd in calls if name == "colcon" and args[0] == "build"]
        assert [cwd for args, cwd in builds] == [str(ros_ws), str(ws)], builds
        assert builds[0][0] == ["build", "--base-paths", "src/moveit", "--packages-up-to", "isaac_moveit"]
        assert builds[1][0] == ["build", "--packages-up-to", "robbdd_tutorials", "bdd_bt_executor_ros2"]
        submodules = [args for name, args, cwd in calls if name == "git" and "submodule" in args]
        assert len(submodules) == 1 and all("humble" not in arg for arg in submodules[0])
        for ext in ("bash", "zsh"):
            generated = (ws / f"setup-robbdd-tutorials.{ext}").read_text()
            assert generated.index(str(ros_ws / "install")) < generated.index(str(ws / "install"))
            assert "ROBBDD_ISAACSIM_VERSION" not in generated
            assert f"export ROBBDD_ISAAC_ROS_WS='{ros_ws}'" in generated

    # Rebuilds allow local edits; initial setup still rejects dirty checkouts.
    (commands / "ant").unlink()
    for extra in ({}, {"MOCK_DIRTY": " M modified\n"}):
        result, calls = run_setup(options=("--build",), extra=extra)
        assert result.returncode == 0, result.stderr
        assert sum(name == "colcon" and args[0] == "build" for name, args, cwd in calls) == 2
        assert not any(name == "git" and "status" in args for name, args, cwd in calls)
    result, calls = run_setup(extra={"MOCK_DIRTY": " M modified\n"})
    assert result.returncode != 0
    assert not any(name == "colcon" for name, args, cwd in calls)
    result, calls = run_setup(options=("--build",), extra={"MOCK_BRANCH": "wrong"})
    assert result.returncode != 0
    assert not any(name == "colcon" for name, args, cwd in calls)
    result, calls = run_setup(extra={"ROBBDD_ISAAC_ROS_WS": str(root / "new checkout/jazzy_ws")})
    assert result.returncode == 0, result.stderr
    assert any(name == "git" and args[0] == "clone" and "fix/jazzy-asyncio-sleep" in args
               and "https://github.com/minhnh/IsaacSim-ros_workspaces.git" in args
               for name, args, cwd in calls)

    result = subprocess.run(
        ["bash", str(repo / "scripts/setup"), "isaacsim-bt", "jazzy", "6.1.0"],
        env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True)
    assert result.returncode != 0 and "too many arguments" in result.stderr

    # MuJoCo prompt selects Ant and never accesses the NVIDIA workspace.
    ant = commands / "ant"
    ant.write_text(mock)
    ant.chmod(0o755)
    motion = commands / "motion-spec"
    motion.write_text(mock)
    motion.chmod(0o755)
    result, calls = run_setup("mujoco", answer="y")
    assert result.returncode == 0, result.stderr
    assert "ant" in next(args for name, args, cwd in calls if name == "sudo")
    assert not any(name == "git" for name, args, cwd in calls), calls
    assert str(ros_ws / "install") not in (ws / "setup-robbdd-tutorials.bash").read_text()

    # The helper must forward context and preserve the branch on pull.
    (repo / "scripts/setup").write_text(mock)
    helper_env = {**env, "ROBBDD_TUTORIAL_WS": str(ws),
                  "ROBBDD_TUTORIAL_CONTEXT": "isaacsim-bt",
                  "ROS_DISTRO": "jazzy"}
    log.write_text("")
    subprocess.run([str(repo / "scripts/bdd_tutorial"), "build"], env=helper_env, check=True)
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    assert calls[-1][1] == ["--build", "isaacsim-bt", "jazzy"], calls
    log.write_text("")
    subprocess.run([str(repo / "scripts/bdd_tutorial"), "pull"], env=helper_env, check=True)
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    assert calls[-1][:2] == ["git", ["-C", str(nvidia), "fetch", "https://github.com/minhnh/IsaacSim-ros_workspaces.git"]], calls
print("PASS: setup prompts, sibling underlay, build order, branch checks, and helper persistence")
