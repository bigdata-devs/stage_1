use crate::inverted_index::json_index::InvertedIndex;
use crate::inverted_index::postings::{append_sorted_unique, unique_terms};
use std::fs;
use std::io;
use std::path::{Path, PathBuf};

const FILE_EXTENSION: &str = ".txt";

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
    letter_dir.join(format!("{term}{FILE_EXTENSION}"))
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
