use std::fs::{self, File};
use std::io::{Read, Write};
use std::net::TcpStream;
use std::path::{Path, PathBuf};

const SERVER: &str = "localhost:8000";
const BOUNDARY: &str = "----RustBoundary123456";
const UPLOAD_PATHS: [&str; 1] = ["private/passwords.txt"]; // Adjust this

fn collect_files(paths: &[&str]) -> Vec<PathBuf> {
    let mut files = Vec::new();
    for path in paths {
        let path = Path::new(path);
        if path.is_dir() {
            for entry in fs::read_dir(path).unwrap() {
                let entry = entry.unwrap();
                let subpath = entry.path();
                if subpath.is_file() {
                    files.push(subpath);
                } else if subpath.is_dir() {
                    files.extend(collect_files(&[subpath.to_str().unwrap()]));
                }
            }
        } else if path.is_file() {
            files.push(path.to_path_buf());
        }
    }
    files
}

fn send_file(file_path: &Path) -> std::io::Result<()> {
    let mut file = File::open(file_path)?;
    let mut buffer = Vec::new();
    file.read_to_end(&mut buffer)?;

    let filename = file_path.file_name().unwrap().to_str().unwrap();
    let content_type = "application/octet-stream"; // Basic MIME type

    let mut body = Vec::new();
    write!(
        body,
        "--{}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{}\"\r\nContent-Type: {}\r\n\r\n",
        BOUNDARY, filename, content_type
    )?;
    body.extend(&buffer);
    write!(body, "\r\n--{}--\r\n", BOUNDARY)?;

    let request = format!(
        "POST /upload HTTP/1.1\r\n\
         Host: localhost\r\n\
         Content-Type: multipart/form-data; boundary={}\r\n\
         Content-Length: {}\r\n\
         Connection: close\r\n\r\n",
        BOUNDARY,
        body.len()
    );

    let mut stream = TcpStream::connect(SERVER)?;
    stream.write_all(request.as_bytes())?;
    stream.write_all(&body)?;

    let mut response = String::new();
    stream.read_to_string(&mut response)?;
    println!("Server Response: {}", response);
    Ok(())
}

fn main() {
    let files = collect_files(&UPLOAD_PATHS);
    for file in files {
        if let Err(e) = send_file(&file) {
            eprintln!("Failed to upload {}: {}", file.display(), e);
        }
    }

    // After all uploads, send metadata
    let metadata = "{\"files_meta\":[]}";
    let request = format!(
        "POST /create-meta HTTP/1.1\r\n\
         Host: localhost\r\n\
         Content-Type: application/json\r\n\
         Content-Length: {}\r\n\
         Connection: close\r\n\r\n{}",
        metadata.len(),
        metadata
    );

    if let Ok(mut stream) = TcpStream::connect(SERVER) {
        let _ = stream.write_all(request.as_bytes());
        let mut response = String::new();
        let _ = stream.read_to_string(&mut response);
        println!("Meta Response: {}", response);
    }
}
