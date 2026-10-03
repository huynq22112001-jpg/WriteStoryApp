//! Windows Job Object that terminates the backend process tree when the app exits.

use std::{io, mem::zeroed, process::Child};
use windows_sys::Win32::{
    Foundation::CloseHandle,
    System::{
        JobObjects::{
            AssignProcessToJobObject, CreateJobObjectW, JobObjectExtendedLimitInformation,
            SetInformationJobObject, JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
            JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
        },
        Threading::OpenProcess,
    },
};

pub struct JobObject(isize);

impl JobObject {
    pub fn assign(child: &Child) -> io::Result<Self> {
        unsafe {
            let handle = CreateJobObjectW(std::ptr::null(), std::ptr::null());
            if handle.is_null() {
                return Err(io::Error::last_os_error());
            }
            let job = Self(handle as isize);
            let mut limits: JOBOBJECT_EXTENDED_LIMIT_INFORMATION = zeroed();
            limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
            if SetInformationJobObject(
                handle,
                JobObjectExtendedLimitInformation,
                &limits as *const _ as *const _,
                std::mem::size_of_val(&limits) as u32,
            ) == 0
            {
                return Err(io::Error::last_os_error());
            }
            // AssignProcessToJobObject requires PROCESS_SET_QUOTA and PROCESS_TERMINATE.
            let process = OpenProcess(0x0100 | 0x0001, 0, child.id());
            if process.is_null() {
                return Err(io::Error::last_os_error());
            }
            let assigned = AssignProcessToJobObject(handle, process);
            CloseHandle(process);
            if assigned == 0 {
                return Err(io::Error::last_os_error());
            }
            Ok(job)
        }
    }
}

impl Drop for JobObject {
    fn drop(&mut self) {
        unsafe {
            CloseHandle(self.0 as _);
        }
    }
}
