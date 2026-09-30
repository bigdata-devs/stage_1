use super::fetcher::GutenbergFetcher;
use super::layout::{Layout, LocatedBook, BODY_SUFFIX, HEADER_SUFFIX};
use super::store::Datalake;
use chrono::Local;
use std::fs;
use std::io;
use std::path::{Path, PathBuf};

const DATE_PATTERN: &str = "%Y%m%d";
const HOUR_PATTERN: &str = "%H";

pub struct TimeBased;

impl Layout for TimeBased {
    fn name(&self) -> &'static str {
        "time_based"
    }

    fn directory(&self, root: &Path, _book_id: i32) -> PathBuf {
        let now = Local::now();
        root.join(now.format(DATE_PATTERN).to_string())
            .join(now.format(HOUR_PATTERN).to_string())
    }

    fn locate(&self, root: &Path, book_id: i32) -> io::Result<LocatedBook> {
        let body_name = format!("{book_id}{BODY_SUFFIX}");
        let header_name = format!("{book_id}{HEADER_SUFFIX}");
        let newest = newest_matching(root, &body_name, &header_name)?.ok_or_else(|| {
            io::Error::new(
                io::ErrorKind::NotFound,
                format!("book not found: {body_name}"),
            )
        })?;
        let header_path = newest.with_file_name(header_name);
        Ok(LocatedBook {
            body_path: newest,
            header_path,
        })
    }
}

fn newest_matching(directory: &Path, body_name: &str, header_name: &str) -> io::Result<Option<PathBuf>> {
    let mut newest: Option<PathBuf> = None;
    collect_newest(directory, body_name, header_name, &mut newest)?;
    Ok(newest)
}

fn collect_newest(
    directory: &Path,
    body_name: &str,
    header_name: &str,
    newest: &mut Option<PathBuf>,
) -> io::Result<()> {
    for entry in fs::read_dir(directory)? {
        let path = entry?.path();
        if path.is_dir() {
            collect_newest(&path, body_name, header_name, newest)?;
            continue;
        }
        let matches = path.file_name().is_some_and(|name| name == body_name)
            && path
                .with_file_name(header_name)
                .is_file();
        if matches {
            let replace = newest.as_ref().is_none_or(|current| path > *current);
            if replace {
                *newest = Some(path);
            }
        }
    }
    Ok(())
}

pub fn download(book_id: i32) -> bool {
    let lake = Datalake::new(super::project_root().join("datalake"), &TimeBased);
    lake.download(&GutenbergFetcher::new(), book_id)
}
