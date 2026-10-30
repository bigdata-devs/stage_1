package datalake;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

public final class GutenbergFetcher implements Fetcher {

    private final String baseUrl;
    private final HttpClient client = HttpClient.newHttpClient();

    public GutenbergFetcher() {
        this("https://www.gutenberg.org/cache/epub");
    }

    public GutenbergFetcher(String baseUrl) {
        this.baseUrl = baseUrl;
    }

    @Override
    public String fetch(int bookId) throws IOException {
        String url = baseUrl + "/" + bookId + "/pg" + bookId + ".txt";
        HttpRequest request = HttpRequest.newBuilder().uri(URI.create(url)).GET().build();
        try {
            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() != 200) {
                throw new IOException("HTTP " + response.statusCode() + " for book " + bookId);
            }
            return response.body();
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            throw new IOException("interrupted while fetching book " + bookId, exception);
        }
    }
}
