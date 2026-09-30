use std::io;

const START_MARKER: &str = "*** START OF THE PROJECT GUTENBERG EBOOK";
const END_MARKER: &str = "*** END OF THE PROJECT GUTENBERG EBOOK";

pub struct Split {
    pub header: String,
    pub body: String,
}

pub fn split(text: &str) -> io::Result<Split> {
    let start = text
        .find(START_MARKER)
        .ok_or_else(|| markers_missing())?;
    let end = text.find(END_MARKER).ok_or_else(|| markers_missing())?;
    let body_start = start + text[start..].find('\n').map_or(0, |offset| offset + 1);
    if end < body_start {
        return Err(markers_missing());
    }
    Ok(Split {
        header: text[..start].trim().to_string(),
        body: text[body_start..end].trim().to_string(),
    })
}

fn markers_missing() -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, "Gutenberg markers not found")
}

#[cfg(test)]
mod tests {
    use super::*;

    const BOOK: &str = "Header text.\n\n\
        *** START OF THE PROJECT GUTENBERG EBOOK Frankenstein ***\n\
        Body paragraph.\n\
        *** END OF THE PROJECT GUTENBERG EBOOK Frankenstein ***\nTrailer.";

    #[test]
    fn split_extracts_trimmed_header_and_body() {
        let split = split(BOOK).unwrap();
        assert_eq!("Header text.", split.header);
        assert_eq!("Body paragraph.", split.body);
    }

    #[test]
    fn split_rejects_texts_without_markers() {
        assert!(split("plain text").is_err());
    }
}
