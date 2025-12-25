import os
import platform
import shutil
import tempfile
import zipfile
from pathlib import Path
from app.utils.logger import get_logger
import httpx


def ensure_ffmpeg_or_raise():
    """
    Ensure ffmpeg & ffprobe are available.
    - If present in PATH or pointed by FFMPEG_LOCATION/FFMPEG_BINARY -> OK
    - Otherwise try to auto-install into local ./bin and export FFMPEG_LOCATION and PATH
    - If still失败 -> raise RuntimeError
    """
    logger = get_logger(__name__)

    def _is_ready() -> bool:
        ff = shutil.which("ffmpeg")
        fp = shutil.which("ffprobe")
        if ff and fp:
            return True
        loc = os.getenv("FFMPEG_LOCATION") or os.getenv("FFMPEG_BINARY")
        if loc:
            p = Path(loc)
            probe = (p if p.is_dir() else p.parent)
            ff = shutil.which("ffmpeg", path=str(probe))
            fp = shutil.which("ffprobe", path=str(probe))
            return bool(ff and fp)
        return False

    if _is_ready():
        return

    # Try auto-install
    system = platform.system().lower()
    bin_dir = Path(__file__).resolve().parents[3] / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    try:
        if system == "windows":
            # Download static build zip (essentials)
            url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
            logger.info("FFmpeg not found, downloading Windows static build...")
            with httpx.stream("GET", url, timeout=60.0) as r:
                r.raise_for_status()
                with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as f:
                    for chunk in r.iter_bytes():
                        f.write(chunk)
                    tmp_zip = f.name
            # Extract and copy ffmpeg.exe/ffprobe.exe into ./bin
            with zipfile.ZipFile(tmp_zip, "r") as zf:
                zf.extractall(bin_dir)
            # Locate inner folder (ffmpeg-xxxx-essentials_build\bin\*.exe)
            exe_ffmpeg = None
            exe_ffprobe = None
            for root, _, files in os.walk(bin_dir):
                if "ffmpeg.exe" in files and "ffprobe.exe" in files:
                    exe_ffmpeg = Path(root) / "ffmpeg.exe"
                    exe_ffprobe = Path(root) / "ffprobe.exe"
                    break
            if not exe_ffmpeg or not exe_ffprobe:
                raise RuntimeError("FFmpeg downloaded but binaries not found in archive")
            # Copy to top-level bin for stability
            shutil.copy2(exe_ffmpeg, bin_dir / "ffmpeg.exe")
            shutil.copy2(exe_ffprobe, bin_dir / "ffprobe.exe")
            os.environ["FFMPEG_LOCATION"] = str(bin_dir)
            os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
            logger.info(f"FFmpeg installed into {bin_dir}")

        elif system in ("linux", "darwin"):
            # Try package manager first
            logger.info("FFmpeg not found, trying to install via package manager...")
            if system == "linux":
                # Attempt apt-get install -y ffmpeg (best-effort)
                import subprocess

                try:
                    subprocess.check_call(["bash", "-lc", "which ffmpeg || sudo apt-get update && sudo apt-get install -y ffmpeg"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass
            elif system == "darwin":
                # Try brew (best-effort)
                import subprocess

                try:
                    subprocess.check_call(["/bin/bash", "-lc", "which ffmpeg || brew install ffmpeg"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass

            if not _is_ready():
                # As a fallback, we could download static binaries here (omitted for brevity on non-Windows)
                logger.warning("FFmpeg auto-installation may have failed; please install ffmpeg via your package manager.")

        else:
            logger.warning(f"Unsupported OS for auto-install: {system}. Please install ffmpeg manually.")
    except Exception as e:
        logger.error(f"Auto-install FFmpeg failed: {e}")

    if not _is_ready():
        raise RuntimeError("FFmpeg/ffprobe not found. Please install ffmpeg or set FFMPEG_LOCATION.")
