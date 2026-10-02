use std::{
    env, fs,
    io::Write,
    path::{Path, PathBuf},
};

use serde::{Deserialize, Serialize};
use time::{format_description::well_known::Rfc3339, OffsetDateTime};
use uuid::Uuid;

use crate::instance_lock::InstanceLock;

const MARKER: &str = ".writestory-data.json";
const POINTER: &str = "data-root.json";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Platform {
    Windows,
    MacOs,
    Other,
}

#[derive(Clone, Debug)]
pub struct ResolveOptions {
    pub platform: Platform,
    pub executable: PathBuf,
    pub app_data: Option<PathBuf>,
    pub home: Option<PathBuf>,
    pub debug: bool,
    pub dev_data_root: Option<PathBuf>,
    pub allow_cloud_sync: bool,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct DataMarker {
    pub data_id: String,
    pub layout_version: u32,
    pub created_at: String,
    pub created_by_app_version: String,
    pub db_initialized: bool,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct DataRootPointer {
    pub version: u32,
    pub data_root: PathBuf,
    pub data_id: String,
    pub chosen_at: String,
}

#[derive(Debug)]
pub struct ResolvedDataRoot {
    pub path: PathBuf,
    pub marker: DataMarker,
    pub lock: InstanceLock,
}

#[derive(Debug)]
pub struct DataRootError {
    pub code: &'static str,
    pub message: String,
}

impl std::fmt::Display for DataRootError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(formatter, "{}: {}", self.code, self.message)
    }
}

impl std::error::Error for DataRootError {}

fn error(code: &'static str, message: impl Into<String>) -> DataRootError {
    DataRootError {
        code,
        message: message.into(),
    }
}

fn now_rfc3339() -> Result<String, DataRootError> {
    OffsetDateTime::now_utc()
        .format(&Rfc3339)
        .map_err(|err| error("DATA_ROOT_ERROR", err.to_string()))
}

fn pointer_path(options: &ResolveOptions) -> Option<PathBuf> {
    match options.platform {
        Platform::Windows => options
            .app_data
            .as_ref()
            .map(|path| path.join("WriteStoryApp").join(POINTER)),
        Platform::MacOs => options.home.as_ref().map(|path| {
            path.join("Library")
                .join("Application Support")
                .join("WriteStoryApp")
                .join(POINTER)
        }),
        Platform::Other => None,
    }
}

fn read_pointer(path: &Path) -> Result<Option<DataRootPointer>, DataRootError> {
    if !path.exists() {
        return Ok(None);
    }
    let bytes = fs::read(path).map_err(|err| error("DATA_ROOT_ERROR", err.to_string()))?;
    serde_json::from_slice(&bytes).map(Some).map_err(|err| {
        error(
            "DATA_ROOT_ERROR",
            format!("Invalid data-root pointer: {err}"),
        )
    })
}

fn from_mac_bundle_path(executable: &Path) -> Option<PathBuf> {
    executable
        .ancestors()
        .find(|part| part.extension().is_some_and(|extension| extension == "app"))
        .map(|app| app.join("data"))
}

pub fn is_cloud_sync(path: &Path) -> bool {
    let normalized = path.to_string_lossy().replace('\\', "/").to_lowercase();
    normalized.contains("/library/mobile documents/")
        || normalized.contains("/library/cloudstorage/")
        || env::var_os("ONEDRIVE")
            .map(PathBuf::from)
            .is_some_and(|root| path.starts_with(root))
}

