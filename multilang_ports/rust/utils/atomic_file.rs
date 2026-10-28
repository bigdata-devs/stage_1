use std::fs::{self, File, OpenOptions};
use std::io::{self, Write};
use std::os::unix::fs::OpenOptionsExt;
use std::path::Path;
use std::sync::atomic::{AtomicU64, Ordering};

static TEMPORARY_SEQUENCE: AtomicU64 = AtomicU64::new(0);
const FILE_MODE: u32 = 0o644;

/// Writes UTF-8 text through a temporary sibling that is fsync-ed and then
/// renamed into place, exactly like `write_text_atomically()` in the Python
/// baseline: a reader sees either the old file or the complete new one.
pub fn write_text(path: &Path, content: &str) -> io::Result<()> {
    write(path, |file| file.write_all(content.as_bytes()))
}

/// Produces the file through the caller's writer, forces it to stable storage
/// and only then swaps it in with a rename. The temporary file starts with a
/// dot and ends in `.tmp`, so datalake and index globs never mistake it for a
/// real book or term file.
pub fn write(path: &Path, produce: impl FnOnce(&mut File) -> io::Result<()>) -> io::Result<()> {
    let directory = parent_directory(path);
    fs::create_dir_all(directory)?;
    let temporary = directory.join(temporary_name(path));
    let produced = produce_temporary(&temporary, produce);
    if let Err(error) = produced {
        return Err(error);
    }
    if let Err(error) = fs::rename(&temporary, path) {
        let _ = fs::remove_file(&temporary);
        return Err(error);
    }
    Ok(())
}

fn produce_temporary(
    temporary: &Path,
    produce: impl FnOnce(&mut File) -> io::Result<()>,
) -> io::Result<()> {
    let mut file = open_temporary(temporary)?;
    let result = produce(&mut file).and_then(|()| file.sync_all());
    drop(file);
    if result.is_err() {
        let _ = fs::remove_file(temporary);
    }
    result
}

fn open_temporary(temporary: &Path) -> io::Result<File> {
    OpenOptions::new()
        .write(true)
        .create_new(true)
        .mode(FILE_MODE)
        .open(temporary)
}

fn parent_directory(path: &Path) -> &Path {
    match path.parent() {
        Some(parent) if !parent.as_os_str().is_empty() => parent,
        _ => Path::new("."),
    }
}

fn temporary_name(path: &Path) -> String {
    let file_name = path.file_name().unwrap_or_default().to_string_lossy();
    let sequence = TEMPORARY_SEQUENCE.fetch_add(1, Ordering::Relaxed);
    format!(".{file_name}.{}.{sequence}.tmp", std::process::id())
}
