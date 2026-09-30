use chrono::Local;

pub fn line(message: &str) {
    println!("{} {message}", Local::now().format("%Y/%m/%d %H:%M:%S"));
}
