use std::time::Duration;
use tauri::Manager;

mod backend;
mod boot_state;
mod commands;
mod data_root;
mod instance_lock;
#[cfg(windows)]
mod win_job;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.unminimize();
                let _ = window.set_focus();
            }
        }))
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            commands::get_boot_state,
            commands::pick_data_root_folder,
            commands::confirm_data_root,
            commands::get_backend_session,
            commands::restart_backend,
            commands::open_logs_folder,
            commands::quit_app,
        ])
        .setup(|app| {
            let manager = backend::BackendManager::new();
            app.manage(manager.clone());
            app.manage(commands::DataRootState::default());
            app.manage(commands::ExitGuard::default());
            let repo_root = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                .parent()
                .and_then(std::path::Path::parent)
                .expect("desktop manifest must be inside the repository")
                .to_path_buf();
            let executable =
                std::env::current_exe().unwrap_or_else(|_| repo_root.join("WriteStoryApp"));
            let data_root = std::env::var_os("WRITESTORY_DATA_ROOT")
                .map(std::path::PathBuf::from)
                .unwrap_or_else(|| repo_root.join("data"));
            let options = data_root::ResolveOptions {
                platform: match std::env::consts::OS {
                    "windows" => data_root::Platform::Windows,
                    "macos" => data_root::Platform::MacOs,
                    _ => data_root::Platform::Other,
                },
                executable,
                app_data: app.path().app_data_dir().ok(),
                home: std::env::var_os("USERPROFILE")
                    .or_else(|| std::env::var_os("HOME"))
                    .map(std::path::PathBuf::from),
                debug: cfg!(debug_assertions),
                dev_data_root: Some(data_root),
                allow_cloud_sync: false,
            };
            app.manage(options.clone());
            let app_handle = app.handle().clone();
            match data_root::resolve(&options) {
                Ok(resolved) => {
                    let root = resolved.path.clone();
                    let marker = resolved.marker.clone();
                    // Keep the lock alive for the full desktop process lifetime.
                    if let Ok(mut current) = app.state::<commands::DataRootState>().0.lock() {
                        *current = Some(resolved);
                    }
                    if let Err(err) = manager.start(app_handle.clone(), root, marker) {
                        manager.set_error(&app_handle, "BACKEND_START_FAILED", err);
                    }
                }
                Err(err) => manager.set_error(&app_handle, err.code, err.to_string()),
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("failed to build WriteStoryApp")
        .run(|app, event| match event {
            tauri::RunEvent::ExitRequested { api, .. } => {
                let guard = app.state::<commands::ExitGuard>();
                if !guard.0.swap(true, std::sync::atomic::Ordering::SeqCst) {
                    api.prevent_exit();
                    let backend = app.state::<backend::BackendManager>();
                    backend.shutdown(app, "app_exit", Duration::from_secs(7));
                    app.exit(0);
                }
            }
            tauri::RunEvent::Exit => {
                let backend = app.state::<backend::BackendManager>();
                backend.shutdown(app, "app_exit", Duration::from_secs(1));
            }
            _ => {}
        });
}
