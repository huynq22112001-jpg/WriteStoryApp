use std::{
    fs::{self, OpenOptions},
    io::{BufRead, BufReader, Read, Write},
    net::{TcpStream, ToSocketAddrs},
    path::{Path, PathBuf},
    process::{Child, ChildStdin, Command, Stdio},
    sync::{Arc, Mutex},
    thread,
    time::Duration,
};

use base64::{engine::general_purpose::URL_SAFE_NO_PAD, Engine};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use tauri::{AppHandle, Emitter, Manager};

use crate::{
    boot_state::{BackendInfo, BootError, BootPhase, BootProgress, BootState},
    data_root::DataMarker,
};

const PROTOCOL_VERSION: u32 = 1;
const READY_TIMEOUT: Duration = Duration::from_secs(60);
const HEALTH_TIMEOUT: Duration = Duration::from_secs(2);
const STDERR_TAIL_LINES: usize = 200;

#[derive(Clone, Debug, PartialEq)]
enum ProtocolMessage {
    Progress(String),
    Ready {
        port: u16,
        protocol_version: u32,
        pid: u32,
    },
    Fatal {
        code: String,
        message: String,
        detail: Value,
    },
    Ignore,
}

fn parse_protocol_line(line: &str) -> ProtocolMessage {
    let Ok(value) = serde_json::from_str::<Value>(line) else {
        return ProtocolMessage::Ignore;
    };
    match value.get("event").and_then(Value::as_str) {
        Some("progress") => value
            .get("stage")
            .and_then(Value::as_str)
            .map(|stage| ProtocolMessage::Progress(stage.to_owned()))
            .unwrap_or(ProtocolMessage::Ignore),
        Some("ready") => match (
            value.get("port").and_then(Value::as_u64),
            value.get("protocol_version").and_then(Value::as_u64),
            value.get("pid").and_then(Value::as_u64),
        ) {
            (Some(port), Some(protocol_version), Some(pid))
                if port <= u16::MAX as u64 && pid <= u32::MAX as u64 =>
            {
                ProtocolMessage::Ready {
                    port: port as u16,
                    protocol_version: protocol_version as u32,
                    pid: pid as u32,
                }
            }
            _ => ProtocolMessage::Ignore,
        },
        Some("fatal") => match (
            value.get("code").and_then(Value::as_str),
            value.get("message").and_then(Value::as_str),
        ) {
            (Some(code), Some(message)) => ProtocolMessage::Fatal {
                code: code.to_owned(),
                message: message.to_owned(),
                detail: value.get("detail").cloned().unwrap_or_else(|| json!({})),
            },
            _ => ProtocolMessage::Ignore,
        },
        _ => ProtocolMessage::Ignore,
    }
}

#[derive(Deserialize)]
struct HealthResponse {
    status: String,
    protocol_version: u32,
    data_id: Option<String>,
}

#[derive(Serialize)]
struct BootstrapConfig<'a> {
    protocol_version: u32,
    token: &'a str,
    data_root: &'a Path,
    data_id: &'a str,
    parent_pid: u32,
    app_version: &'a str,
    allowed_origins: [&'a str; 4],
    dev_features: bool,
    log_level: &'a str,
}

struct Shared {
    state: Mutex<BootState>,
    child: Mutex<Option<Child>>,
    stdin: Mutex<Option<ChildStdin>>,
    stderr_tail: Mutex<Vec<String>>,
    last_protocol_at: Mutex<std::time::Instant>,
    token: Mutex<Option<String>>,
    #[cfg(windows)]
    _job: Mutex<Option<crate::win_job::JobObject>>,
}

pub struct BackendManager(Arc<Shared>);

#[derive(Clone, Debug, Serialize)]
pub struct BackendSession {
    pub base_url: String,
    pub token: String,
    pub protocol_version: u32,
}

impl BackendManager {
    pub fn new() -> Self {
        Self(Arc::new(Shared {
            state: Mutex::new(BootState::resolving()),
            child: Mutex::new(None),
            stdin: Mutex::new(None),
            stderr_tail: Mutex::new(Vec::new()),
            last_protocol_at: Mutex::new(std::time::Instant::now()),
            token: Mutex::new(None),
            #[cfg(windows)]
            _job: Mutex::new(None),
        }))
    }

