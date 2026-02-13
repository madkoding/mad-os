#!/usr/bin/env python3
"""
Tests for madOS GPU compute driver auto-detection and activation.

Validates that the system includes NVIDIA CUDA and AMD ROCm compute drivers,
and that the setup-gpu-compute script correctly detects and activates them
when compatible hardware is found.

These tests verify:
1. GPU compute packages (CUDA, ROCm, OpenCL) are included in the ISO and installer
2. The setup-gpu-compute script exists, has valid syntax, and correct structure
3. The systemd service is configured for auto-detection at boot
4. The first-boot script enables the GPU compute service
5. The profiledef.sh includes proper permissions
6. The script correctly detects NVIDIA and AMD GPUs via simulated lspci output
7. Driver activation logic for CUDA and ROCm
"""

import os
import re
import subprocess
import sys
import unittest

# ---------------------------------------------------------------------------
# Mock gi / gi.repository so installer modules can be imported headlessly.
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import create_gtk_mocks

gi_mock, repo_mock = create_gtk_mocks()
sys.modules["gi"] = gi_mock
sys.modules["gi.repository"] = repo_mock

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AIROOTFS = os.path.join(REPO_DIR, "airootfs")
BIN_DIR = os.path.join(AIROOTFS, "usr", "local", "bin")
LIB_DIR = os.path.join(AIROOTFS, "usr", "local", "lib")
SYSTEMD_DIR = os.path.join(AIROOTFS, "etc", "systemd", "system")

# Add lib dir to path for imports
sys.path.insert(0, LIB_DIR)


# ═══════════════════════════════════════════════════════════════════════════
# GPU compute packages in packages.x86_64
# ═══════════════════════════════════════════════════════════════════════════
class TestGPUComputePackages(unittest.TestCase):
    """Verify GPU compute packages are included in the ISO package list."""

    def _read_packages(self):
        pkg_file = os.path.join(REPO_DIR, "packages.x86_64")
        with open(pkg_file) as f:
            return [
                line.strip() for line in f
                if line.strip() and not line.strip().startswith("#")
            ]

    def test_nvidia_utils_included(self):
        """nvidia-utils must be in packages.x86_64 for NVIDIA driver support."""
        self.assertIn("nvidia-utils", self._read_packages(),
                       "nvidia-utils must be in packages.x86_64")

    def test_opencl_nvidia_included(self):
        """opencl-nvidia must be in packages.x86_64 for NVIDIA OpenCL support."""
        self.assertIn("opencl-nvidia", self._read_packages(),
                       "opencl-nvidia must be in packages.x86_64")

    def test_cuda_included(self):
        """cuda must be in packages.x86_64 for NVIDIA CUDA toolkit."""
        self.assertIn("cuda", self._read_packages(),
                       "cuda must be in packages.x86_64")

    def test_rocm_hip_runtime_included(self):
        """rocm-hip-runtime must be in packages.x86_64 for AMD GPU compute."""
        self.assertIn("rocm-hip-runtime", self._read_packages(),
                       "rocm-hip-runtime must be in packages.x86_64")

    def test_rocm_opencl_runtime_included(self):
        """rocm-opencl-runtime must be in packages.x86_64 for AMD OpenCL."""
        self.assertIn("rocm-opencl-runtime", self._read_packages(),
                       "rocm-opencl-runtime must be in packages.x86_64")

    def test_opencl_headers_included(self):
        """opencl-headers must be in packages.x86_64 for OpenCL development."""
        self.assertIn("opencl-headers", self._read_packages(),
                       "opencl-headers must be in packages.x86_64")

    def test_ocl_icd_included(self):
        """ocl-icd must be in packages.x86_64 for OpenCL ICD loader."""
        self.assertIn("ocl-icd", self._read_packages(),
                       "ocl-icd must be in packages.x86_64")


