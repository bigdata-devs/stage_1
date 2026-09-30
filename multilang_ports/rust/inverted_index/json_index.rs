use std::collections::HashMap;
use std::fs;
use std::io;
use std::path::Path;

struct IndexEntry {
    term: String,
    postings: Vec<i32>,
    last_book_id: i32,
}

pub struct InvertedIndex {
    entries: Vec<IndexEntry>,
    lookup: HashMap<String, usize>,
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
            let entry = &mut self.entries[position];
            if entry.last_book_id != book_id {
                entry.postings.push(book_id);
                entry.last_book_id = book_id;
            }
        }
    }

    pub fn term_count(&self) -> usize {
        self.entries.len()
    }

    pub fn save(&self, path: &Path) -> io::Result<()> {
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
        fs::write(path, json)
    }

    fn create_entry(&mut self, term: &str) -> usize {
        self.entries.push(IndexEntry {
            term: term.to_string(),
            postings: Vec::new(),
            last_book_id: -1,
        });
        let position = self.entries.len() - 1;
        self.lookup.insert(term.to_string(), position);
        position
    }
}

pub fn load_index(path: &Path) -> io::Result<HashMap<String, Vec<i32>>> {
    let json = fs::read_to_string(path)?;
    IndexParser::new(&json).parse_object()
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

    fn parse_object(&mut self) -> io::Result<HashMap<String, Vec<i32>>> {
        let mut index = HashMap::new();
        self.expect(b'{')?;
        self.skip_whitespace();
        if self.peek() == b'}' {
            return Ok(index);
        }
        loop {
            self.skip_whitespace();
            let term = self.parse_string()?;
            self.skip_whitespace();
            self.expect(b':')?;
            self.skip_whitespace();
            let book_ids = self.parse_postings()?;
            index.insert(term, book_ids);
            self.skip_whitespace();
            if self.consume_if(b'}') {
                return Ok(index);
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
