use search_engine_bench::datalake::{batch_based, book_based, time_based};

fn main() {
    println!("--- Testing Time-based in Rust ---");
    time_based::download(1342);

    println!("\n--- Testing Book-based in Rust ---");
    book_based::download(84);

    println!("\n--- Testing Batch-based in Rust ---");
    batch_based::download(1500);
}