# ═══════════════════════════════════════════════════════════════════════════
# GPU compute packages in installer Phase 2
# ═══════════════════════════════════════════════════════════════════════════
class TestGPUComputeInstallerPackages(unittest.TestCase):
    """Verify GPU compute packages are in the installer Phase 2 package list."""

    def test_cuda_in_phase2(self):
        """CUDA must be in PACKAGES_PHASE2."""
        from mados_installer.config import PACKAGES_PHASE2
        self.assertIn("cuda", PACKAGES_PHASE2,
                       "cuda must be in PACKAGES_PHASE2")

    def test_nvidia_utils_in_phase2(self):
        """nvidia-utils must be in PACKAGES_PHASE2."""
        from mados_installer.config import PACKAGES_PHASE2
        self.assertIn("nvidia-utils", PACKAGES_PHASE2,
                       "nvidia-utils must be in PACKAGES_PHASE2")

    def test_opencl_nvidia_in_phase2(self):
        """opencl-nvidia must be in PACKAGES_PHASE2."""
        from mados_installer.config import PACKAGES_PHASE2
        self.assertIn("opencl-nvidia", PACKAGES_PHASE2,
                       "opencl-nvidia must be in PACKAGES_PHASE2")

    def test_rocm_hip_runtime_in_phase2(self):
        """rocm-hip-runtime must be in PACKAGES_PHASE2."""
        from mados_installer.config import PACKAGES_PHASE2
        self.assertIn("rocm-hip-runtime", PACKAGES_PHASE2,
                       "rocm-hip-runtime must be in PACKAGES_PHASE2")

    def test_rocm_opencl_runtime_in_phase2(self):
        """rocm-opencl-runtime must be in PACKAGES_PHASE2."""
        from mados_installer.config import PACKAGES_PHASE2
        self.assertIn("rocm-opencl-runtime", PACKAGES_PHASE2,
                       "rocm-opencl-runtime must be in PACKAGES_PHASE2")

    def test_ocl_icd_in_phase2(self):
        """ocl-icd must be in PACKAGES_PHASE2."""
        from mados_installer.config import PACKAGES_PHASE2
        self.assertIn("ocl-icd", PACKAGES_PHASE2,
                       "ocl-icd must be in PACKAGES_PHASE2")


# ═══════════════════════════════════════════════════════════════════════════
# setup-gpu-compute script structure
# ═══════════════════════════════════════════════════════════════════════════
class TestSetupGPUComputeScript(unittest.TestCase):
    """Verify setup-gpu-compute script exists and has correct structure."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, "setup-gpu-compute")
        if not os.path.isfile(self.script_path):
            self.skipTest("setup-gpu-compute script not found")
        with open(self.script_path) as f:
            self.content = f.read()

    def test_script_exists(self):
        """setup-gpu-compute must exist."""
        self.assertTrue(os.path.isfile(self.script_path))

    def test_valid_bash_syntax(self):
        """setup-gpu-compute must have valid bash syntax."""
        result = subprocess.run(
            ["bash", "-n", self.script_path],
            capture_output=True, text=True,
        )
        self.assertEqual(
            result.returncode, 0,
            f"Bash syntax error: {result.stderr}",
        )

    def test_has_shebang(self):
        """Script must start with a bash shebang."""
        first_line = self.content.splitlines()[0]
        self.assertTrue(first_line.startswith("#!"), "Must start with #!")
        self.assertIn("bash", first_line, "Must use bash")

    def test_uses_strict_mode(self):
        """Script must use bash strict mode."""
        self.assertIn("set -euo pipefail", self.content,
                       "Must use 'set -euo pipefail' for safety")

    def test_has_logging(self):
        """Script must use systemd logging."""
        self.assertIn("LOG_TAG=", self.content,
                       "Must define LOG_TAG for journald logging")
        self.assertIn("mados-gpu-compute", self.content,
                       "Must use mados-gpu-compute as log tag")

    def test_has_nvidia_detection(self):
        """Script must have NVIDIA GPU detection function."""
        self.assertIn("detect_nvidia_gpu", self.content,
                       "Must have detect_nvidia_gpu function")

    def test_has_amd_detection(self):
        """Script must have AMD GPU detection function."""
        self.assertIn("detect_amd_gpu", self.content,
                       "Must have detect_amd_gpu function")

    def test_has_cuda_detection(self):
        """Script must detect CUDA capability."""
        self.assertIn("detect_nvidia_cuda_capable", self.content,
                       "Must have detect_nvidia_cuda_capable function")

    def test_has_rocm_detection(self):
        """Script must detect ROCm capability."""
        self.assertIn("detect_amd_rocm_capable", self.content,
                       "Must have detect_amd_rocm_capable function")

    def test_has_nvidia_activation(self):
        """Script must have NVIDIA CUDA activation function."""
        self.assertIn("activate_nvidia_cuda", self.content,
                       "Must have activate_nvidia_cuda function")

    def test_has_amd_activation(self):
        """Script must have AMD ROCm activation function."""
        self.assertIn("activate_amd_rocm", self.content,
                       "Must have activate_amd_rocm function")

    def test_uses_lspci_for_detection(self):
        """Script must use lspci to detect GPUs."""
        self.assertIn("lspci", self.content,
                       "Must use lspci to detect GPU hardware")

    def test_checks_vga_controllers(self):
        """Script must filter lspci output for VGA/3D controllers."""
        self.assertIn("VGA", self.content,
                       "Must filter for VGA controllers")
        self.assertIn("3D", self.content,
                       "Must filter for 3D controllers")

    def test_loads_nvidia_kernel_module(self):
        """Script must load nvidia kernel module for CUDA."""
        self.assertIn("modprobe nvidia", self.content,
                       "Must load nvidia kernel module")

    def test_loads_amdgpu_kernel_module(self):
        """Script must load amdgpu kernel module for ROCm."""
        self.assertIn("modprobe amdgpu", self.content,
                       "Must load amdgpu kernel module")

    def test_verifies_nvidia_smi(self):
        """Script must verify nvidia-smi for CUDA validation."""
        self.assertIn("nvidia-smi", self.content,
                       "Must use nvidia-smi to verify CUDA")

    def test_verifies_opencl(self):
        """Script must verify OpenCL availability."""
        self.assertIn("verify_opencl", self.content,
                       "Must verify OpenCL availability")

    def test_has_main_function(self):
        """Script must have a main function."""
        self.assertIn("main()", self.content,
                       "Must have main function")

    def test_returns_correct_exit_codes(self):
        """Script must return 0 for GPU found, 1 for no GPU."""
        self.assertIn("return 0", self.content,
                       "Must return 0 when GPU compute is configured")
        self.assertIn("return 1", self.content,
                       "Must return 1 when no compatible GPU found")

    def test_filters_legacy_amd_gpus(self):
        """Script must filter out legacy AMD GPUs that don't support ROCm."""
        self.assertIn("Pre-GCN", self.content,
                       "Must identify pre-GCN AMD GPUs as incompatible")

    def test_checks_nvidia_uvm_module(self):
        """Script must load nvidia_uvm module for CUDA unified memory."""
        self.assertIn("nvidia_uvm", self.content,
                       "Must load nvidia_uvm module for CUDA unified memory")


