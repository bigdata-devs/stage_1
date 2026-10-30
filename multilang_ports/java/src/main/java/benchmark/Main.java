package benchmark;

import java.io.IOException;
import java.nio.file.Path;
import java.util.Arrays;

public final class Main {

    private static final String USAGE = "Usage: java benchmark.Main bench [flags]\n"
        + "       java benchmark.Main equivalence <bodies_dir> <book_ids_file> <queries_file> <output_file>";

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
        if (args.length == 5 && args[0].equals("equivalence")) {
            Equivalence.run(Path.of(args[1]), Path.of(args[2]), Path.of(args[3]),
                Path.of(args[4]));
            return;
        }
        throw new IllegalArgumentException(USAGE);
    }
}