fn is_network_path(path: &Path, platform: Platform) -> bool {
    if platform == Platform::Windows {
        let value = path.to_string_lossy();
        if value.starts_with("\\\\") {
            return true;
        }
        #[cfg(windows)]
        {
            use windows_sys::Win32::Storage::FileSystem::GetDriveTypeW;
            let prefix = path
                .components()
                .next()
                .map(|component| component.as_os_str());
            if let Some(prefix) = prefix {
                let mut root: Vec<u16> = prefix.to_string_lossy().encode_utf16().collect();
                if root.len() == 2 && root[1] == b':' as u16 {
                    root.push(b'\\' as u16);
                }
                root.push(0);
                const DRIVE_REMOTE: u32 = 4;
                return unsafe { GetDriveTypeW(root.as_ptr()) } == DRIVE_REMOTE;
            }
        }
        return false;
    }

    #[cfg(target_os = "macos")]
    {
        use std::ffi::CString;

        // The selected directory may not exist yet. statfs the nearest existing
        // ancestor so a new subdirectory on an SMB/NFS mount is still rejected.
        let existing = path.ancestors().find(|candidate| candidate.exists());
        if let Some(existing) = existing {
            if let Ok(path) = CString::new(existing.as_os_str().as_encoded_bytes()) {
                let mut info = std::mem::MaybeUninit::<libc::statfs>::uninit();
                let result = unsafe { libc::statfs(path.as_ptr(), info.as_mut_ptr()) };
                if result == 0 {
                    let info = unsafe { info.assume_init() };
                    return info.f_flags & libc::MNT_LOCAL as u32 == 0;
                }
            }
        }
    }
    false
}

fn ensure_writable(path: &Path) -> Result<(), DataRootError> {
    fs::create_dir_all(path).map_err(|err| error("DATA_ROOT_UNWRITABLE", err.to_string()))?;
    let nonce = Uuid::now_v7();
    let temp = path.join(format!(".write-test-{nonce}"));
    let renamed = path.join(format!(".write-test-{nonce}.renamed"));
    let result = (|| {
        let mut file = fs::File::create(&temp)?;
        file.write_all(b"writestory")?;
        file.sync_all()?;
        fs::rename(&temp, &renamed)?;
        fs::remove_file(&renamed)
    })();
    result.map_err(|err| error("DATA_ROOT_UNWRITABLE", err.to_string()))
}

fn make_marker(path: &Path) -> Result<DataMarker, DataRootError> {
    let marker_path = path.join(MARKER);
    if marker_path.exists() {
        let bytes =
            fs::read(&marker_path).map_err(|err| error("DATA_ROOT_ERROR", err.to_string()))?;
        return serde_json::from_slice(&bytes)
            .map_err(|err| error("DATA_ROOT_ERROR", format!("Invalid data marker: {err}")));
    }
    let mut entries =
        fs::read_dir(path).map_err(|err| error("DATA_ROOT_ERROR", err.to_string()))?;
    if entries.next().is_some() {
        return Err(error(
            "DATA_ROOT_NOT_EMPTY",
            "Choose an empty folder or an existing WriteStoryApp data folder.",
        ));
    }
    let marker = DataMarker {
        data_id: Uuid::now_v7().to_string(),
        layout_version: 1,
        created_at: now_rfc3339()?,
        created_by_app_version: env!("CARGO_PKG_VERSION").into(),
        db_initialized: false,
    };
    let bytes = serde_json::to_vec_pretty(&marker)
        .map_err(|err| error("DATA_ROOT_ERROR", err.to_string()))?;
    write_atomic(&marker_path, &bytes)?;
    Ok(marker)
}

fn write_atomic(path: &Path, bytes: &[u8]) -> Result<(), DataRootError> {
    let parent = path
        .parent()
        .ok_or_else(|| error("DATA_ROOT_ERROR", "Path has no parent."))?;
    fs::create_dir_all(parent).map_err(|err| error("DATA_ROOT_ERROR", err.to_string()))?;
    let temp = parent.join(format!(
        ".{}.{}.tmp",
        path.file_name().unwrap_or_default().to_string_lossy(),
        Uuid::now_v7()
    ));
    let mut file =
        fs::File::create(&temp).map_err(|err| error("DATA_ROOT_ERROR", err.to_string()))?;
    file.write_all(bytes)
        .map_err(|err| error("DATA_ROOT_ERROR", err.to_string()))?;
    file.sync_all()
        .map_err(|err| error("DATA_ROOT_ERROR", err.to_string()))?;
    fs::rename(&temp, path).map_err(|err| error("DATA_ROOT_ERROR", err.to_string()))
}

fn write_pointer(path: &Path, data_root: &Path, data_id: &str) -> Result<(), DataRootError> {
    let pointer = DataRootPointer {
        version: 1,
        data_root: data_root.to_path_buf(),
        data_id: data_id.to_owned(),
        chosen_at: now_rfc3339()?,
    };
    let bytes = serde_json::to_vec_pretty(&pointer)
        .map_err(|err| error("DATA_ROOT_ERROR", err.to_string()))?;
    write_atomic(path, &bytes)
}

