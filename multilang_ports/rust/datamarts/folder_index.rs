use crate::inverted_index::json_index::InvertedIndex;
use crate::inverted_index::postings::{append_sorted_unique, unique_terms};
use std::fs;
use std::io;
use std::path::{Path, PathBuf};

const FILE_EXTENSION: &str = ".txt";
const RESERVED_NAME_ESCAPE: &str = "_";

/// Mirrors WINDOWS_RESERVED_NAMES in folder_index.py: Windows refuses these
/// device names as file names whatever their extension, so their term files
/// get a trailing underscore ("con" -> "C/con_.txt"). Terms only contain
/// letters, so the escaped name can never clash with a real term.
fn is_windows_reserved_name(term: &str) -> bool {
    let lowered = term.to_ascii_lowercase();
    if matches!(lowered.as_str(), "con" | "prn" | "aux" | "nul") {
        return true;
    }
    let device_number = lowered
        .strip_prefix("com")
        .or_else(|| lowered.strip_prefix("lpt"));
    matches!(device_number, Some("1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9"))
}

fn term_file_name(term: &str) -> String {
    if is_windows_reserved_name(term) {
        return format!("{term}{RESERVED_NAME_ESCAPE}{FILE_EXTENSION}");
    }
    format!("{term}{FILE_EXTENSION}")
}

pub fn save(index: &InvertedIndex, output_dir: &Path) -> io::Result<()> {
    fs::create_dir_all(output_dir)?;
    for (term, postings) in index.iter() {
        let letter_dir = output_dir.join(letter(term));
        fs::create_dir_all(&letter_dir)?;
        write_term_file(&term_file(&letter_dir, term), postings)?;
    }
    Ok(())
}

pub fn query(term: &str, index_dir: &Path) -> io::Result<Vec<i32>> {
    if term.is_empty() {
        return Ok(Vec::new());
    }
    let file = term_file(&index_dir.join(letter(term)), term);
    if !file.is_file() {
        return Ok(Vec::new());
    }
    read_postings(&file)
}

pub fn update(book_id: i32, tokens: &[String], index_dir: &Path) -> io::Result<()> {
    for term in unique_terms(tokens) {
        let letter_dir = index_dir.join(letter(&term));
        fs::create_dir_all(&letter_dir)?;
        let file = term_file(&letter_dir, &term);
        let mut postings = if file.is_file() {
            read_postings(&file)?
        } else {
            Vec::new()
        };
        append_sorted_unique(&mut postings, book_id);
        write_term_file(&file, &postings)?;
    }
    Ok(())
}

fn letter(term: &str) -> String {
    term.chars()
        .next()
        .expect("terms are never empty")
        .to_ascii_uppercase()
        .to_string()
}

fn term_file(letter_dir: &Path, term: &str) -> PathBuf {
    letter_dir.join(term_file_name(term))
}

fn read_postings(file: &Path) -> io::Result<Vec<i32>> {
    let content = fs::read_to_string(file)?;
    let mut book_ids = Vec::new();
    for line in content.lines() {
        let trimmed = line.trim();
        if !trimmed.is_empty() {
            book_ids.push(trimmed.parse().map_err(|_| {
                io::Error::new(
                    io::ErrorKind::InvalidData,
                    format!("invalid book id in {}: {trimmed}", file.display()),
                )
            })?);
        }
    }
    Ok(book_ids)
}

fn write_term_file(file: &Path, book_ids: &[i32]) -> io::Result<()> {
    let mut content = String::new();
    for book_id in book_ids {
        content.push_str(&format!("{book_id}\n"));
    }
    fs::write(file, content)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn temp_dir(label: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!(
            "stage1_rust_folder_{label}_{}",
            std::process::id()
        ));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        dir
    }

    #[test]
    fn save_writes_one_file_per_term_under_uppercase_letter_directories() {
        let dir = temp_dir("save");
        let mut index = InvertedIndex::new();
        index.add_book(11, &vec!["alpha".to_string(), "beta".to_string()]);
        index.add_book(84, &vec!["alpha".to_string()]);
        save(&index, &dir).unwrap();
        assert_eq!("11\n84\n", fs::read_to_string(dir.join("A/alpha.txt")).unwrap());
        assert_eq!("11\n", fs::read_to_string(dir.join("B/beta.txt")).unwrap());
        fs::remove_dir_all(&dir).unwrap();
    }

    #[test]
    fn query_returns_an_empty_list_for_missing_terms() {
        let dir = temp_dir("query_missing");
        assert_eq!(Vec::<i32>::new(), query("alpha", &dir).unwrap());
        assert_eq!(Vec::<i32>::new(), query("", &dir).unwrap());
        fs::remove_dir_all(&dir).unwrap();
    }

    #[test]
    fn save_escapes_windows_reserved_names() {
        let dir = temp_dir("reserved_save");
        let mut index = InvertedIndex::new();
        let terms: Vec<String> = ["con", "aux", "nul", "prn", "console"]
            .iter()
            .map(|term| term.to_string())
            .collect();
        index.add_book(7, &terms);
        save(&index, &dir).unwrap();
        for name in ["C/con_.txt", "A/aux_.txt", "N/nul_.txt", "P/prn_.txt", "C/console.txt"] {
            assert!(dir.join(name).is_file(), "missing term file {name}");
        }
        assert!(!dir.join("C/con.txt").exists());
        for term in &terms {
            assert_eq!(vec![7], query(term, &dir).unwrap());
        }
        fs::remove_dir_all(&dir).unwrap();
    }

    #[test]
    fn update_escapes_windows_reserved_names() {
        let dir = temp_dir("reserved_update");
        update(3, &vec!["aux".to_string()], &dir).unwrap();
        update(1, &vec!["aux".to_string()], &dir).unwrap();
        assert_eq!("1\n3\n", fs::read_to_string(dir.join("A/aux_.txt")).unwrap());
        fs::remove_dir_all(&dir).unwrap();
    }

    #[test]
    fn term_file_name_only_escapes_device_names() {
        assert_eq!("con_.txt", term_file_name("con"));
        assert_eq!("lpt9_.txt", term_file_name("lpt9"));
        assert_eq!("com.txt", term_file_name("com"));
        assert_eq!("console.txt", term_file_name("console"));
    }

    #[test]
    fn update_appends_sorted_unique_book_ids() {
        let dir = temp_dir("update");
        update(9, &vec!["island".to_string(), "zebra".to_string()], &dir).unwrap();
        update(4, &vec!["island".to_string(), "apple".to_string()], &dir).unwrap();
        assert_eq!("4\n9\n", fs::read_to_string(dir.join("I/island.txt")).unwrap());
        assert_eq!("4\n", fs::read_to_string(dir.join("A/apple.txt")).unwrap());
        assert_eq!("9\n", fs::read_to_string(dir.join("Z/zebra.txt")).unwrap());
        fs::remove_dir_all(&dir).unwrap();
    }
}