# ═══════════════════════════════════════════════════════════════════════════
# Simulated GPU detection logic
# ═══════════════════════════════════════════════════════════════════════════
class TestGPUComputeDetectionLogic(unittest.TestCase):
    """Verify GPU compute detection via bash simulation with mocked lspci."""

    SCRIPT_PATH = os.path.join(BIN_DIR, "setup-gpu-compute")

    def _run_with_mock_lspci(self, lspci_output, has_nvidia_smi=False,
                              has_modprobe=True):
        """Run setup-gpu-compute with mocked lspci output."""
        nvidia_smi_mock = ""
        if has_nvidia_smi:
            nvidia_smi_mock = '''
cat > "$MOCK_DIR/nvidia-smi" << 'NVSMI'
#!/bin/bash
if [[ "$*" == *"compute_cap"* ]]; then
    echo "8.6"
elif [[ "$*" == *"name"* ]]; then
    echo "NVIDIA GeForce RTX 3080"
fi
NVSMI
chmod +x "$MOCK_DIR/nvidia-smi"
'''

        modprobe_mock = '''
cat > "$MOCK_DIR/modprobe" << 'MODPROBE'
#!/bin/bash
exit 0
MODPROBE
chmod +x "$MOCK_DIR/modprobe"
''' if has_modprobe else '''
cat > "$MOCK_DIR/modprobe" << 'MODPROBE'
#!/bin/bash
exit 1
MODPROBE
chmod +x "$MOCK_DIR/modprobe"
'''

        bash_code = f'''
MOCK_DIR=$(mktemp -d)

# Create mock lspci
cat > "$MOCK_DIR/lspci" << 'LSPCI'
#!/bin/bash
cat << 'EOF'
{lspci_output}
EOF
LSPCI
chmod +x "$MOCK_DIR/lspci"

# Create mock systemctl
cat > "$MOCK_DIR/systemctl" << 'SYSTEMCTL'
#!/bin/bash
exit 0
SYSTEMCTL
chmod +x "$MOCK_DIR/systemctl"

# Create mock systemd-cat
cat > "$MOCK_DIR/systemd-cat" << 'SDCAT'
#!/bin/bash
exit 0
SDCAT
chmod +x "$MOCK_DIR/systemd-cat"

{modprobe_mock}

{nvidia_smi_mock}

PATH="$MOCK_DIR:$PATH" bash "{self.SCRIPT_PATH}" 2>&1
echo "EXIT_CODE=$?"
rm -rf "$MOCK_DIR"
'''
        result = subprocess.run(
            ["bash", "-c", bash_code],
            capture_output=True, text=True,
        )
        return result.stdout

    def test_detects_nvidia_gpu(self):
        """Must detect NVIDIA GPU from lspci output and return 0."""
        output = self._run_with_mock_lspci(
            "01:00.0 VGA compatible controller: NVIDIA Corporation GA106 [GeForce RTX 3060]",
            has_nvidia_smi=True,
        )
        self.assertIn("NVIDIA GPU detected", output,
                       "Must detect NVIDIA GPU")
        self.assertIn("EXIT_CODE=0", output,
                       "Must return 0 when NVIDIA GPU found")

    def test_detects_amd_gpu(self):
        """Must detect AMD GPU from lspci output and return 0."""
        output = self._run_with_mock_lspci(
            "06:00.0 VGA compatible controller: Advanced Micro Devices, Inc. [AMD/ATI] Navi 10 [Radeon RX 5600 OXT]",
        )
        self.assertIn("AMD GPU detected", output,
                       "Must detect AMD GPU")
        self.assertIn("EXIT_CODE=0", output,
                       "Must return 0 when AMD GPU found")

    def test_no_gpu_returns_1(self):
        """Must return 1 when no compatible GPU is found."""
        output = self._run_with_mock_lspci(
            "00:02.0 VGA compatible controller: Intel Corporation HD Graphics 530",
        )
        self.assertIn("No CUDA/ROCm capable GPU detected", output,
                       "Must report no compatible GPU found")
        self.assertIn("EXIT_CODE=1", output,
                       "Must return 1 when no GPU compute found")

    def test_rejects_legacy_amd_gpu(self):
        """Must reject legacy AMD GPUs that don't support ROCm."""
        output = self._run_with_mock_lspci(
            "01:00.0 VGA compatible controller: ATI Technologies Inc Radeon HD 3870",
        )
        self.assertIn("No CUDA/ROCm capable GPU detected", output,
                       "Must reject pre-GCN AMD GPUs")
        self.assertIn("EXIT_CODE=1", output,
                       "Must return 1 for legacy AMD GPU")

    def test_detects_nvidia_3d_controller(self):
        """Must detect NVIDIA 3D controller (data center GPUs)."""
        output = self._run_with_mock_lspci(
            "00:03.0 3D controller: NVIDIA Corporation A100 [CUDA]",
            has_nvidia_smi=True,
        )
        self.assertIn("NVIDIA GPU detected", output,
                       "Must detect NVIDIA 3D controller")