    fn update(&self, app: &AppHandle, f: impl FnOnce(&mut BootState)) {
        if let Ok(mut state) = self.0.state.lock() {
            let old_phase = format!("{:?}", state.phase);
            f(&mut state);
            let new_phase = format!("{:?}", state.phase);
            if old_phase != new_phase {
                if let Some(root) = state.data_root.as_ref() {
                    append_desktop_log(Path::new(root), &format!("boot phase: {new_phase}"));
                }
            }
            let _ = app.emit("boot:state", &*state);
        }
    }

    fn fail(&self, app: &AppHandle, phase: BootPhase, code: &str, message: String, detail: Value) {
        self.update(app, |state| {
            state.phase = phase;
            state.error = Some(BootError {
                code: code.to_owned(),
                message,
                detail: Some(detail),
            });
        });
    }

    pub fn state(&self) -> BootState {
        self.0
            .state
            .lock()
            .map(|state| state.clone())
            .unwrap_or_else(|_| BootState::resolving())
    }

    pub fn set_error(&self, app: &AppHandle, code: &str, message: String) {
        let phase = match code {
            "APP_TRANSLOCATED" => BootPhase::Translocated,
            "DATA_ROOT_LOCKED" => BootPhase::LockedByOtherInstance,
            "DATA_ROOT_MISMATCH" | "DATA_ROOT_MISSING" => BootPhase::DataRootError,
            "DATA_ROOT_UNWRITABLE"
            | "DATA_ROOT_NETWORK"
            | "DATA_ROOT_CLOUD_SYNC"
            | "DATA_ROOT_NOT_EMPTY" => BootPhase::NeedsDataRoot,
            _ => BootPhase::StartupFailed,
        };
        let root = self.state().data_root.map(PathBuf::from);
        self.fail(app, phase, code, message, json!({}));
        if let Some(root) = root {
            let path = root.join("logs").join("desktop.log");
            if let Some(parent) = path.parent() {
                let _ = fs::create_dir_all(parent);
            }
            if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(path) {
                if let Some(error) = self.state().error {
                    let _ = writeln!(
                        file,
                        "backend startup error [{}]: {}",
                        error.code, error.message
                    );
                }
            }
        }
    }

