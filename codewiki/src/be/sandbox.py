import os
import subprocess
import tempfile
import shutil
from dataclasses import dataclass

'''
# 这是一个简单的python 沙箱执行命令工具
# 沙箱实现
    unshare / namespaces → 隔离 pid / net / mount / ipc / user
    chroot → 限制 root filesystem
    cgroups → CPU / memory 限制
    ulimit → 资源限制
    seccomp（可选） → syscall 限制
    iptables / net namespace → 网络控制

# 示例配置
cfg = SandboxConfig(
    root="/sandbox/rootfs",
)

sb = Sandbox(cfg)

result = sb.run("ls -al /")

print(result["stdout"])

'''


@dataclass
class SandboxConfig:
    root: str # 沙箱根目录
    network: bool = False  # 是否启用网络隔离
    allow_sudo: bool = False  # 是否允许使用sudo
    allow_mount: bool = False  # 是否允许挂载文件系统
    cpu_limit: int = 4  # CPU 核心数限制
    mem_limit: int = 1024  # 1GB 内存限制
    pids_limit: int = 128  # 进程数限制
    timeout: int = 60  # 默认命令的超时时间（60秒）


class Sandbox:
    def __init__(self, config: SandboxConfig):
        self.config = config
        self.cgroup_path = f"/sys/fs/cgroup/sandbox_{os.getpid()}"
        self._setup_cgroup()

    # -------------------------
    # CGROUP
    # -------------------------

    def _setup_cgroup(self):
        os.makedirs(self.cgroup_path, exist_ok=True)

        cpu_quota = self.config.cpu_limit * 100000

        try:
            with open(f"{self.cgroup_path}/cpu.max", "w") as f:
                f.write(f"{cpu_quota} 100000")
        except:
            pass

        mem_bytes = self.config.mem_limit * 1024 * 1024

        try:
            with open(f"{self.cgroup_path}/memory.max", "w") as f:
                f.write(str(mem_bytes))
        except:
            pass

        try:
            with open(f"{self.cgroup_path}/pids.max", "w") as f:
                f.write(str(self.config.pids_limit))
        except:
            pass

    # -------------------------
    # NAMESPACE COMMAND
    # -------------------------

    def _build_unshare_cmd(self):

        cmd = [
            "unshare",
            "--fork",
            "--pid",
            "--ipc",
            "--uts",
            "--mount",
            "--user",
            "--map-root-user",
        ]

        if not self.config.network:
            cmd.append("--net")

        return cmd

    # -------------------------
    # CHROOT ENV
    # -------------------------

    def _prepare_root(self):
        root = self.config.root

        if not os.path.exists(root):
            raise RuntimeError("rootfs does not exist")

        required = ["proc", "dev", "tmp"]

        for d in required:
            os.makedirs(os.path.join(root, d), exist_ok=True)

    # -------------------------
    # LIMITS
    # -------------------------

    def _build_limits(self):

        cmds = []

        cmds.append(f"ulimit -t {self.config.timeout}")
        cmds.append(f"ulimit -v {self.config.mem_limit * 1024}")

        if not self.config.allow_mount:
            cmds.append("mount -t tmpfs tmpfs /tmp")

        return " && ".join(cmds)

    # -------------------------
    # NETWORK
    # -------------------------

    def _network_setup(self):

        if not self.config.network:
            return "ip link set lo down || true"

        return "ip link set lo up || true"

    # -------------------------
    # SUDO CONTROL
    # -------------------------

    def _sanitize_env(self):

        if not self.config.allow_sudo:
            os.environ["PATH"] = "/usr/bin:/bin"

    # -------------------------
    # RUN COMMAND
    # -------------------------

    def run(self, command: str):

        self._prepare_root()
        self._sanitize_env()

        unshare_cmd = self._build_unshare_cmd()

        limit_cmd = self._build_limits()

        net_cmd = self._network_setup()

        full_cmd = f"""
{limit_cmd} &&
{net_cmd} &&
exec {command}
"""

        cmd = (
            unshare_cmd
            + [
                "chroot",
                self.config.root,
                "/bin/bash",
                "-c",
                full_cmd,
            ]
        )

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        stdout, stderr = process.communicate(timeout=self.config.timeout)

        return {
            "code": process.returncode,
            "stdout": stdout,
            "stderr": stderr,
        }

    # -------------------------
    # CLEANUP
    # -------------------------

    def cleanup(self):
        try:
            shutil.rmtree(self.cgroup_path)
        except:
            pass