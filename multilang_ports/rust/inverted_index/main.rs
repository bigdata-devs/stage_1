use search_engine_bench::inverted_index::json_index::{load_index, InvertedIndex};
use search_engine_bench::inverted_index::text_processor::process_text;
use std::env;
use std::error::Error;
use std::fs;
use std::io;
use std::path::Path;

const BODY_SUFFIX: &str = "_body.txt";

fn main() {
    if let Err(message) = run() {
        eprintln!("{message}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn Error>> {
    let args: Vec<String> = env::args().collect();
    match args.get(1).map(String::as_str) {
        Some("build") if args.len() == 4 => build_index(&args[2], &args[3]),
        Some("query") if args.len() >= 4 => query_terms(&args[2], &args[3..]),
        _ => Err(usage().into()),
    }
}

fn build_index(bodies_directory: &str, output_path: &str) -> Result<(), Box<dyn Error>> {
    let mut index = InvertedIndex::new();
    for book_id in discover_book_ids(Path::new(bodies_directory))? {
        let body_path = Path::new(bodies_directory).join(format!("{book_id}{BODY_SUFFIX}"));
        let text = fs::read_to_string(&body_path)?;
        index.add_book(book_id, &process_text(&text));
    }
    index.save(Path::new(output_path))?;
    println!("Index contains {} unique terms", index.term_count());
    Ok(())
}

fn discover_book_ids(bodies_directory: &Path) -> io::Result<Vec<i32>> {
    let mut book_ids = Vec::new();
    for entry in fs::read_dir(bodies_directory)? {
        let file_name = entry?.file_name();
        let name = file_name.to_string_lossy();
        let Some(book_id) = name.strip_suffix(BODY_SUFFIX) else {
            continue;
        };
        let book_id = book_id.parse().map_err(|_| {
            io::Error::new(
                io::ErrorKind::InvalidData,
                format!("invalid book id: {book_id}"),
            )
        })?;
        book_ids.push(book_id);
    }
    book_ids.sort_unstable();
    Ok(book_ids)
}

fn query_terms(index_path: &str, terms: &[String]) -> Result<(), Box<dyn Error>> {
    let index = load_index(Path::new(index_path))?;
    for term in terms {
        match index.get(term) {
            Some(book_ids) => println!("{term}: {book_ids:?}"),
            None => println!("{term}: []"),
        }
    }
    Ok(())
}

fn usage() -> &'static str {
    "Usage: index_rust build <bodies_dir> <output_json>\n       index_rust query <index_json> <term>..."
}
