use super::BenchResult;
use std::collections::HashSet;
use std::fs;
use std::path::Path;

pub fn load(path: &Path) -> BenchResult<Vec<Vec<String>>> {
    let content = fs::read_to_string(path)?;
    let mut queries = Vec::new();
    for line in content.lines() {
        let terms = terms_of(line);
        if !terms.is_empty() {
            queries.push(terms);
        }
    }
    if queries.is_empty() {
        return Err(format!("{} must define at least one query", path.display()).into());
    }
    Ok(queries)
}

pub fn intersect<F>(terms: &[String], mut lookup: F) -> BenchResult<Vec<i32>>
where
    F: FnMut(&str) -> BenchResult<Vec<i32>>,
{
    let mut matched: Option<HashSet<i32>> = None;
    for (position, term) in terms.iter().enumerate() {
        let current: HashSet<i32> = lookup(term)?.into_iter().collect();
        if position == 0 {
            matched = Some(current);
        } else {
            matched.as_mut().unwrap().retain(|book_id| current.contains(book_id));
        }
        if matched.as_ref().is_some_and(HashSet::is_empty) {
            break;
        }
    }
    let mut result: Vec<i32> = matched.map(|set| set.into_iter().collect()).unwrap_or_default();
    result.sort_unstable();
    Ok(result)
}

fn terms_of(line: &str) -> Vec<String> {
    let content = match line.find('#') {
        Some(position) => &line[..position],
        None => line,
    };
    content
        .split_whitespace()
        .map(|term| term.to_string())
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn temp_dir(label: &str) -> std::path::PathBuf {
        let dir = std::env::temp_dir().join(format!(
            "stage1_rust_queries_{label}_{}",
            std::process::id()
        ));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        dir
    }

    #[test]
    fn load_reads_terms_and_skips_comments_and_blank_lines() {
        let dir = temp_dir("load");
        let path = dir.join("queries.txt");
        fs::write(&path, "# comment line\n\n  alpha beta \t gamma\nalpha\n").unwrap();
        let queries = load(&path).unwrap();
        assert_eq!(
            vec![
                vec!["alpha", "beta", "gamma"],
                vec!["alpha"]
            ],
            queries
                .iter()
                .map(|query| query.iter().map(String::as_str).collect::<Vec<_>>())
                .collect::<Vec<_>>()
        );
        fs::remove_dir_all(&dir).unwrap();
    }

    #[test]
    fn load_rejects_an_empty_workload() {
        let dir = temp_dir("empty");
        let path = dir.join("queries.txt");
        fs::write(&path, "# nothing here\n\n").unwrap();
        assert!(load(&path).is_err());
        fs::remove_dir_all(&dir).unwrap();
    }

    #[test]
    fn intersect_keeps_documents_that_contain_every_term() {
        let postings = |term: &str| -> BenchResult<Vec<i32>> {
            Ok(match term {
                "alpha" => vec![1, 2, 3],
                "beta" => vec![2, 3, 4],
                "gamma" => vec![9],
                _ => Vec::new(),
            })
        };
        let terms: Vec<String> = ["alpha", "beta"].iter().map(|t| t.to_string()).collect();
        assert_eq!(vec![2, 3], intersect(&terms, postings).unwrap());
    }

    #[test]
    fn intersect_returns_empty_when_any_term_is_missing() {
        let terms: Vec<String> = ["alpha", "missing"].iter().map(|t| t.to_string()).collect();
        let result = intersect(&terms, |term| {
            Ok(if term == "alpha" { vec![1, 2] } else { Vec::new() })
        })
        .unwrap();
        assert!(result.is_empty());
    }
}
