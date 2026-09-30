package metadata;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class BookProcessor {
    private static final String START_MARKER = "*** START OF THE PROJECT GUTENBERG EBOOK";
    private static final String END_MARKER = "*** END OF THE PROJECT GUTENBERG EBOOK";

    public static Map<String, Object> extractMetadata(String headerText) {
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("Title", "Unknown");
        metadata.put("Author", "Unknown");
        metadata.put("Language", "Unknown");

        Pattern titlePattern = Pattern.compile("Title:\\s*(.+)", Pattern.CASE_INSENSITIVE);
        Pattern authorPattern = Pattern.compile("Author:\\s*(.+)", Pattern.CASE_INSENSITIVE);
        Pattern languagePattern = Pattern.compile("Language:\\s*(.+)", Pattern.CASE_INSENSITIVE);

        Matcher titleMatcher = titlePattern.matcher(headerText);
        if (titleMatcher.find()) {
            metadata.put("Title", titleMatcher.group(1).trim());
        }

        Matcher authorMatcher = authorPattern.matcher(headerText);
        if (authorMatcher.find()) {
            metadata.put("Author", authorMatcher.group(1).trim());
        }

        Matcher languageMatcher = languagePattern.matcher(headerText);
        if (languageMatcher.find()) {
            metadata.put("Language", languageMatcher.group(1).trim());
        }

        return metadata;
    }

    public static Map<String, Object> processBook(int bookId, String outputDir, MetadataStorage dbBackend) {
        Path outputPath = Paths.get(outputDir);
        try {
            Files.createDirectories(outputPath);
        } catch (IOException e) {
            System.err.println("Error creating the output directory: " + e.getMessage());
            return null;
        }

        String url = String.format("https://www.gutenberg.org/cache/epub/%d/pg%d.txt", bookId, bookId);
        String text;

        try {
            HttpClient client = HttpClient.newBuilder().followRedirects(HttpClient.Redirect.NORMAL).build();
            HttpRequest request = HttpRequest.newBuilder().uri(URI.create(url)).build();
            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() != 200) {
                System.out.println("Error downloading the book " + bookId + ". Código HTTP: " + response.statusCode());
                return null;
            }
            text = response.body();
        } catch (IOException | InterruptedException e) {
            System.err.println("Error in the HTTP request for the book " + bookId + ": " + e.getMessage());
            return null;
        }

        if (!text.contains(START_MARKER) || !text.contains(END_MARKER)) {
            System.out.println("Bookmarks not found in the book " + bookId + ".");
            return null;
        }

        int startIndex = text.indexOf(START_MARKER);
        String header = text.substring(0, startIndex);
        
        String bodyAndFooter = text.substring(startIndex);
        int endIndex = bodyAndFooter.indexOf(END_MARKER);
        String body = bodyAndFooter.substring(0, endIndex);

        Path bodyPath = outputPath.resolve(bookId + "_body.txt");
        Path headerPath = outputPath.resolve(bookId + "_header.txt");

        try {
            Files.writeString(bodyPath, body.strip());
            Files.writeString(headerPath, header.strip());
        } catch (IOException e) {
            System.err.println("Error saving local text files: " + e.getMessage());
        }

        Map<String, Object> metadata = extractMetadata(header);
        metadata.put("book_id", bookId);

        DateTimeFormatter dtf = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
        metadata.put("Capture Date", LocalDateTime.now().format(dtf));

        dbBackend.save(metadata);

        return metadata;
    }
}