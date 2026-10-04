use super::BenchResult;
use std::fs;
use std::path::Path;

const BYTES_PER_MB: f64 = 1024.0 * 1024.0;

pub struct DiskUsage {
    pub path: String,
    pub size_mb: f64,
    pub file_count: u64,
    pub dir_count: u64,
}

impl DiskUsage {
    pub fn measure(path: &Path) -> BenchResult<Self> {
        if !path.exists() {
            return Err(format!("path does not exist: {}", path.display()).into());
        }
        if !path.is_dir() {
            return Ok(Self {
                path: path.display().to_string(),
                size_mb: fs::metadata(path)?.len() as f64 / BYTES_PER_MB,
                file_count: 1,
                dir_count: 0,
            });
        }
        let mut usage = Self {
            path: path.display().to_string(),
            size_mb: 0.0,
            file_count: 0,
            dir_count: 0,
        };
        accumulate(path, &mut usage)?;
        Ok(usage)
    }
}

fn accumulate(directory: &Path, usage: &mut DiskUsage) -> BenchResult<()> {
    for entry in fs::read_dir(directory)? {
        let path = entry?.path();
        if path.is_dir() {
            usage.dir_count += 1;
            accumulate(&path, usage)?;
        } else {
            usage.file_count += 1;
            usage.size_mb += fs::metadata(&path)?.len() as f64 / BYTES_PER_MB;
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    fn temp_dir(label: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!(
            "stage1_rust_disk_{label}_{}",
            std::process::id()
        ));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        dir
    }

    #[test]
    fn single_file_has_one_file_and_no_directories() {
        let dir = temp_dir("file");
        let file = dir.join("index.json");
        fs::write(&file, "0123456789").unwrap();
        let usage = DiskUsage::measure(&file).unwrap();
        assert_eq!(1, usage.file_count);
        assert_eq!(0, usage.dir_count);
        assert!((usage.size_mb - 10.0 / BYTES_PER_MB).abs() < 1e-12);
        fs::remove_dir_all(&dir).unwrap();
    }

    #[test]
    fn directory_tree_counts_files_and_subdirectories_but_not_the_root() {
        let dir = temp_dir("tree");
        fs::create_dir_all(dir.join("a/b")).unwrap();
        fs::write(dir.join("one.txt"), "abc").unwrap();
        fs::write(dir.join("a/two.txt"), "defg").unwrap();
        let usage = DiskUsage::measure(&dir).unwrap();
        assert_eq!(2, usage.file_count);
        assert_eq!(2, usage.dir_count);
        assert!((usage.size_mb - 7.0 / BYTES_PER_MB).abs() < 1e-12);
        fs::remove_dir_all(&dir).unwrap();
    }

    #[test]
    fn missing_path_is_rejected() {
        let dir = temp_dir("missing");
        assert!(DiskUsage::measure(&dir.join("absent")).is_err());
        fs::remove_dir_all(&dir).unwrap();
    }
}
