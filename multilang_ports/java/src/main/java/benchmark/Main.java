package benchmark;

import java.io.IOException;
import java.util.Arrays;

public final class Main {

    private static final String USAGE = "Usage: java benchmark.Main bench [flags]";

    public static void main(String[] args) {
        try {
            run(args);
        } catch (Exception exception) {
            System.err.println(exception.getMessage());
            System.exit(1);
        }
    }

    static void run(String[] args) throws IOException {
        if (args.length >= 1 && args[0].equals("bench")) {
            Config config = Config.parse(Arrays.copyOfRange(args, 1, args.length));
            new Suite(config).run();
            return;
        }
        throw new IllegalArgumentException(USAGE);
    }
}