    pub fn start(
        &self,
        app: AppHandle,
        data_root: PathBuf,
        marker: DataMarker,
    ) -> Result<(), String> {
        self.update(&app, |state| {
            state.phase = BootPhase::StartingBackend;
            state.data_root = Some(data_root.display().to_string());
            state.data_id = Some(marker.data_id.clone());
            state.error = None;
            state.backend = None;
            state.progress = Some(BootProgress {
                stage: "starting".into(),
            });
        });
        let token = make_token()?;
        if let Ok(mut slot) = self.0.token.lock() {
            *slot = Some(token.clone());
        }
        let mut command = if cfg!(debug_assertions) {
            let repo_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                .parent()
                .and_then(Path::parent)
                .ok_or_else(|| "Cannot locate repository root from desktop manifest".to_owned())?
                .to_path_buf();
            let uv = std::env::var_os("USERPROFILE")
                .map(PathBuf::from)
                .map(|profile| {
                    profile.join(".local").join("bin").join(if cfg!(windows) {
                        "uv.exe"
                    } else {
                        "uv"
                    })
                })
                .filter(|path| path.is_file())
                .unwrap_or_else(|| PathBuf::from("uv"));
            let mut command = Command::new(uv);
            command
                .args(["run", "python", "-m", "writestory_be"])
                .current_dir(repo_root)
                .env("WRITESTORY_DATA_ROOT", &data_root)
                .env("WRITESTORY_DEV_TOKEN", &token)
                .env("WRITESTORY_DEV_PORT", "0");
            command
        } else {
            let resource_dir = app
                .path()
                .resource_dir()
                .map_err(|err| format!("BACKEND_BINARY_MISSING: cannot locate resources: {err}"))?;
            let binary_name = if cfg!(windows) {
                "writestory-backend.exe"
            } else {
                "writestory-backend"
            };
            let executable = [
                resource_dir.join("backend").join(binary_name),
                resource_dir
                    .join("resources")
                    .join("backend")
                    .join(binary_name),
            ]
            .into_iter()
            .find(|path| path.is_file())
            .ok_or_else(|| {
                format!(
                    "BACKEND_BINARY_MISSING: expected {}/backend/{}",
                    resource_dir.display(),
                    binary_name
                )
            })?;
            let mut command = Command::new(executable);
            command.current_dir(&data_root);
            command
        };
        command
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            command.creation_flags(0x08000000); // CREATE_NO_WINDOW
        }
        let mut child = command
            .spawn()
            .map_err(|err| format!("BACKEND_BINARY_MISSING: cannot start uv: {err}"))?;
        let pid = child.id();
        #[cfg(windows)]
        let job = crate::win_job::JobObject::assign(&child).map_err(|err| {
            let _ = child.kill();
            format!("Could not assign backend to Windows Job Object: {err}")
        })?;
        let stdin = child
            .stdin
            .take()
            .ok_or_else(|| "Backend stdin was not piped".to_owned())?;
        let stdout = child
            .stdout
            .take()
            .ok_or_else(|| "Backend stdout was not piped".to_owned())?;
        let stderr = child
            .stderr
            .take()
            .ok_or_else(|| "Backend stderr was not piped".to_owned())?;
        let config = BootstrapConfig {
            protocol_version: PROTOCOL_VERSION,
            token: &token,
            data_root: &data_root,
            data_id: &marker.data_id,
            parent_pid: std::process::id(),
            app_version: env!("CARGO_PKG_VERSION"),
            allowed_origins: [
                "tauri://localhost",
                "http://tauri.localhost",
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            ],
            dev_features: true,
            log_level: "info",
        };
        let mut stdin = stdin;
        let mut config_line = serde_json::to_vec(&config).map_err(|err| err.to_string())?;
        config_line.push(b'\n');
        stdin
            .write_all(&config_line)
            .map_err(|err| format!("Cannot write bootstrap config: {err}"))?;
        self.touch_protocol();
        *self
            .0
            .child
            .lock()
            .map_err(|_| "backend child lock poisoned".to_owned())? = Some(child);
        *self
            .0
            .stdin
            .lock()
            .map_err(|_| "backend stdin lock poisoned".to_owned())? = Some(stdin);
        #[cfg(windows)]
        {
            *self
                .0
                ._job
                .lock()
                .map_err(|_| "backend job lock poisoned".to_owned())? = Some(job);
        }

        let stderr_shared = Arc::clone(&self.0);
        let log_path = data_root.join("logs").join("backend-stderr.log");
        thread::Builder::new()
            .name("backend-stderr".into())
            .spawn(move || drain_stderr(stderr, &log_path, &stderr_shared))
            .map_err(|err| format!("Cannot start stderr reader: {err}"))?;

        let manager = self.clone();
        let app_stdout = app.clone();
        thread::Builder::new().name("backend-protocol".into()).spawn(move || {
            let mut reader = BufReader::new(stdout);
            let mut line = String::new();
            let mut became_ready = false;
            loop {
                line.clear();
                match reader.read_line(&mut line) {
                    Ok(0) => break,
                    Ok(_) => match parse_protocol_line(line.trim()) {
                        ProtocolMessage::Progress(stage) => {
                            manager.touch_protocol();
                            manager.update(&app_stdout, |state| {
                                if matches!(state.phase, BootPhase::StartingBackend) {
                                    state.progress = Some(BootProgress { stage });
                                }
                            })
                        }
                        ProtocolMessage::Ready { port, protocol_version, pid: backend_pid } => {
                            manager.touch_protocol();
                            if !matches!(manager.state().phase, BootPhase::StartingBackend) { break; }
                            if protocol_version != PROTOCOL_VERSION {
                                manager.fail(&app_stdout, BootPhase::ProtocolMismatch, "PROTOCOL_MISMATCH",
                                    format!("Backend protocol {protocol_version} does not match desktop protocol {PROTOCOL_VERSION}"), json!({"protocol_version": protocol_version}));
                                break;
                            }
                            match check_health(port, &token, &marker.data_id) {
                                Ok(()) => {
                                    manager.update(&app_stdout, |state| {
                                        state.phase = BootPhase::Ready;
                                        state.backend = Some(BackendInfo {
                                            base_url: format!("http://127.0.0.1:{port}"),
                                            protocol_version, pid: backend_pid,
                                        });
                                        state.progress = None;
                                        state.error = None;
                                    });
                                    became_ready = true;
                                    break;
                                }
                                Err(err) => manager.fail(&app_stdout, BootPhase::StartupFailed, "BACKEND_NOT_READY", err, json!({"port": port})),
                            }
                        }
                        ProtocolMessage::Fatal { code, message, detail } => {
                            manager.touch_protocol();
                            if !matches!(manager.state().phase, BootPhase::StartingBackend) { break; }
                            let phase = if code == "PROTOCOL_MISMATCH" { BootPhase::ProtocolMismatch } else { BootPhase::StartupFailed };
                            manager.fail(&app_stdout, phase, &code, message, detail);
                            break;
                        }
                        ProtocolMessage::Ignore => {}
                    },
                    Err(err) => {
                        manager.fail(&app_stdout, BootPhase::StartupFailed, "BACKEND_PROTOCOL_ERROR", err.to_string(), json!({}));
                        break;
                    }
                }
            }
            let _ = became_ready;
        }).map_err(|err| format!("Cannot start protocol reader: {err}"))?;

