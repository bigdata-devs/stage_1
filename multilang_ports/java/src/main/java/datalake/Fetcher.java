package datalake;

import java.io.IOException;

public interface Fetcher {

    String fetch(int bookId) throws IOException;
}
