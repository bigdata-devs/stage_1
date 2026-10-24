package benchmark;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Locale;

final class Log {

    private static final DateTimeFormatter STAMP = DateTimeFormatter.ofPattern("yyyy/MM/dd HH:mm:ss");

    private Log() {
    }

    static void line(String format, Object... args) {
        System.out.println(LocalDateTime.now().format(STAMP) + " "
            + String.format(Locale.ROOT, format, args));
    }
}
