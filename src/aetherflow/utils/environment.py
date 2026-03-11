import asyncio
import logging

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class EnvironmentVerificationResult(BaseModel):
    """Environment verification flags for required tooling."""

    uv: bool
    powershell: bool
    cl_exe: bool

    def __init__(self, uv: bool, powershell: bool, cl_exe: bool):
        """Initialize verification results for required tools."""
        super().__init__(uv=uv, powershell=powershell, cl_exe=cl_exe)


async def check_uv() -> bool:
    """Check if uv is installed and available in the PATH."""
    try:
        await asyncio.create_subprocess_exec('uv', '--version')
        return True
    except Exception as e:
        logger.error(f'Error checking uv: {e}')
        return False


async def check_powershell() -> bool:
    """Check if PowerShell is installed and available in the PATH."""
    try:
        await asyncio.create_subprocess_exec('pwsh', '-v')
        return True
    except Exception as e:
        logger.error(f'Error checking PowerShell: {e}')
        return False


async def check_cl_exe() -> bool:
    """Check if cl.exe (Visual Studio compiler) is installed and available in the PATH."""
    try:
        await asyncio.create_subprocess_exec('cl.exe', '/?')
        return True
    except Exception as e:
        logger.error(f'Error checking cl.exe: {e}')
        return False


async def verify_environment() -> EnvironmentVerificationResult:
    """Verify the environment by checking the availability of uv, PowerShell, and cl.exe."""
    uv_result = await check_uv()
    powershell_result = await check_powershell()
    cl_exe_result = await check_cl_exe()
    return EnvironmentVerificationResult(
        uv=uv_result, powershell=powershell_result, cl_exe=cl_exe_result
    )
