from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH).resolve().parents[1]
sys.path[:0] = [str(ROOT / "be" / "src"), str(ROOT / "ai" / "src")]

datas = collect_data_files("writestory_ai")
datas += [(str(ROOT / "be" / "alembic.ini"), ".")]
migration_root = ROOT / "be" / "migrations"
datas += [
    (str(path), str(path.parent.relative_to(ROOT / "be")))
    for path in migration_root.rglob("*")
    if path.is_file()
]
hiddenimports = ["aiosqlite"]
hiddenimports += collect_submodules("writestory_be")
hiddenimports += collect_submodules("writestory_ai.providers")

a = Analysis(
    [str(ROOT / "be" / "src" / "writestory_be" / "__main__.py")],
    pathex=[str(ROOT / "be" / "src"), str(ROOT / "ai" / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="writestory-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, name="writestory-backend")
