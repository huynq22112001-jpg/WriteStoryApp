use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Emitter};

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum BootPhase {
    ResolvingDataRoot,
    NeedsDataRoot,
    Translocated,
    DataRootError,
    LockedByOtherInstance,
    StartingBackend,
    Ready,
    BackendCrashed,
    StartupFailed,
    ProtocolMismatch,
    ShuttingDown,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct BootError {
    pub code: String,
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub detail: Option<serde_json::Value>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct BootProgress {
    pub stage: String,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct BackendInfo {
    pub base_url: String,
    pub protocol_version: u32,
    pub pid: u32,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct BootState {
    pub phase: BootPhase,
    pub platform: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data_root: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<BootError>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub backend: Option<BackendInfo>,
    pub restart_count: u32,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub progress: Option<BootProgress>,
}

impl BootState {
    pub fn resolving() -> Self {
        Self {
            phase: BootPhase::ResolvingDataRoot,
            platform: std::env::consts::OS.into(),
            data_root: None,
            data_id: None,
            error: None,
            backend: None,
            restart_count: 0,
            progress: None,
        }
    }

    pub fn emit(&self, app: &AppHandle) {
        let _ = app.emit("boot:state", self);
    }
}
