use std::path::PathBuf;
use std::fs;
use std::env;

#[allow(unused_imports)]
use winres::WindowsResource;

fn CopyDirectoryRecursive(Source: &PathBuf, Destination: &PathBuf) -> std::io::Result<()> {
    if !Destination.exists() {
        fs::create_dir_all(Destination)?;
    }
    
    for Entry in fs::read_dir(Source)? {
        let Entry = Entry?;
        let SourcePath = Entry.path();
        let DestinationPath = Destination.join(Entry.file_name());
        
        if SourcePath.is_dir() {
            let DirectoryName = Entry.file_name();
            let DirectoryNameString = DirectoryName.to_string_lossy();
            if DirectoryNameString == "__pycache__" || DirectoryNameString == ".git" {
                continue;
            }
            CopyDirectoryRecursive(&SourcePath, &DestinationPath)?;
        } else {
            if let Some(Extension) = SourcePath.extension() {
                if Extension == "pyc" {
                    continue;
                }
            }
            fs::copy(&SourcePath, &DestinationPath)?;
        }
    }
    Ok(())
}

fn main() {
    if cfg!(target_os = "windows") {
        let mut ResourceBuilder = winres::WindowsResource::new();
        ResourceBuilder.set_icon("icons/icon.ico");
        ResourceBuilder.compile().unwrap();
    }
    
    let BuildProfile = env::var("PROFILE").unwrap_or_default();
    let SrcTauriPath = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
    let PythonDestinationPath = SrcTauriPath.join("Python314");
    
    if BuildProfile == "release" {
        let PythonSourcePath = PathBuf::from(r"C:\Users\zomrd\AppData\Local\Programs\Python\Python314");
        
        println!("cargo:warning=============================================");
        println!("cargo:warning=Copying Python distribution for release build");
        println!("cargo:warning=From: {:?}", PythonSourcePath);
        println!("cargo:warning=To: {:?}", PythonDestinationPath);
        println!("cargo:warning=============================================");
        
        if !PythonSourcePath.exists() {
            println!("cargo:warning=ERROR: Python source directory not found!");
            println!("cargo:warning=Please ensure Python 3.14 is installed at the expected location");
            panic!("Python source directory not found at: {:?}", PythonSourcePath);
        }
        
        if PythonDestinationPath.exists() {
            println!("cargo:warning=Removing old Python copy...");
            if let Err(Error) = fs::remove_dir_all(&PythonDestinationPath) {
                println!("cargo:warning=Warning: Failed to remove old Python directory: {}", Error);
            }
        }
        
        println!("cargo:warning=Copying Python files (this may take a moment)...");
        match CopyDirectoryRecursive(&PythonSourcePath, &PythonDestinationPath) {
            Ok(_) => {
                println!("cargo:warning=Python copied successfully!");
                println!("cargo:warning=============================================");
            }
            Err(Error) => {
                println!("cargo:warning=ERROR: Failed to copy Python: {}", Error);
                panic!("Failed to copy Python distribution: {}", Error);
            }
        }
    } else {
        println!("cargo:warning=Debug build - creating placeholder Python314 directory");
        if !PythonDestinationPath.exists() {
            fs::create_dir_all(&PythonDestinationPath).unwrap();
            println!("cargo:warning=Placeholder directory created at {:?}", PythonDestinationPath);
        }
    }
    
    tauri_build::build();
}