        let manager = self.clone();
        thread::Builder::new()
            .name("backend-watcher".into())
            .spawn(move || manager.watch_child(app, pid))
            .map_err(|err| format!("Cannot start backend watcher: {err}"))?;
        Ok(())
    }

    fn stderr_tail(&self) -> Vec<String> {
        self.0
            .stderr_tail
            .lock()
            .map(|lines| lines.clone())
            .unwrap_or_default()
    }

    fn touch_protocol(&self) {
        if let Ok(mut last) = self.0.last_protocol_at.lock() {
            *last = std::time::Instant::now();
        }
    }

    fn kill_child(&self) {
        if let Ok(mut child) = self.0.child.lock() {
            if let Some(child) = child.as_mut() {
                let _ = child.kill();
            }
        }
    }

    fn watch_child(&self, app: AppHandle, pid: u32) {
        loop {
            if matches!(self.state().phase, BootPhase::StartingBackend)
                && self
                    .0
                    .last_protocol_at
                    .lock()
                    .is_ok_and(|last| last.elapsed() >= READY_TIMEOUT)
            {
                self.fail(
                    &app,
                    BootPhase::StartupFailed,
                    "BACKEND_START_TIMEOUT",
                    "Backend did not report readiness within 60 seconds".into(),
                    json!({"stderr_tail": self.stderr_tail()}),
                );
                self.kill_child();
            }
            let result = match self.0.child.lock() {
                Ok(mut slot) => match slot.as_mut() {
                    Some(child) => Some(child.try_wait()),
                    None => break,
                },
                Err(_) => break,
            };
            match result {
                Some(Ok(Some(status))) => {
                    let state = self.state();
                    if matches!(state.phase, BootPhase::Ready) {
                        self.fail(
                            &app,
                            BootPhase::BackendCrashed,
                            "BACKEND_EXITED",
                            "Backend process exited unexpectedly".into(),
                            json!({"exit_code": status.code(), "stderr_tail": self.stderr_tail()}),
                        );
                    }
                    break;
                }
                Some(Err(err)) => {
                    self.fail(
                        &app,
                        BootPhase::BackendCrashed,
                        "BACKEND_EXITED",
                        err.to_string(),
                        json!({"stderr_tail": self.stderr_tail()}),
                    );
                    break;
                }
                _ => thread::sleep(Duration::from_millis(100)),
            }
        }
        let _ = pid;
    }

    pub fn session(&self) -> Result<BackendSession, String> {
        let state = self.state();
        if !matches!(state.phase, BootPhase::Ready) {
            return Err("BACKEND_NOT_READY".into());
        }
        let backend = state
            .backend
            .ok_or_else(|| "BACKEND_NOT_READY".to_owned())?;
        let token = self
            .0
            .token
            .lock()
            .map_err(|_| "backend token lock poisoned")?
            .clone()
            .ok_or_else(|| "BACKEND_NOT_READY".to_owned())?;
        Ok(BackendSession {
            base_url: backend.base_url,
            token,
            protocol_version: backend.protocol_version,
        })
    }

    pub fn shutdown(&self, app: &AppHandle, reason: &str, wait: Duration) {
        let child_running = self.0.child.lock().ok().is_some_and(|mut child| {
            child
                .as_mut()
                .is_some_and(|process| process.try_wait().ok().flatten().is_none())
        });
        if !child_running {
            return;
        }

        self.update(app, |state| state.phase = BootPhase::ShuttingDown);
        if let Ok(session) = self.session_for_shutdown() {
            let _ = post_shutdown(&session, reason, wait);
        }
        if let Ok(mut child) = self.0.child.lock() {
            let deadline = std::time::Instant::now() + wait;
            while std::time::Instant::now() < deadline {
                if child
                    .as_mut()
                    .and_then(|process| process.try_wait().ok().flatten())
                    .is_some()
                {
                    break;
                }
                thread::sleep(Duration::from_millis(50));
            }
            if child
                .as_mut()
                .is_some_and(|process| process.try_wait().ok().flatten().is_none())
            {
                if let Some(process) = child.as_mut() {
                    let _ = process.kill();
                }
                let kill_deadline = std::time::Instant::now() + Duration::from_secs(2);
                while std::time::Instant::now() < kill_deadline {
                    if child
                        .as_mut()
                        .and_then(|process| process.try_wait().ok().flatten())
                        .is_some()
                    {
                        break;
                    }
                    thread::sleep(Duration::from_millis(50));
                }
            }
            *child = None;
        }
        if let Ok(mut stdin) = self.0.stdin.lock() {
            *stdin = None;
        }
        if let Ok(mut token) = self.0.token.lock() {
            *token = None;
        }
    }

    fn session_for_shutdown(&self) -> Result<BackendSession, String> {
        let state = self.state();
        let backend = state
            .backend
            .ok_or_else(|| "BACKEND_NOT_READY".to_owned())?;
        let token = self
            .0
            .token
            .lock()
            .map_err(|_| "backend token lock poisoned")?
            .clone()
            .ok_or_else(|| "BACKEND_NOT_READY".to_owned())?;
        Ok(BackendSession {
            base_url: backend.base_url,
            token,
            protocol_version: backend.protocol_version,
        })
    }

    pub fn restart(
        &self,
        app: AppHandle,
        data_root: PathBuf,
        marker: DataMarker,
    ) -> Result<BootState, String> {
        self.shutdown(&app, "restart", Duration::from_secs(5));
        let restart_count = self.state().restart_count.saturating_add(1);
        if let Ok(mut state) = self.0.state.lock() {
            state.restart_count = restart_count;
        }
        self.start(app, data_root, marker)?;
        Ok(self.state())
    }
}

