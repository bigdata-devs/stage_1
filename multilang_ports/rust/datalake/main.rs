mod downloader;
mod time_based;
mod book_based;
mod batch_based;

fn main() {
    println!("--- Testing Time-based in Rust ---");
    time_based::download(1342);
    
    println!("\n--- Testing Book-based in Rust ---");
    book_based::download(84);
    
    println!("\n--- Testing Batch-based in Rust ---");
    batch_based::download(1500, 1000);
}