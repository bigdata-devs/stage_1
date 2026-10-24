package microbench;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class SampleBookTest {

    private static final String BODIES_DIRECTORY_PROPERTY = "jmh.bodies.dir";

    @Test
    void sampleTextFallsBackToTheEmbeddedChapterWhenTheDatasetIsMissing() {
        String original = System.getProperty(BODIES_DIRECTORY_PROPERTY);
        System.setProperty(BODIES_DIRECTORY_PROPERTY, "no/such/directory");
        try {
            assertTrue(SampleBook.sampleBookText().length() > 10_000);
        } finally {
            restoreProperty(original);
        }
    }

    @Test
    void sampleTokenizedBooksAlwaysReturnTheRequestedCount() {
        String original = System.getProperty(BODIES_DIRECTORY_PROPERTY);
        System.setProperty(BODIES_DIRECTORY_PROPERTY, "no/such/directory");
        try {
            Map<Integer, List<String>> books = SampleBook.sampleTokenizedBooks(3);
            assertTrue(books.size() == 3);
            assertFalse(books.get(1).isEmpty());
            assertTrue(books.get(1).size() > 100);
        } finally {
            restoreProperty(original);
        }
    }

    private static void restoreProperty(String original) {
        if (original == null) {
            System.clearProperty(BODIES_DIRECTORY_PROPERTY);
        } else {
            System.setProperty(BODIES_DIRECTORY_PROPERTY, original);
        }
    }
}