impl Clone for BackendManager {
    fn clone(&self) -> Self {
        Self(Arc::clone(&self.0))
    }
}

fn make_token() -> Result<String, String> {
    let mut bytes = [0u8; 32];
    getrandom::fill(&mut bytes)
        .map_err(|err| format!("Secure random token generation failed: {err}"))?;
    Ok(URL_SAFE_NO_PAD.encode(bytes))
}

fn drain_stderr(stderr: impl Read, log_path: &Path, shared: &Shared) {
    if let Some(parent) = log_path.parent() {
        let _ = fs::create_dir_all(parent);
    }
    let mut log = OpenOptions::new()
        .create(true)
        .append(true)
        .open(log_path)
        .ok();
    let mut reader = BufReader::new(stderr);
    let mut line = String::new();
    loop {
        line.clear();
        match reader.read_line(&mut line) {
            Ok(0) | Err(_) => break,
            Ok(_) => {
                let clean = line.trim_end().to_owned();
                if let Some(file) = log.as_mut() {
                    let _ = writeln!(file, "{clean}");
                }
                if let Ok(mut tail) = shared.stderr_tail.lock() {
                    tail.push(clean);
                    if tail.len() > STDERR_TAIL_LINES {
                        tail.remove(0);
                    }
                }
            }
        }
    }
}

fn append_desktop_log(data_root: &Path, line: &str) {
    let path = data_root.join("logs").join("desktop.log");
    if let Some(parent) = path.parent() {
        let _ = fs::create_dir_all(parent);
    }
    if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(path) {
        let _ = writeln!(file, "{line}");
    }
}

