//! Equivalence writes the canonical file that the cross-language checker
//! compares byte for byte: the token stream of every sample book, the posting
//! lists built from them and the result of every shared query. It reuses the
//! exact tokenizer, postings builder and query intersection of the timed
//! suite, so a file identical to the other languages' proves the harness
//! measures the same work everywhere.

use super::queries;
use super::BenchResult;
use crate::inverted_index::json_index::InvertedIndex;
use crate::inverted_index::postings;
use crate::inverted_index::text_processor;
use std::collections::BTreeMap;
use std::fs;
use std::io::Write;
use std::path::Path;

/// run implements `index_rust equivalence`, the Rust side of the
/// cross-language equivalence contract.
pub fn run(
    bodies_directory: &Path,
    book_ids_file: &Path,
    queries_file: &Path,
    output_file: &Path,
) -> BenchResult<()> {
    let book_ids = load_book_ids(book_ids_file)?;
    let tokenized = tokenize_books(bodies_directory, &book_ids)?;
    let index = postings::build(&tokenized);
    let queries = queries::load(queries_file)?;
    write_canonical_file(output_file, &tokenized, &index, &queries)
}

fn load_book_ids(book_ids_file: &Path) -> BenchResult<Vec<i32>> {
    let content = fs::read_to_string(book_ids_file)?;
    let mut book_ids = Vec::new();
    for line in content.lines() {
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        book_ids.push(
            trimmed
                .parse::<i32>()
                .map_err(|_| format!("{}: invalid book id {:?}", book_ids_file.display(), trimmed))?,
        );
    }
    Ok(book_ids)
}

fn tokenize_books(
    bodies_directory: &Path,
    book_ids: &[i32],
) -> BenchResult<BTreeMap<i32, Vec<String>>> {
    let mut tokenized = BTreeMap::new();
    for book_id in book_ids {
        let body = bodies_directory.join(format!("{book_id}_body.txt"));
        let text = fs::read_to_string(&body)?;
        tokenized.insert(*book_id, text_processor::process_text(&text));
    }
    Ok(tokenized)
}

fn write_canonical_file(
    output_file: &Path,
    tokenized: &BTreeMap<i32, Vec<String>>,
    index: &InvertedIndex,
    queries: &[Vec<String>],
) -> BenchResult<()> {
    let mut output = fs::File::create(output_file)?;
    write_token_lines(&mut output, tokenized)?;
    write_postings_lines(&mut output, index)?;
    write_query_lines(&mut output, index, queries)?;
    output.flush()?;
    Ok(())
}

fn write_token_lines(output: &mut impl Write, tokenized: &BTreeMap<i32, Vec<String>>) -> BenchResult<()> {
    for (book_id, tokens) in tokenized {
        writeln!(output, "tokens\t{book_id}\t{}", tokens.join("\t"))?;
    }
    Ok(())
}

fn write_postings_lines(output: &mut impl Write, index: &InvertedIndex) -> BenchResult<()> {
    let mut entries: Vec<(&str, &Vec<i32>)> = index.iter().collect();
    entries.sort_by(|left, right| left.0.cmp(right.0));
    for (term, book_ids) in entries {
        writeln!(output, "postings\t{term}\t{}", join_ids(book_ids))?;
    }
    Ok(())
}

fn write_query_lines(
    output: &mut impl Write,
    index: &InvertedIndex,
    queries: &[Vec<String>],
) -> BenchResult<()> {
    for (position, terms) in queries.iter().enumerate() {
        let matched = queries::intersect(terms, |term| {
            Ok(index.get(term).cloned().unwrap_or_default())
        })?;
        let suffix = if matched.is_empty() {
            String::new()
        } else {
            format!("\t{}", join_ids(&matched))
        };
        writeln!(output, "query\t{}{suffix}", position + 1)?;
    }
    Ok(())
}

fn join_ids(book_ids: &[i32]) -> String {
    book_ids
        .iter()
        .map(i32::to_string)
        .collect::<Vec<String>>()
        .join(",")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn canonical_file_contains_token_postings_and_query_lines() {
        let dir = std::env::temp_dir().join(format!("equivalence_test_{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        fs::write(dir.join("1_body.txt"), "alpha beta alpha").unwrap();
        fs::write(dir.join("2_body.txt"), "beta gamma").unwrap();
        let ids = dir.join("ids.txt");
        fs::write(&ids, "1\n2\n").unwrap();
        let queries_file = dir.join("queries.txt");
        fs::write(&queries_file, "alpha beta\nbeta delta\n").unwrap();
        let output = dir.join("out.txt");

        run(&dir, &ids, &queries_file, &output).unwrap();

        let content = fs::read_to_string(&output).unwrap();
        let lines: Vec<&str> = content.lines().collect();
        assert_eq!(lines[0], format!("tokens\t1\t{}", text_processor::process_text("alpha beta alpha").join("\t")));
        assert_eq!(
            &lines[2..],
            [
                "postings\talpha\t1",
                "postings\tbeta\t1,2",
                "postings\tgamma\t2",
                "query\t1\t1",
                "query\t2",
            ]
        );
        let _ = fs::remove_dir_all(&dir);
    }
}