fn choose_candidate(
    options: &ResolveOptions,
) -> Result<(PathBuf, bool, Option<String>), DataRootError> {
    if options.debug {
        if let Some(path) = options
            .dev_data_root
            .clone()
            .or_else(|| env::var_os("WRITESTORY_DATA_ROOT").map(PathBuf::from))
        {
            return Ok((path, false, None));
        }
    }
    if options.platform == Platform::MacOs
        && options
            .executable
            .to_string_lossy()
            .contains("/AppTranslocation/")
    {
        return Err(error(
            "APP_TRANSLOCATED",
            "Move WriteStoryApp to /Applications before opening it.",
        ));
    }

    if options.platform == Platform::Windows {
        let beside_exe = options
            .executable
            .parent()
            .unwrap_or(Path::new("."))
            .join("data");
        if ensure_writable(&beside_exe).is_ok() {
            return Ok((beside_exe, false, None));
        }
    }

    let pointer_file = pointer_path(options);
    let pointer = pointer_file
        .as_deref()
        .map(read_pointer)
        .transpose()?
        .flatten();
    if let Some(pointer) = pointer {
        if !pointer.data_root.exists() {
            return Err(error(
                "DATA_ROOT_MISSING",
                "The saved data folder is unavailable.",
            ));
        }
        return Ok((pointer.data_root, false, Some(pointer.data_id)));
    }
    match options.platform {
        Platform::Windows => Err(error(
            "DATA_ROOT_UNWRITABLE",
            "The application folder is not writable. Choose another data folder.",
        )),
        Platform::MacOs => {
            if let Some(path) = from_mac_bundle_path(&options.executable) {
                if ensure_writable(&path).is_ok() {
                    return Ok((path, false, None));
                }
            }
            let fallback = options
                .home
                .as_ref()
                .map(|home| home.join("Library/Application Support/WriteStoryApp/data"))
                .ok_or_else(|| error("DATA_ROOT_UNWRITABLE", "No home directory is available."))?;
            Ok((fallback, true, None))
        }
        Platform::Other => Ok((
            options
                .executable
                .parent()
                .unwrap_or(Path::new("."))
                .join("data"),
            false,
            None,
        )),
    }
}

pub fn resolve(options: &ResolveOptions) -> Result<ResolvedDataRoot, DataRootError> {
    let (path, needs_pointer, pointer_data_id) = choose_candidate(options)?;
    if !path.is_absolute() {
        return Err(error(
            "DATA_ROOT_UNWRITABLE",
            "The data folder path must be absolute.",
        ));
    }
    if is_network_path(&path, options.platform) {
        return Err(error(
            "DATA_ROOT_NETWORK",
            "Network drives are not supported for active data.",
        ));
    }
    if is_cloud_sync(&path) && !options.allow_cloud_sync {
        return Err(error(
            "DATA_ROOT_CLOUD_SYNC",
            "Cloud-synced folders can corrupt active data.",
        ));
    }
    ensure_writable(&path)?;
    let marker = make_marker(&path)?;
    if pointer_data_id
        .as_ref()
        .is_some_and(|data_id| data_id != &marker.data_id)
    {
        return Err(error(
            "DATA_ROOT_MISMATCH",
            "The selected data folder does not match its saved pointer.",
        ));
    }
    if needs_pointer {
        if let Some(pointer) = pointer_path(options) {
            write_pointer(&pointer, &path, &marker.data_id)?;
        }
    }
    let lock =
        InstanceLock::acquire(&path).map_err(|err| error("DATA_ROOT_LOCKED", err.to_string()))?;
    for directory in [
        "db", "assets", "imports", "exports", "backups", "logs", "cache", "tmp",
    ] {
        fs::create_dir_all(path.join(directory))
            .map_err(|err| error("DATA_ROOT_UNWRITABLE", err.to_string()))?;
    }
    Ok(ResolvedDataRoot { path, marker, lock })
}

#[cfg(test)]
mod tests {
    use super::{is_cloud_sync, is_network_path, resolve, Platform, ResolveOptions};
    use std::path::PathBuf;

