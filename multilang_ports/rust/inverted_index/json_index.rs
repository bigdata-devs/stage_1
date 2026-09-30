use super::postings::append_sorted_unique;
use std::collections::HashMap;
use std::fs;
use std::io;
use std::path::Path;

struct IndexEntry {
    term: String,
    postings: Vec<i32>,
}

pub struct InvertedIndex {
    entries: Vec<IndexEntry>,
    lookup: HashMap<String, usize>,
}

impl Default for InvertedIndex {
    fn default() -> Self {
        Self::new()
    }
}

impl InvertedIndex {
    pub fn new() -> Self {
        Self {
            entries: Vec::new(),
            lookup: HashMap::new(),
        }
    }

    pub fn add_book(&mut self, book_id: i32, tokens: &[String]) {
        for token in tokens {
            let position = match self.lookup.get(token) {
                Some(&position) => position,
                None => self.create_entry(token),
            };
            append_sorted_unique(&mut self.entries[position].postings, book_id);
        }
    }

    pub fn get(&self, term: &str) -> Option<&Vec<i32>> {
        self.lookup
            .get(term)
            .map(|position| &self.entries[*position].postings)
    }

    pub fn term_count(&self) -> usize {
        self.entries.len()
    }

    pub fn iter(&self) -> impl Iterator<Item = (&str, &Vec<i32>)> {
        self.entries
            .iter()
            .map(|entry| (entry.term.as_str(), &entry.postings))
    }

    pub fn save(&self, path: &Path) -> io::Result<()> {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        fs::write(path, self.serialize())
    }

    fn serialize(&self) -> String {
        let mut json = String::from("{\n");
        for (position, entry) in self.entries.iter().enumerate() {
            json.push_str(&format!("  \"{}\": ", entry.term));
            json.push_str(&format_postings(&entry.postings));
            json.push_str(if position + 1 < self.entries.len() {
                ",\n"
            } else {
                "\n"
            });
        }
        json.push('}');
        json
    }

    fn create_entry(&mut self, term: &str) -> usize {
        self.entries.push(IndexEntry {
            term: term.to_string(),
            postings: Vec::new(),
        });
        let position = self.entries.len() - 1;
        self.lookup.insert(term.to_string(), position);
        position
    }
}

pub fn load(path: &Path) -> io::Result<InvertedIndex> {
    let json = fs::read_to_string(path)?;
    let mut index = InvertedIndex::new();
    IndexParser::new(&json).parse_object(&mut index)?;
    Ok(index)
}

pub fn add_book_to_file(book_id: i32, tokens: &[String], path: &Path) -> io::Result<()> {
    let mut index = if path.is_file() {
        load(path)?
    } else {
        InvertedIndex::new()
    };
    index.add_book(book_id, tokens);
    index.save(path)
}

fn format_postings(book_ids: &[i32]) -> String {
    if book_ids.is_empty() {
        return "[]".to_string();
    }
    let mut formatted = String::from("[\n");
    for (position, book_id) in book_ids.iter().enumerate() {
        formatted.push_str(&format!("    {book_id}"));
        formatted.push_str(if position + 1 < book_ids.len() {
            ",\n"
        } else {
            "\n"
        });
    }
    formatted.push_str("  ]");
    formatted
}

fn invalid_index() -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, "invalid index file")
}

struct IndexParser<'a> {
    source: &'a [u8],
    position: usize,
}

impl<'a> IndexParser<'a> {
    fn new(source: &'a str) -> Self {
        Self {
            source: source.as_bytes(),
            position: 0,
        }
    }

    fn parse_object(&mut self, index: &mut InvertedIndex) -> io::Result<()> {
        self.expect(b'{')?;
        self.skip_whitespace();
        if self.peek() == b'}' {
            return Ok(());
        }
        loop {
            self.skip_whitespace();
            let term = self.parse_string()?;
            self.skip_whitespace();
            self.expect(b':')?;
            self.skip_whitespace();
            let postings = self.parse_postings()?;
            index.entries.push(IndexEntry { term, postings });
            let last = index.entries.len() - 1;
            index
                .lookup
                .insert(index.entries[last].term.clone(), last);
            self.skip_whitespace();
            if self.consume_if(b'}') {
                return Ok(());
            }
            self.expect(b',')?;
        }
    }

