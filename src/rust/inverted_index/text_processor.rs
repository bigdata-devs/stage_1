use std::collections::HashSet;
use std::sync::LazyLock;

static ROMAN_NUMERALS: LazyLock<HashSet<&'static str>> = LazyLock::new(|| {
    [
        "c", "i", "ii", "iii", "iv", "ix", "l", "lx", "lxx", "lxxx", "v",
        "vi", "vii", "viii", "x", "xc", "xi", "xii", "xiii", "xiv", "xix",
        "xl", "xv", "xvi", "xvii", "xviii", "xx", "xxi", "xxii", "xxiii",
        "xxiv", "xxix", "xxv", "xxvi", "xxvii", "xxviii", "xxx",
    ]
    .into_iter()
    .collect()
});

static STOP_WORDS: LazyLock<HashSet<&'static str>> = LazyLock::new(|| {
    [
        "a", "about", "after", "again", "all", "also", "an", "and", "are",
        "as", "at", "back", "be", "been", "before", "being", "between",
        "both", "but", "by", "can", "could", "did", "do", "does", "each",
        "even", "every", "few", "for", "from", "had", "has", "have", "he",
        "her", "here", "his", "how", "i", "if", "in", "into", "is", "it",
        "its", "just", "many", "may", "me", "might", "more", "most", "much",
        "my", "new", "no", "not", "now", "of", "off", "on", "one", "only",
        "or", "other", "our", "out", "over", "own", "same", "shall", "she",
        "should", "so", "some", "still", "such", "than", "that", "the",
        "their", "them", "then", "there", "these", "they", "this", "those",
        "three", "through", "to", "too", "two", "under", "up", "very", "was",
        "we", "well", "were", "when", "where", "why", "will", "with", "would",
        "you", "your",
    ]
    .into_iter()
    .collect()
});

pub fn process_text(text: &str) -> Vec<String> {
    let lowered = text.to_lowercase();
    let mut tokens = Vec::new();
    let mut run = String::new();
    for character in lowered.chars() {
        if character.is_ascii_lowercase() {
            run.push(character);
        } else {
            flush_run(&mut tokens, &mut run);
        }
    }
    flush_run(&mut tokens, &mut run);
    tokens
}

fn flush_run(tokens: &mut Vec<String>, run: &mut String) {
    if run.is_empty() {
        return;
    }
    if should_keep(run.as_str()) {
        tokens.push(std::mem::take(run));
    } else {
        run.clear();
    }
}

fn should_keep(token: &str) -> bool {
    token.len() > 1 && !STOP_WORDS.contains(token) && !ROMAN_NUMERALS.contains(token)
}