    fn options(temp: &tempfile::TempDir, platform: Platform) -> ResolveOptions {
        ResolveOptions {
            platform,
            executable: temp.path().join("WriteStoryApp.exe"),
            app_data: Some(temp.path().join("appdata")),
            home: Some(temp.path().join("home")),
            debug: false,
            dev_data_root: None,
            allow_cloud_sync: false,
        }
    }

    #[test]
    fn creates_marker_and_directories_in_writable_root() {
        let temp = tempfile::tempdir().unwrap();
        let mut config = options(&temp, Platform::Windows);
        config.executable = temp.path().join("app").join("WriteStoryApp.exe");
        let root = resolve(&config).unwrap();
        assert!(root.path.join(".writestory-data.json").is_file());
        assert!(root.path.join("db").is_dir());
    }

    #[test]
    fn rejects_nonempty_directory_without_marker() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path().join("chosen");
        std::fs::create_dir_all(&root).unwrap();
        std::fs::write(root.join("keep.txt"), "data").unwrap();
        let config = ResolveOptions {
            platform: Platform::Other,
            executable: root.join("app"),
            app_data: None,
            home: None,
            debug: true,
            dev_data_root: Some(root.clone()),
            allow_cloud_sync: false,
        };
        assert_eq!(resolve(&config).unwrap_err().code, "DATA_ROOT_NOT_EMPTY");
    }

    #[test]
    fn rejects_network_and_cloud_paths() {
        assert!(is_network_path(
            PathBuf::from(r"\\server\share\data").as_path(),
            Platform::Windows
        ));
        assert!(!is_network_path(
            PathBuf::from(r"C:\data").as_path(),
            Platform::Windows
        ));
        assert!(is_cloud_sync(
            PathBuf::from("/Users/test/Library/CloudStorage/Drive/data").as_path()
        ));
    }

    #[test]
    fn rejects_translocated_macos_executable() {
        let temp = tempfile::tempdir().unwrap();
        let mut config = options(&temp, Platform::MacOs);
        config.executable =
            PathBuf::from("/AppTranslocation/ABC/d/WriteStoryApp.app/Contents/MacOS/app");
        assert_eq!(resolve(&config).unwrap_err().code, "APP_TRANSLOCATED");
    }

    #[test]
    fn rejects_unwritable_root() {
        let temp = tempfile::tempdir().unwrap();
        let blocker = temp.path().join("not-a-directory");
        std::fs::write(&blocker, "file").unwrap();
        let config = ResolveOptions {
            platform: Platform::Other,
            executable: temp.path().join("app"),
            app_data: None,
            home: None,
            debug: true,
            dev_data_root: Some(blocker.join("data")),
            allow_cloud_sync: false,
        };
        assert_eq!(resolve(&config).unwrap_err().code, "DATA_ROOT_UNWRITABLE");
    }

    #[test]
    fn rejects_pointer_and_marker_data_id_mismatch() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path().join("chosen");
        std::fs::create_dir_all(&root).unwrap();
        std::fs::write(
            root.join(".writestory-data.json"),
            r#"{"data_id":"marker-id","layout_version":1,"created_at":"2026-01-01T00:00:00Z","created_by_app_version":"0.1.0","db_initialized":false}"#,
        )
        .unwrap();
        let pointer_path = temp
            .path()
            .join("appdata")
            .join("WriteStoryApp")
            .join("data-root.json");
        std::fs::create_dir_all(pointer_path.parent().unwrap()).unwrap();
        std::fs::write(
            &pointer_path,
            serde_json::json!({
                "version": 1,
                "data_root": root,
                "data_id": "pointer-id",
                "chosen_at": "2026-01-01T00:00:00Z"
            })
            .to_string(),
        )
        .unwrap();
        std::fs::write(temp.path().join("install"), "not a directory").unwrap();
        let config = ResolveOptions {
            platform: Platform::Windows,
            executable: temp.path().join("install").join("WriteStoryApp.exe"),
            app_data: Some(temp.path().join("appdata")),
            home: None,
            debug: false,
            dev_data_root: None,
            allow_cloud_sync: false,
        };
        assert_eq!(resolve(&config).unwrap_err().code, "DATA_ROOT_MISMATCH");
    }
}
