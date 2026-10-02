import { spawn, spawnSync } from "node:child_process";
import { homedir, tmpdir } from "node:os";
import { delimiter, join } from "node:path";
import process from "node:process";

const windows = process.platform === "win32";
const probe = spawnSync(windows ? "where.exe" : "which", ["uv"], {
  encoding: "utf8",
  shell: windows,
});
const uvFromPath = probe.status === 0 ? probe.stdout.trim().split(/\r?\n/)[0] : null;
const uvFallback = join(homedir(), ".local", "bin", windows ? "uv.exe" : "uv");
const uv = uvFromPath || uvFallback;
const env = {
  ...process.env,
  UV_CACHE_DIR:
    process.env.UV_CACHE_DIR || join(tmpdir(), "writestoryapp-uv-cache"),
  UV_PYTHON_INSTALL_DIR:
    process.env.UV_PYTHON_INSTALL_DIR ||
    join(homedir(), ".local", "share", "uv", "python"),
};

const child = spawn(uv, ["run", "--no-sync", "python", "tools/dev/run_dev.py"], {
  cwd: new URL("../../", import.meta.url),
  env,
  stdio: "inherit",
  windowsHide: true,
});

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => child.kill(signal));
}

child.on("error", (error) => {
  console.error(`[dev] Could not launch uv at ${uv}: ${error.message}`);
  process.exitCode = 1;
});
child.on("exit", (code, signal) => {
  process.exitCode = code ?? (signal ? 1 : 0);
});