fn check_health(port: u16, token: &str, data_id: &str) -> Result<(), String> {
    let addr = ("127.0.0.1", port)
        .to_socket_addrs()
        .map_err(|err| err.to_string())?
        .next()
        .ok_or_else(|| "Could not resolve backend loopback address".to_owned())?;
    let mut last_error = "Health check failed".to_owned();
    for _ in 0..3 {
        let result = (|| {
            let mut stream = TcpStream::connect_timeout(&addr, HEALTH_TIMEOUT)?;
            stream.set_read_timeout(Some(HEALTH_TIMEOUT))?;
            stream.set_write_timeout(Some(HEALTH_TIMEOUT))?;
            write!(stream, "GET /v1/health HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nAuthorization: Bearer {token}\r\nConnection: close\r\n\r\n")?;
            let mut response = String::new();
            stream.read_to_string(&mut response)?;
            let (headers, body) = response
                .split_once("\r\n\r\n")
                .ok_or_else(|| std::io::Error::other("Malformed HTTP health response"))?;
            if !headers
                .lines()
                .next()
                .is_some_and(|line| line.contains(" 200 "))
            {
                return Err(std::io::Error::other(
                    "Health endpoint did not return HTTP 200",
                ));
            }
            let health: HealthResponse =
                serde_json::from_str(body).map_err(std::io::Error::other)?;
            if health.status != "ok"
                || health.protocol_version != PROTOCOL_VERSION
                || health.data_id.as_deref() != Some(data_id)
            {
                return Err(std::io::Error::other(
                    "Health response contract did not match bootstrap config",
                ));
            }
            Ok::<(), std::io::Error>(())
        })();
        match result {
            Ok(()) => return Ok(()),
            Err(err) => {
                last_error = err.to_string();
                thread::sleep(Duration::from_millis(250));
            }
        }
    }
    Err(last_error)
}

fn post_shutdown(session: &BackendSession, reason: &str, wait: Duration) -> Result<(), String> {
    let port = session
        .base_url
        .rsplit_once(':')
        .and_then(|(_, port)| port.parse::<u16>().ok())
        .ok_or_else(|| "Invalid backend URL".to_owned())?;
    let address = ("127.0.0.1", port)
        .to_socket_addrs()
        .map_err(|err| err.to_string())?
        .next()
        .ok_or_else(|| "Could not resolve backend loopback address".to_owned())?;
    let timeout = wait.min(Duration::from_secs(2));
    let mut stream =
        TcpStream::connect_timeout(&address, timeout).map_err(|err| err.to_string())?;
    stream
        .set_read_timeout(Some(timeout))
        .map_err(|err| err.to_string())?;
    stream
        .set_write_timeout(Some(timeout))
        .map_err(|err| err.to_string())?;
    let body =
        json!({"reason": reason, "deadline_ms": wait.as_millis().min(u64::MAX as u128) as u64})
            .to_string();
    write!(stream,
        "POST /v1/system/shutdown HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nAuthorization: Bearer {}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
        session.token, body.len(), body
    ).map_err(|err| err.to_string())?;
    let mut response = String::new();
    stream
        .read_to_string(&mut response)
        .map_err(|err| err.to_string())?;
    if response
        .lines()
        .next()
        .is_some_and(|line| line.contains(" 202 "))
    {
        Ok(())
    } else {
        Err("Backend did not accept shutdown request".into())
    }
}

#[cfg(test)]
mod tests {
    use super::{parse_protocol_line, ProtocolMessage};

    #[test]
    fn parses_ready_message() {
        assert_eq!(
            parse_protocol_line(r#"{"event":"ready","port":3456,"protocol_version":1,"pid":42}"#),
            ProtocolMessage::Ready {
                port: 3456,
                protocol_version: 1,
                pid: 42
            }
        );
    }

    #[test]
    fn parses_progress_message() {
        assert_eq!(
            parse_protocol_line(r#"{"event":"progress","stage":"migrating"}"#),
            ProtocolMessage::Progress("migrating".into())
        );
    }

    #[test]
    fn parses_fatal_message() {
        assert_eq!(
            parse_protocol_line(
                r#"{"event":"fatal","code":"DB_MISSING","message":"missing","detail":{"path":"db"}}"#
            ),
            ProtocolMessage::Fatal {
                code: "DB_MISSING".into(),
                message: "missing".into(),
                detail: serde_json::json!({"path":"db"})
            }
        );
    }

    #[test]
    fn ignores_non_protocol_and_invalid_lines() {
        assert_eq!(
            parse_protocol_line("library stdout noise"),
            ProtocolMessage::Ignore
        );
        assert_eq!(
            parse_protocol_line(r#"{"event":"ready","port":"bad"}"#),
            ProtocolMessage::Ignore
        );
    }
}
