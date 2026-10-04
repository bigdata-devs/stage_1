use search_engine_bench::inverted_index::corpus;
use search_engine_bench::inverted_index::json_index::{self, InvertedIndex};
use search_engine_bench::inverted_index::postings;
use std::env;
use std::error::Error;
use std::path::Path;

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
    let books = corpus::load(Path::new(bodies_directory))?;
    let index = postings::build(&books);
    index.save(Path::new(output_path))?;
    println!("Index contains {} unique terms", index.term_count());
    Ok(())
}

fn query_terms(index_path: &str, terms: &[String]) -> Result<(), Box<dyn Error>> {
    let index: InvertedIndex = json_index::load(Path::new(index_path))?;
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
