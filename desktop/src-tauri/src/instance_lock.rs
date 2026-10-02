use std::{
    fs::{self, File},
    path::Path,
};

use fs4::fs_std::FileExt;

#[derive(Debug)]
pub struct InstanceLock {
    _file: File,
}

impl InstanceLock {
    pub fn acquire(data_root: &Path) -> std::io::Result<Self> {
        let lock_path = data_root.join(".instance.lock");
        if let Some(parent) = lock_path.parent() {
            fs::create_dir_all(parent)?;
        }
        let file = File::options()
            .create(true)
            .truncate(false)
            .read(true)
            .write(true)
            .open(lock_path)?;
        if !file.try_lock_exclusive()? {
            return Err(std::io::Error::from(std::io::ErrorKind::WouldBlock));
        }
        Ok(Self { _file: file })
    }
}

#[cfg(test)]
mod tests {
    use super::InstanceLock;
    use std::{path::Path, process::Command};

    #[test]
    fn lock_is_exclusive_and_released_when_dropped() {
        let temp = tempfile::tempdir().expect("temporary directory");
        let first = InstanceLock::acquire(temp.path()).expect("first lock");
        run_lock_probe(temp.path(), "held");
        drop(first);
        run_lock_probe(temp.path(), "free");
    }

    #[test]
    fn lock_probe() {
        let Ok(root) = std::env::var("WRITESTORY_LOCK_PROBE_ROOT") else {
            return;
        };
        match std::env::var("WRITESTORY_LOCK_PROBE_MODE").as_deref() {
            Ok("held") => assert!(InstanceLock::acquire(Path::new(&root)).is_err()),
            Ok("free") => assert!(InstanceLock::acquire(Path::new(&root)).is_ok()),
            _ => panic!("missing lock probe mode"),
        }
    }

    fn run_lock_probe(root: &std::path::Path, mode: &str) {
        let output = Command::new(std::env::current_exe().expect("test executable"))
            .args(["--exact", "instance_lock::tests::lock_probe"])
            .env("WRITESTORY_LOCK_PROBE_ROOT", root)
            .env("WRITESTORY_LOCK_PROBE_MODE", mode)
            .output()
            .expect("spawn lock probe");
        assert!(
            output.status.success(),
            "lock probe failed ({}): stdout={} stderr={}",
            output.status,
            String::from_utf8_lossy(&output.stdout),
            String::from_utf8_lossy(&output.stderr),
        );
    }
}
