use super::json_index::InvertedIndex;
use std::collections::BTreeMap;

pub fn build(books: &BTreeMap<i32, Vec<String>>) -> InvertedIndex {
    let mut index = InvertedIndex::new();
    for (book_id, tokens) in books {
        index.add_book(*book_id, tokens);
    }
    index
}

pub fn unique_terms(tokens: &[String]) -> Vec<String> {
    let mut seen = Vec::new();
    for token in tokens {
        if !seen.iter().any(|existing| existing == token) {
            seen.push(token.clone());
        }
    }
    seen
}

pub fn append_sorted_unique(postings: &mut Vec<i32>, book_id: i32) {
    if let Err(position) = postings.binary_search(&book_id) {
        postings.insert(position, book_id);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tokens(values: &[&str]) -> Vec<String> {
        values.iter().map(|value| value.to_string()).collect()
    }

    #[test]
    fn build_sorts_and_deduplicates_book_ids() {
        let mut books = BTreeMap::new();
        books.insert(9, tokens(&["cat"]));
        books.insert(3, tokens(&["cat"]));
        let index = build(&books);
        assert_eq!(Some(&vec![3, 9]), index.get("cat"));
    }

    #[test]
    fn build_keeps_first_appearance_order_of_terms() {
        let mut books = BTreeMap::new();
        books.insert(1, tokens(&["zebra", "apple"]));
        books.insert(2, tokens(&["mango", "apple"]));
        let index = build(&books);
        let terms: Vec<&str> = index.iter().map(|(term, _)| term).collect();
        assert_eq!(vec!["zebra", "apple", "mango"], terms);
    }

    #[test]
    fn unique_terms_keeps_first_appearance() {
        assert_eq!(
            tokens(&["cat", "dog", "bird"]),
            unique_terms(&tokens(&["cat", "dog", "cat", "bird", "dog"]))
        );
    }

    #[test]
    fn append_sorted_unique_inserts_in_order_without_duplicates() {
        let mut postings = vec![5, 12];
        append_sorted_unique(&mut postings, 9);
        assert_eq!(vec![5, 9, 12], postings);
        append_sorted_unique(&mut postings, 5);
        assert_eq!(vec![5, 9, 12], postings);
        let mut single = Vec::new();
        append_sorted_unique(&mut single, 7);
        assert_eq!(vec![7], single);
    }

    #[test]
    fn build_matches_python_corpus_semantics() {
        let mut books = BTreeMap::new();
        books.insert(11, tokens(&["island"]));
        books.insert(84, tokens(&["island", "shipwreck"]));
        let index = build(&books);
        assert_eq!(Some(&vec![11, 84]), index.get("island"));
        assert_eq!(Some(&vec![84]), index.get("shipwreck"));
        let terms: Vec<&str> = index.iter().map(|(term, _)| term).collect();
        assert!(terms.iter().position(|t| *t == "island") < terms.iter().position(|t| *t == "shipwreck"));
    }

    #[test]
    fn build_ignores_repeated_tokens_of_the_same_book() {
        let mut books = BTreeMap::new();
        books.insert(1, tokens(&["island", "island", "ship"]));
        let index = build(&books);
        assert_eq!(Some(&vec![1]), index.get("island"));
        assert_eq!(Some(&vec![1]), index.get("ship"));
    }
}
