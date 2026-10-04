use super::text_processor::process_text;
use std::collections::BTreeMap;
use std::fs;
use std::io;
use std::path::Path;

pub const BODY_SUFFIX: &str = "_body.txt";

pub fn discover_book_ids(bodies_directory: &Path) -> io::Result<Vec<i32>> {
    if !bodies_directory.is_dir() {
        return Err(io::Error::new(
            io::ErrorKind::NotFound,
            format!("missing corpus directory: {}", bodies_directory.display()),
        ));
    }
    let mut book_ids = Vec::new();
    for entry in fs::read_dir(bodies_directory)? {
        let file_name = entry?.file_name();
        let name = file_name.to_string_lossy();
        let Some(book_id) = name.strip_suffix(BODY_SUFFIX) else {
            continue;
        };
        if let Ok(book_id) = book_id.parse() {
            book_ids.push(book_id);
        }
    }
    book_ids.sort_unstable();
    Ok(book_ids)
}

pub fn load(bodies_directory: &Path) -> io::Result<BTreeMap<i32, Vec<String>>> {
    let mut books = BTreeMap::new();
    for book_id in discover_book_ids(bodies_directory)? {
        let body_path = bodies_directory.join(format!("{book_id}{BODY_SUFFIX}"));
        let text = fs::read_to_string(&body_path)?;
        books.insert(book_id, process_text(&text));
    }
    Ok(books)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn temp_dir(label: &str) -> std::path::PathBuf {
        let dir = std::env::temp_dir().join(format!(
            "stage1_rust_corpus_{label}_{}",
            std::process::id()
        ));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        dir
    }

    #[test]
    fn discover_book_ids_returns_sorted_numeric_ids() {
        let dir = temp_dir("discover");
        fs::write(dir.join("1342_body.txt"), "text").unwrap();
        fs::write(dir.join("11_body.txt"), "text").unwrap();
        fs::write(dir.join("notes_body.txt"), "text").unwrap();
        assert_eq!(vec![11, 1342], discover_book_ids(&dir).unwrap());
        fs::remove_dir_all(&dir).unwrap();
    }

    #[test]
    fn load_tokenizes_every_body_in_book_id_order() {
        let dir = temp_dir("load");
        fs::write(dir.join("84_body.txt"), "Frankenstein by Shelley").unwrap();
        fs::write(dir.join("11_body.txt"), "Sense and Sensibility").unwrap();
        let books = load(&dir).unwrap();
        let ids: Vec<i32> = books.keys().copied().collect();
        assert_eq!(vec![11, 84], ids);
        assert_eq!(vec!["sense", "sensibility"], books[&11]);
        assert_eq!(vec!["frankenstein", "shelley"], books[&84]);
        fs::remove_dir_all(&dir).unwrap();
    }
}
