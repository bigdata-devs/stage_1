use std::fs;
use std::io;
use std::path::{Path, PathBuf};

pub const BODY_SUFFIX: &str = "_body.txt";
pub const HEADER_SUFFIX: &str = "_header.txt";

#[derive(Debug, PartialEq, Eq)]
pub struct LocatedBook {
    pub body_path: PathBuf,
    pub header_path: PathBuf,
}

pub trait Layout {
    fn name(&self) -> &'static str;

    fn directory(&self, root: &Path, book_id: i32) -> PathBuf;

    fn locate(&self, root: &Path, book_id: i32) -> io::Result<LocatedBook> {
        let body_path = self.directory(root, book_id).join(format!("{book_id}{BODY_SUFFIX}"));
        let header_path = body_path.with_file_name(format!("{book_id}{HEADER_SUFFIX}"));
        if body_path.is_file() && header_path.is_file() {
            return Ok(LocatedBook { body_path, header_path });
        }
        Err(not_found(&body_path))
    }
}

pub fn not_found(path: &Path) -> io::Error {
    io::Error::new(
        io::ErrorKind::NotFound,
        format!("book not found: {}", path.display()),
    )
}

pub fn read_book_body(book_id: i32, bodies_directory: &Path) -> io::Result<String> {
    fs::read_to_string(bodies_directory.join(format!("{book_id}{BODY_SUFFIX}")))
}

pub fn read_book_header(book_id: i32, headers_directory: &Path) -> io::Result<String> {
    fs::read_to_string(headers_directory.join(format!("{book_id}{HEADER_SUFFIX}")))
}
