use super::suite::first_ids;
use super::BenchResult;
use crate::datalake::layout::Layout;
use crate::datalake::store::{pending_book_ids, Datalake};
use std::collections::HashSet;
use std::fs;
use std::path::Path;
use std::time::Instant;

pub struct RecoveryReport {
    pub total_books: usize,
    pub processed_before: usize,
    pub processed_after: usize,
    pub duplicated: usize,
    pub lost: usize,
    pub detection_time: std::time::Duration,
    pub processing_time: std::time::Duration,
    pub elapsed: std::time::Duration,
}

pub fn resume_after_interruption(
    layout: &dyn Layout,
    root: &Path,
    book_ids: &[i32],
) -> BenchResult<RecoveryReport> {
    let processed = first_ids(book_ids, book_ids.len() / 2);
    let detection_start = Instant::now();
    let pending = pending_book_ids(root, &processed)?;
    let detection_time = detection_start.elapsed();

    let processing_start = Instant::now();
    let resumed = read_stored_books(layout, root, &pending)?;
    let processing_time = processing_start.elapsed();

    let processed_set: HashSet<i32> = processed.iter().copied().collect();
    let resumed_set: HashSet<i32> = resumed.iter().copied().collect();
    let duplicated = resumed
        .iter()
        .filter(|book_id| processed_set.contains(book_id))
        .count();
    let lost = book_ids
        .iter()
        .filter(|book_id| !processed_set.contains(book_id) && !resumed_set.contains(book_id))
        .count();

    Ok(RecoveryReport {
        total_books: book_ids.len(),
        processed_before: processed.len(),
        processed_after: resumed.len(),
        duplicated,
        lost,
        detection_time,
        processing_time,
        elapsed: detection_time + processing_time,
    })
}

fn read_stored_books(
    layout: &dyn Layout,
    root: &Path,
    book_ids: &[i32],
) -> BenchResult<Vec<i32>> {
    let lake = Datalake::new(root, layout);
    let mut resumed = Vec::with_capacity(book_ids.len());
    for &book_id in book_ids {
        if is_book_complete(&lake, book_id) {
            resumed.push(book_id);
        }
    }
    Ok(resumed)
}

fn is_book_complete(lake: &Datalake<'_>, book_id: i32) -> bool {
    let Ok(book) = lake.locate(book_id) else {
        return false;
    };
    fs::read_to_string(&book.body_path).is_ok() && fs::read_to_string(&book.header_path).is_ok()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::datalake::book_based::BookBased;
    use std::path::PathBuf;

    fn temp_dir(label: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!(
            "stage1_rust_recovery_{label}_{}",
            std::process::id()
        ));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        dir
    }

    fn store(root: &Path, book_ids: &[i32]) {
        let lake = Datalake::new(root, &BookBased);
        for &book_id in book_ids {
            lake.store(book_id, &format!("header {book_id}"), &format!("body {book_id}"))
                .unwrap();
        }
    }

    #[test]
    fn complete_lake_resumes_the_second_half_without_losses() {
        let root = temp_dir("complete");
        let book_ids: Vec<i32> = (1..=6).collect();
        store(&root, &book_ids);
        let report = resume_after_interruption(&BookBased, &root, &book_ids).unwrap();
        assert_eq!(6, report.total_books);
        assert_eq!(3, report.processed_before);
        assert_eq!(3, report.processed_after);
        assert_eq!(0, report.duplicated);
        assert_eq!(0, report.lost);
        assert!(report.elapsed >= report.detection_time);
        fs::remove_dir_all(&root).unwrap();
    }

    #[test]
    fn interrupted_lake_resumes_stored_books_and_counts_the_lost_ones() {
        let root = temp_dir("interrupted");
        let book_ids: Vec<i32> = (1..=6).collect();
        store(&root, &book_ids);
        fs::remove_file(root.join("5/5_body.txt")).unwrap();
        fs::remove_file(root.join("6/6_body.txt")).unwrap();
        let report = resume_after_interruption(&BookBased, &root, &book_ids).unwrap();
        assert_eq!(1, report.processed_after);
        assert_eq!(2, report.lost);
        assert_eq!(0, report.duplicated);
        fs::remove_dir_all(&root).unwrap();
    }
}
