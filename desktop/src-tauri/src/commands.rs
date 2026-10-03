use std::{
    path::PathBuf,
    process::Command,
    sync::{atomic::AtomicBool, Mutex},
};

use tauri::{AppHandle, State};
use tauri_plugin_dialog::DialogExt;

use crate::{
    backend::{BackendManager, BackendSession},
    boot_state::BootState,
    data_root::{self, ResolveOptions, ResolvedDataRoot},
};

#[derive(Default)]
pub struct DataRootState(pub Mutex<Option<ResolvedDataRoot>>);

#[derive(Default)]
pub struct ExitGuard(pub AtomicBool);

#[tauri::command]
pub fn get_boot_state(backend: State<'_, BackendManager>) -> BootState {
    backend.state()
}

#[tauri::command]
pub fn pick_data_root_folder(app: AppHandle) -> Option<PathBuf> {
    app.dialog()
        .file()
        .set_title("Chọn thư mục dữ liệu WriteStoryApp")
        .blocking_pick_folder()
        .and_then(|path| path.into_path().ok())
}

#[tauri::command(rename_all = "snake_case")]
pub fn confirm_data_root(
    app: AppHandle,
    backend: State<'_, BackendManager>,
    current: State<'_, DataRootState>,
    options: State<'_, ResolveOptions>,
    path: String,
    accept_cloud_sync_warning: Option<bool>,
) -> Result<BootState, String> {
    let mut options = options.inner().clone();
    options.dev_data_root = Some(PathBuf::from(path));
    options.allow_cloud_sync = accept_cloud_sync_warning.unwrap_or(false);
    match data_root::resolve(&options) {
        Ok(resolved) => {
            let root = resolved.path.clone();
            let marker = resolved.marker.clone();
            *current
                .0
                .lock()
                .map_err(|_| "data-root state lock poisoned")? = Some(resolved);
            if let Err(err) = backend.start(app.clone(), root, marker) {
                backend.set_error(&app, "BACKEND_START_FAILED", err);
            }
            Ok(backend.state())
        }
        Err(err) => {
            backend.set_error(&app, err.code, err.to_string());
            Err(err.to_string())
        }
    }
}

#[tauri::command]
pub fn get_backend_session(backend: State<'_, BackendManager>) -> Result<BackendSession, String> {
    backend.session()
}

#[tauri::command]
pub fn restart_backend(
    app: AppHandle,
    backend: State<'_, BackendManager>,
    current: State<'_, DataRootState>,
) -> Result<BootState, String> {
    let root = current
        .0
        .lock()
        .map_err(|_| "data-root state lock poisoned")?;
    let resolved = root
        .as_ref()
        .ok_or_else(|| "BACKEND_NOT_READY".to_owned())?;
    backend.restart(app, resolved.path.clone(), resolved.marker.clone())
}

#[tauri::command]
pub fn open_logs_folder(current: State<'_, DataRootState>) -> Result<(), String> {
    let root = current
        .0
        .lock()
        .map_err(|_| "data-root state lock poisoned")?;
    let resolved = root
        .as_ref()
        .ok_or_else(|| "BACKEND_NOT_READY".to_owned())?;
    let logs = resolved.path.join("logs");
    std::fs::create_dir_all(&logs).map_err(|err| err.to_string())?;
    #[cfg(target_os = "windows")]
    let mut command = {
        let mut command = Command::new("explorer.exe");
        command.arg(&logs);
        command
    };
    #[cfg(target_os = "macos")]
    let mut command = {
        let mut command = Command::new("open");
        command.arg(&logs);
        command
    };
    #[cfg(all(not(target_os = "windows"), not(target_os = "macos")))]
    let mut command = {
        let mut command = Command::new("xdg-open");
        command.arg(&logs);
        command
    };
    command.spawn().map(|_| ()).map_err(|err| err.to_string())
}

#[tauri::command]
pub fn quit_app(app: AppHandle) {
    app.exit(0);
}
