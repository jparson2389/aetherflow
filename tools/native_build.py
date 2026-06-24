"""Shared CMake build path for native contract and behavioral tests.

The project's CMake build system is the single source of truth for compiling
native targets. Tests consume the targets it declares instead of re-listing
host sources or re-specifying compiler command lines, so the C++/Python
boundary is declared in exactly one place (``CMakeLists.txt`` plus the
canonical native harness).

Gating is on toolchain availability only, never on the host OS: the native
harness needs nothing more than CMake and a C++20 compiler, so it can run on
Linux CI and Windows alike.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

_COMPILER_CANDIDATES = ('c++', 'g++', 'clang++', 'cl')
# GCC/Clang-style drivers that accept the snippet compile flags below; MSVC is
# intentionally excluded because behavioral snippets use gcc-style syntax.
_GCC_STYLE_COMPILERS = ('g++', 'clang++', 'c++')
_BUILD_TIMEOUT_S = 600
_RUN_TIMEOUT_S = 60


def find_cmake() -> str | None:
    """Return the path to the cmake executable, or None when not installed."""
    return shutil.which('cmake')


def find_cxx_compiler() -> str | None:
    """Return the first C++ compiler found on PATH, or None when none exist."""
    for candidate in _COMPILER_CANDIDATES:
        found = shutil.which(candidate)
        if found is not None:
            return found
    return None


def find_gcc_style_compiler() -> str | None:
    """Return the first gcc/clang-style C++ compiler on PATH, or None.

    Behavioral snippet tests compile with gcc-style flags (``-std=c++20``,
    ``-pthread``, direct static-archive inputs), so MSVC is not a candidate.
    """
    for candidate in _GCC_STYLE_COMPILERS:
        found = shutil.which(candidate)
        if found is not None:
            return found
    return None


class NativeToolchainUnavailable(RuntimeError):
    """Raised when no usable C++ toolchain (cmake + compiler) is present."""


class NativeBuild:
    """A configured CMake build tree shared across native tests."""

    def __init__(self, cmake: str, build_dir: Path) -> None:
        """Bind to a cmake executable and an already-configured build dir."""
        self._cmake = cmake
        self._build_dir = build_dir

    @property
    def build_dir(self) -> Path:
        """Return the CMake binary directory backing this build."""
        return self._build_dir

    def build_target(self, target: str) -> Path:
        """Build a single CMake target and return its executable artifact.

        Args:
            target: The CMake target name to build.

        Returns:
            The path to the produced executable, resolved platform-neutrally
            (no hardcoded ``.exe`` and no multi-config directory assumptions).

        Raises:
            RuntimeError: If the build fails or produces no executable.

        """
        self._build(target)
        return self._resolve_artifact(target, {target, f'{target}.exe'})

    def library_artifact(self, target: str) -> Path:
        """Build a CMake library target and return its static-archive artifact.

        This is the single shared build path for the host translation units:
        behavioral tests link the archive produced here instead of re-listing
        host sources in per-test compiler command lines.

        Args:
            target: The CMake library target name to build.

        Returns:
            The path to the produced static library archive.

        Raises:
            RuntimeError: If the build fails or produces no archive.

        """
        self._build(target)
        return self._resolve_artifact(
            target, {f'lib{target}.a', f'{target}.a', f'{target}.lib'}
        )

    def compile_and_run(
        self,
        name: str,
        libraries: tuple[str, ...],
        work_dir: Path,
        source: str,
        run_args: tuple[str, ...] = (),
    ) -> subprocess.CompletedProcess[str]:
        """Compile a C++ snippet against shared host libraries and run it.

        The snippet is linked against the CMake-built archives named in
        ``libraries`` (in link order), so the host sources and contract symbols
        live in exactly one place — CMakeLists.txt and the canonical native
        harness — never in the test.

        Args:
            name: Base name for the snippet source and binary.
            libraries: CMake library targets to link, in dependency-first order.
            work_dir: Directory for the generated source and binary.
            source: The C++ snippet source text.
            run_args: Command-line arguments to pass to the compiled binary.

        Returns:
            The CompletedProcess of running the compiled binary.

        Raises:
            NativeToolchainUnavailable: If no gcc/clang-style compiler exists.
            RuntimeError: If the snippet fails to compile.

        """
        compiler = find_gcc_style_compiler()
        if compiler is None:
            raise NativeToolchainUnavailable('C++ compiler not available')

        source_path = work_dir / f'{name}.cpp'
        binary_path = work_dir / name
        source_path.write_text(source, encoding='utf-8')
        lib_paths = [str(self.library_artifact(lib)) for lib in libraries]

        compiled = subprocess.run(
            [
                compiler,
                '-std=c++20',
                '-I',
                str(PROJECT_ROOT / 'include'),
                str(source_path),
                *lib_paths,
                '-pthread',
                '-o',
                str(binary_path),
            ],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=_BUILD_TIMEOUT_S,
        )
        if compiled.returncode != 0:
            raise RuntimeError(
                f'Failed to compile native snippet {name!r}:\n'
                f'{compiled.stdout}{compiled.stderr}'
            )

        return subprocess.run(
            [str(binary_path), *run_args],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=_RUN_TIMEOUT_S,
        )

    def _build(self, target: str) -> None:
        """Build a CMake target in the configured build directory.

        Args:
            target: CMake target name to build.

        Raises:
            RuntimeError: If the target build exits non-zero.

        """
        result = subprocess.run(
            [self._cmake, '--build', str(self._build_dir), '--target', target],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=_BUILD_TIMEOUT_S,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f'Failed to build target {target!r}:\n{result.stdout}{result.stderr}'
            )

    def _resolve_artifact(self, target: str, names: set[str]) -> Path:
        """Resolve a produced build artifact by candidate file names.

        Args:
            target: Logical target name, used only for error messages.
            names: Candidate artifact file names to match.

        Returns:
            The first matching artifact path under the build directory.

        Raises:
            RuntimeError: If no matching artifact exists.

        """
        matches = sorted(
            path
            for path in self._build_dir.rglob('*')
            if path.is_file() and path.name in names and 'CMakeFiles' not in path.parts
        )
        if not matches:
            raise RuntimeError(
                f'Target {target!r} produced no artifact under {self._build_dir}'
            )
        return matches[0]


def configure_native_build(build_dir: Path) -> NativeBuild:
    """Configure the CMake project once and return a NativeBuild handle.

    Args:
        build_dir: An empty directory to use as the CMake binary directory.

    Returns:
        A NativeBuild bound to the configured tree.

    Raises:
        NativeToolchainUnavailable: If cmake or a C++ compiler is absent — the
            only condition that should skip native tests rather than fail CI.
        RuntimeError: If the toolchain is present but CMake configure fails (a
            real configuration regression that must surface as a failure).

    """
    cmake = find_cmake()
    if cmake is None or find_cxx_compiler() is None:
        raise NativeToolchainUnavailable(
            'cmake and a C++ compiler are required for native tests'
        )
    result = subprocess.run(
        [cmake, '-S', str(PROJECT_ROOT), '-B', str(build_dir)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=_BUILD_TIMEOUT_S,
    )
    if result.returncode != 0:
        raise RuntimeError(f'CMake configure failed:\n{result.stdout}{result.stderr}')
    return NativeBuild(cmake, build_dir)