    fn parse_postings(&mut self) -> io::Result<Vec<i32>> {
        let mut book_ids = Vec::new();
        self.expect(b'[')?;
        self.skip_whitespace();
        if self.peek() == b']' {
            self.position += 1;
            return Ok(book_ids);
        }
        loop {
            self.skip_whitespace();
            book_ids.push(self.parse_integer()?);
            self.skip_whitespace();
            if self.consume_if(b']') {
                return Ok(book_ids);
            }
            self.expect(b',')?;
        }
    }

    fn parse_string(&mut self) -> io::Result<String> {
        self.expect(b'"')?;
        let start = self.position;
        while self.peek() != b'"' {
            if self.position >= self.source.len() {
                return Err(invalid_index());
            }
            self.position += 1;
        }
        let value = std::str::from_utf8(&self.source[start..self.position])
            .map_err(|_| invalid_index())?
            .to_string();
        self.position += 1;
        Ok(value)
    }

    fn parse_integer(&mut self) -> io::Result<i32> {
        let start = self.position;
        while self.position < self.source.len()
            && (self.source[self.position].is_ascii_digit() || self.source[self.position] == b'-')
        {
            self.position += 1;
        }
        std::str::from_utf8(&self.source[start..self.position])
            .ok()
            .filter(|text| !text.is_empty())
            .and_then(|text| text.parse().ok())
            .ok_or_else(invalid_index)
    }

    fn skip_whitespace(&mut self) {
        while self.position < self.source.len() && self.source[self.position].is_ascii_whitespace()
        {
            self.position += 1;
        }
    }

    fn peek(&self) -> u8 {
        *self.source.get(self.position).unwrap_or(&0)
    }

    fn consume_if(&mut self, expected: u8) -> bool {
        if self.peek() == expected {
            self.position += 1;
            return true;
        }
        false
    }

    fn expect(&mut self, expected: u8) -> io::Result<()> {
        if self.consume_if(expected) {
            Ok(())
        } else {
            Err(invalid_index())
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tokens(values: &[&str]) -> Vec<String> {
        values.iter().map(|value| value.to_string()).collect()
    }

    fn temp_file(label: &str) -> std::path::PathBuf {
        let path = std::env::temp_dir().join(format!(
            "stage1_rust_index_{label}_{}.json",
            std::process::id()
        ));
        let _ = fs::remove_file(&path);
        path
    }

    #[test]
    fn save_and_load_round_trip_preserves_order() {
        let mut books = std::collections::BTreeMap::new();
        books.insert(11, tokens(&["alpha", "beta"]));
        books.insert(84, tokens(&["beta"]));
        let path = temp_file("roundtrip");
        crate::inverted_index::postings::build(&books).save(&path).unwrap();
        let loaded = load(&path).unwrap();
        let terms: Vec<&str> = loaded.iter().map(|(term, _)| term).collect();
        assert_eq!(vec!["alpha", "beta"], terms);
        assert_eq!(Some(&vec![11]), loaded.get("alpha"));
        assert_eq!(Some(&vec![11, 84]), loaded.get("beta"));
        fs::remove_file(&path).unwrap();
    }

    #[test]
    fn add_book_to_file_creates_and_merges_sorted_postings() {
        let path = temp_file("add_book");
        add_book_to_file(9, &tokens(&["island", "zebra"]), &path).unwrap();
        add_book_to_file(4, &tokens(&["island", "apple"]), &path).unwrap();
        let loaded = load(&path).unwrap();
        assert_eq!(Some(&vec![4]), loaded.get("apple"));
        assert_eq!(Some(&vec![4, 9]), loaded.get("island"));
        assert_eq!(Some(&vec![9]), loaded.get("zebra"));
        fs::remove_file(&path).unwrap();
    }

    #[test]
    fn load_fails_for_a_missing_file() {
        let path = std::env::temp_dir().join("stage1_rust_absent_index.json");
        assert!(load(&path).is_err());
    }
}
