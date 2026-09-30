use search_engine_bench::benchmark::{BenchResult, Config, Suite};
use std::process::ExitCode;

fn main() -> ExitCode {
    match run_benchmark() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("benchmark failed: {error}");
            ExitCode::FAILURE
        }
    }
}

fn run_benchmark() -> BenchResult<()> {
    let config = Config::parse(&benchmark_arguments())?;
    Suite::new(config).run()
}

fn benchmark_arguments() -> Vec<String> {
    let mut arguments: Vec<String> = std::env::args().skip(1).collect();
    if arguments.first().map(String::as_str) == Some("bench") {
        arguments.remove(0);
    }
    arguments
}
