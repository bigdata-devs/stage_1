package datalake;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

public class Downloader {
    private static final String START_MARKER = "*** START OF THE PROJECT GUTENBERG EBOOK";
    private static final String END_MARKER = "*** END OF THE PROJECT GUTENBERG EBOOK";

    public static final Path PROJECT_ROOT = Paths.get(".").toAbsolutePath().normalize();

    public static boolean fetchAndSave(int bookId, Path outputPath) {
        try {
            Files.createDirectories(outputPath);
            String url = "https://www.gutenberg.org/cache/epub/" + bookId + "/pg" + bookId + ".txt";
            System.out.println("Downloading book " + bookId + " from " + url + "...");

            HttpClient client = HttpClient.newHttpClient();
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(url))
                    .GET()
                    .build();

            HttpResponse response = client.send(request, HttpResponse.BodyHandlers.ofString());
            String text = response.body();

            if (response.statusCode() != 200 || !text.contains(START_MARKER)) {
                System.out.println("Error or invalid format for book " + bookId);
                return false;
            }

            int startIndex = text.indexOf(START_MARKER);
            int endIndex = text.indexOf(END_MARKER);

            if (startIndex == -1 || endIndex == -1) {
                System.out.println("Markers not found in book " + bookId);
                return false;
            }

            String header = text.substring(0, startIndex).trim();
            int bodyStart = text.indexOf('\n', startIndex) + 1;
            String body = text.substring(bodyStart, endIndex).trim();

            Path bodyPath = outputPath.resolve(bookId + "_body.txt");
            Path headerPath = outputPath.resolve(bookId + "_header.txt");

            Files.writeString(bodyPath, body);
            Files.writeString(headerPath, header);

            System.out.println("Book " + bookId + " successfully saved to " + outputPath);
            return true;

        } catch (IOException | InterruptedException e) {
            System.err.println("Exception downloading book " + bookId + ": " + e.getMessage());
            return false;
        }
    }
}