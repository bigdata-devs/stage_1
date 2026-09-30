import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Set;

public final class TextProcessor {

    private static final Set<String> ROMAN_NUMERALS = Set.of(
        "c", "i", "ii", "iii", "iv", "ix", "l", "lx", "lxx", "lxxx", "v",
        "vi", "vii", "viii", "x", "xc", "xi", "xii", "xiii", "xiv", "xix",
        "xl", "xv", "xvi", "xvii", "xviii", "xx", "xxi", "xxii", "xxiii",
        "xxiv", "xxix", "xxv", "xxvi", "xxvii", "xxviii", "xxx"
    );

    private static final Set<String> STOP_WORDS = Set.of(
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
        "you", "your"
    );

    private TextProcessor() {
    }

    public static List<String> processText(String text) {
        return normalize(tokenize(text));
    }

    private static List<String> tokenize(String text) {
        String lowered = text.toLowerCase(Locale.ROOT);
        List<String> tokens = new ArrayList<>();
        int runStart = -1;
        for (int position = 0; position <= lowered.length(); position++) {
            boolean insideRun = position < lowered.length() && isAlphabetLetter(lowered.charAt(position));
            if (insideRun && runStart < 0) {
                runStart = position;
            } else if (!insideRun && runStart >= 0) {
                tokens.add(lowered.substring(runStart, position));
                runStart = -1;
            }
        }
        return tokens;
    }

    private static boolean isAlphabetLetter(char character) {
        return character >= 'a' && character <= 'z';
    }

    private static List<String> normalize(List<String> tokens) {
        List<String> kept = new ArrayList<>();
        for (String token : tokens) {
            if (shouldKeep(token)) {
                kept.add(token);
            }
        }
        return kept;
    }

    private static boolean shouldKeep(String token) {
        return token.length() > 1
            && !STOP_WORDS.contains(token)
            && !ROMAN_NUMERALS.contains(token);
    }
}
