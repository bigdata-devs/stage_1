use search_engine_bench::inverted_index::text_processor::process_text;
use std::env;
use std::fs;

fn main() {
    let path = env::args().nth(1).expect("book path");
    let text = fs::read_to_string(&path).expect("read book");
    let tokens = process_text(&text);
    eprintln!("RUST count: {}", tokens.len());
    for token in &tokens {
        println!("{}", token);
    }
}