# ═══════════════════════════════════════════════════════════════════════════
# systemd service configuration
# ═══════════════════════════════════════════════════════════════════════════
class TestGPUComputeService(unittest.TestCase):
    """Verify the mados-gpu-compute.service systemd unit."""

    def setUp(self):
        self.service_path = os.path.join(
            SYSTEMD_DIR, "mados-gpu-compute.service"
        )
        if not os.path.isfile(self.service_path):
            self.skipTest("mados-gpu-compute.service not found")
        with open(self.service_path) as f:
            self.content = f.read()

    def test_service_exists(self):
        """mados-gpu-compute.service must exist."""
        self.assertTrue(os.path.isfile(self.service_path))

    def test_service_description(self):
        """Service must have a description mentioning GPU compute."""
        self.assertIn("GPU Compute", self.content,
                       "Service must describe GPU compute purpose")

    def test_service_is_oneshot(self):
        """Service must be Type=oneshot."""
        self.assertIn("Type=oneshot", self.content,
                       "Service must be Type=oneshot")

    def test_service_runs_after_udev(self):
        """Service must run after udev settle to ensure GPU is detected."""
        self.assertIn("systemd-udev-settle", self.content,
                       "Service must wait for udev to settle")

    def test_service_runs_after_modules_load(self):
        """Service must run after kernel modules are loaded."""
        self.assertIn("systemd-modules-load", self.content,
                       "Service must wait for kernel modules")

    def test_service_exec_start(self):
        """Service must execute setup-gpu-compute script."""
        self.assertIn("ExecStart=/usr/local/bin/setup-gpu-compute", self.content,
                       "Service must run setup-gpu-compute")

    def test_service_wanted_by_multi_user(self):
        """Service must be wanted by multi-user.target."""
        self.assertIn("WantedBy=multi-user.target", self.content,
                       "Service must be wanted by multi-user.target")

    def test_service_has_timeout(self):
        """Service must have a timeout for GPU detection."""
        self.assertIn("TimeoutStartSec=", self.content,
                       "Service must have timeout")


