package datalake;

public final class Splitter {

    private static final String START_MARKER = "*** START OF THE PROJECT GUTENBERG EBOOK";
    private static final String END_MARKER = "*** END OF THE PROJECT GUTENBERG EBOOK";

    private Splitter() {
    }

    public static Split split(String text) {
        int startIndex = text.indexOf(START_MARKER);
        int endIndex = text.indexOf(END_MARKER);
        if (startIndex == -1 || endIndex == -1) {
            throw new IllegalArgumentException("Gutenberg markers not found");
        }
        String header = text.substring(0, startIndex).trim();
        int bodyStart = text.indexOf('\n', startIndex) + 1;
        String body = text.substring(bodyStart, endIndex).trim();
        return new Split(header, body);
    }

    public record Split(String header, String body) {
    }
}
