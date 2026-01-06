#app/pipeline.py
import os
import subprocess
from typing import Optional, Dict, Any, List

PY = os.getenv("PYTHON_BIN", "python")


def run_script(
    path: str,
    args: Optional[List[str]] = None,
    *,
    timeout: int = 3600,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    tail: int = 4000,
) -> Dict[str, Any]:
    """
    Ejecuta un script Python y devuelve salida recortada para API/UI.
    - timeout: evita procesos colgados
    - cwd: útil si tu script depende de rutas relativas
    - env: variables extra
    """
    cmd = [PY, path] + (args or [])
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            env=merged_env,
            timeout=timeout,
        )
        stdout = (p.stdout or "")
        stderr = (p.stderr or "")
        return {
            "cmd": cmd,
            "returncode": p.returncode,
            "stdout": stdout[-tail:],
            "stderr": stderr[-tail:],
        }
    except subprocess.TimeoutExpired as e:
        return {
            "cmd": cmd,
            "returncode": 124,
            "stdout": (e.stdout or "")[-tail:] if hasattr(e, "stdout") else "",
            "stderr": (e.stderr or "")[-tail:] if hasattr(e, "stderr") else "",
            "error": f"timeout_exceeded ({timeout}s)"
        }