# ═══════════════════════════════════════════════════════════════════════════
# profiledef.sh permissions
# ═══════════════════════════════════════════════════════════════════════════
class TestGPUComputeProfileDef(unittest.TestCase):
    """Verify profiledef.sh includes setup-gpu-compute permissions."""

    def test_profiledef_includes_setup_gpu_compute(self):
        """profiledef.sh must set permissions for setup-gpu-compute."""
        profiledef = os.path.join(REPO_DIR, "profiledef.sh")
        with open(profiledef) as f:
            content = f.read()
        self.assertIn("setup-gpu-compute", content,
                       "profiledef.sh must include setup-gpu-compute")

    def test_profiledef_sets_executable(self):
        """profiledef.sh must set setup-gpu-compute as executable (755)."""
        profiledef = os.path.join(REPO_DIR, "profiledef.sh")
        with open(profiledef) as f:
            content = f.read()
        # Find the setup-gpu-compute line and verify 755 permissions
        for line in content.splitlines():
            if "setup-gpu-compute" in line:
                self.assertIn("755", line,
                               "setup-gpu-compute must have 755 permissions")
                break


# ═══════════════════════════════════════════════════════════════════════════
# First-boot script enables GPU compute service
# ═══════════════════════════════════════════════════════════════════════════
class TestGPUComputeFirstBoot(unittest.TestCase):
    """Verify the first-boot script enables the GPU compute service."""

    def setUp(self):
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        if not os.path.isfile(install_py):
            self.skipTest("installation.py not found")
        with open(install_py) as f:
            self.content = f.read()

    def test_enables_gpu_compute_service(self):
        """First-boot script must enable mados-gpu-compute.service."""
        self.assertIn(
            "mados-gpu-compute.service", self.content,
            "First-boot script must enable mados-gpu-compute.service",
        )

    def test_gpu_compute_enabled_with_systemctl(self):
        """First-boot must use systemctl enable for GPU compute service."""
        self.assertIn(
            "systemctl enable mados-gpu-compute.service", self.content,
            "Must use systemctl enable for GPU compute service",
        )


# ═══════════════════════════════════════════════════════════════════════════
# End-to-end: detection → activation chain
# ═══════════════════════════════════════════════════════════════════════════
class TestGPUComputeEndToEnd(unittest.TestCase):
    """Verify the complete GPU compute chain: detection → activation."""

    def test_script_detects_then_activates(self):
        """setup-gpu-compute must detect GPU before activating drivers."""
        script_path = os.path.join(BIN_DIR, "setup-gpu-compute")
        with open(script_path) as f:
            content = f.read()
        # Detection must happen before activation
        detect_pos = content.find("detect_nvidia_cuda_capable")
        activate_pos = content.find("activate_nvidia_cuda")
        # The main() function calls detect first, then activate
        main_pos = content.find("main()")
        self.assertGreater(main_pos, 0, "Must have main() function")
        # In main(), detect must be referenced before activate
        main_section = content[main_pos:]
        detect_in_main = main_section.find("detect_nvidia_cuda_capable")
        activate_in_main = main_section.find("activate_nvidia_cuda")
        self.assertLess(detect_in_main, activate_in_main,
                          "Must detect before activating NVIDIA CUDA")

    def test_script_detects_amd_then_activates(self):
        """setup-gpu-compute must detect AMD GPU before activating ROCm."""
        script_path = os.path.join(BIN_DIR, "setup-gpu-compute")
        with open(script_path) as f:
            content = f.read()
        main_pos = content.find("main()")
        main_section = content[main_pos:]
        detect_in_main = main_section.find("detect_amd_rocm_capable")
        activate_in_main = main_section.find("activate_amd_rocm")
        self.assertLess(detect_in_main, activate_in_main,
                          "Must detect before activating AMD ROCm")

    def test_both_nvidia_and_amd_supported(self):
        """setup-gpu-compute must support both NVIDIA and AMD GPUs."""
        script_path = os.path.join(BIN_DIR, "setup-gpu-compute")
        with open(script_path) as f:
            content = f.read()
        self.assertIn("nvidia", content.lower(),
                       "Must support NVIDIA GPUs")
        self.assertIn("amd", content.lower(),
                       "Must support AMD GPUs")
        self.assertIn("CUDA", content,
                       "Must reference CUDA")
        self.assertIn("ROCm", content,
                       "Must reference ROCm")


if __name__ == "__main__":
    unittest.main()
