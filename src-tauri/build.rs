#![allow(non_snake_case)]

use std::path::PathBuf;
use std::fs;
use std::env;

#[allow(unused_imports)]
use winres::WindowsResource;

const SKIP_DIRS: &[&str] = &[
    "__pycache__",
    ".git",
    "Doc",
    "docs", 
    "Tools",
    "tools",
    "Scripts",
    "test",
    "tests",
    "turtledemo",
    "idle",
    "idlelib",
    "ensurepip",
];

const SKIP_EXTENSIONS: &[&str] = &[
    "pyc",
    "pyo",
    "pyd.bak",
];

const SKIP_ROOT_FILES: &[&str] = &[
    "NEWS.txt",
    "LICENSE.txt",
    "README.txt",
    "CHANGES",
    "NOTICE",
];

const SKIP_STDLIB_MODULES: &[&str] = &[
    "test",
    "tests",
    "turtle.py",
    "turtledemo",
    "mailbox.py",
    "mailcap.py",
    "imaplib.py",
    "smtplib.py",
    "smtpd.py",
    "ftplib.py",
    "poplib.py",
    "nntplib.py",
    "telnetlib.py",
    "xmlrpc",
    "wsgiref",
    "lzma.py",
    "bz2.py",
    "cgi.py",
    "cgitb.py",
    "antigravity.py",
    "this.py",
    "formatter.py",
    "imghdr.py",
    "sunau.py",
    "aifc.py",
    "chunk.py",
    "sndhdr.py",
    "msilib",
    "distutils",
    "lib2to3",
    "pydoc_data",
    "venv",
    "zipapp.py",
    "pickletools.py",
    "profile.py",
    "pstats.py",
    "cProfile.py",
    "timeit.py",
    "tabnanny.py",
    "compileall.py",
    "py_compile.py",
];

fn ShouldSkipDir(Name: &str) -> bool {
    let Lower = Name.to_lowercase();
    SKIP_DIRS.iter().any(|S| Lower == S.to_lowercase())
}

fn ShouldSkipFile(Name: &str, Extension: Option<&str>) -> bool {
    if let Some(Ext) = Extension {
        if SKIP_EXTENSIONS.iter().any(|S| Ext.eq_ignore_ascii_case(S)) {
            return true;
        }
    }
    false
}

fn ShouldSkipRootFile(Name: &str) -> bool {
    SKIP_ROOT_FILES.iter().any(|S| Name.eq_ignore_ascii_case(S))
}

fn ShouldSkipStdlibEntry(Name: &str) -> bool {
    SKIP_STDLIB_MODULES.iter().any(|S| Name.eq_ignore_ascii_case(S))
}

fn CopyDirectoryRecursive(
    Source: &PathBuf,
    Destination: &PathBuf,
    IsLib: bool,
) -> std::io::Result<()> {
    if !Destination.exists() {
        fs::create_dir_all(Destination)?;
    }

    for Entry in fs::read_dir(Source)? {
        let Entry = Entry?;
        let SourcePath = Entry.path();
        let FileName = Entry.file_name();
        let NameStr = FileName.to_string_lossy();

        if SourcePath.is_dir() {
            if ShouldSkipDir(&NameStr) {
                continue;
            }
            if IsLib && ShouldSkipStdlibEntry(&NameStr) {
                continue;
            }

            let DestPath = Destination.join(&FileName);
            let NextIsLib = IsLib && NameStr.to_lowercase() != "site-packages";
            CopyDirectoryRecursive(&SourcePath, &DestPath, NextIsLib)?;

        } else {
            let Extension = SourcePath
                .extension()
                .and_then(|E| E.to_str());

            if ShouldSkipFile(&NameStr, Extension) {
                continue;
            }
            if ShouldSkipRootFile(&NameStr) {
                continue;
            }
            if IsLib && ShouldSkipStdlibEntry(&NameStr) {
                continue;
            }

            let DestPath = Destination.join(&FileName);
            fs::copy(&SourcePath, &DestPath)?;
        }
    }
    Ok(())
}

fn CompileBackendPyc(PythonExe: &PathBuf, BackendPy: &PathBuf) {
    if !BackendPy.exists() {
        println!("cargo:warning=backend.py not found at {:?} — skipping pyc compile", BackendPy);
        return;
    }

    println!("cargo:warning=Compiling backend.py → .pyc ...");

    let BackendPyStr  = BackendPy.to_string_lossy();
    let BackendPycStr = BackendPy.with_extension("pyc").to_string_lossy().into_owned();

    let Script = format!(
        "import py_compile; py_compile.compile(r'{}', cfile=r'{}', optimize=2, doraise=True)",
        BackendPyStr, BackendPycStr
    );

    let Output = std::process::Command::new(PythonExe)
        .args(["-c", &Script])
        .output();

    match Output {
        Ok(Out) => {
            if Out.status.success() {
                println!("cargo:warning=backend.pyc written to {:?}", BackendPycStr);

                if let Err(E) = fs::remove_file(BackendPy) {
                    println!("cargo:warning=Could not remove backend.py: {}", E);
                } else {
                    println!("cargo:warning=backend.py removed from output (only .pyc ships)");
                }
            } else {
                let Stderr = String::from_utf8_lossy(&Out.stderr);
                println!("cargo:warning=py_compile failed: {}", Stderr);
                println!("cargo:warning=backend.py will ship uncompiled");
            }
        }
        Err(E) => {
            println!("cargo:warning=Could not launch Python to compile backend.py: {}", E);
            println!("cargo:warning=backend.py will ship uncompiled");
        }
    }
}

fn HashRequirements(Path: &PathBuf) -> String {
    let Contents = fs::read_to_string(Path).unwrap_or_default();
    let mut Hash: u64 = 0xcbf29ce484222325;
    for Byte in Contents.bytes() {
        Hash ^= Byte as u64;
        Hash = Hash.wrapping_mul(0x100000001b3);
    }
    format!("{:016x}", Hash)
}

fn main() {
    if cfg!(target_os = "windows") {
        let mut ResourceBuilder = winres::WindowsResource::new();
        ResourceBuilder.set_icon("icons/icon.ico");
        ResourceBuilder.compile().unwrap();
    }

    let BuildProfile          = env::var("PROFILE").unwrap_or_default();
    let SrcTauriPath          = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
    let PythonDestinationPath = SrcTauriPath.join("Python314");
    let RequirementsPath      = SrcTauriPath.parent().unwrap().join("requirements.txt");
    let SavedHashesDir        = SrcTauriPath.join("saved-hashes");
    let LatestHashFile        = SavedHashesDir.join("latest.txt");

    println!("cargo:rerun-if-changed=build.rs");
    println!("cargo:rerun-if-changed=../requirements.txt");

    if BuildProfile == "release" {
        let PythonSourcePath = PathBuf::from(
            r"C:\Users\zomrd\AppData\Local\Programs\Python\Python314"
        );

        if !PythonSourcePath.exists() {
            panic!("Python source directory not found at: {:?}", PythonSourcePath);
        }

        fs::create_dir_all(&SavedHashesDir)
            .expect("Failed to create saved-hashes directory");

        let CurrentHash = HashRequirements(&RequirementsPath);
        let SavedHash   = fs::read_to_string(&LatestHashFile).unwrap_or_default();

        println!("cargo:warning=Requirements hash (current): {}", CurrentHash);
        println!("cargo:warning=Requirements hash (saved):   {}", SavedHash.trim());

        let HashChanged   = SavedHash.trim() != CurrentHash;
        let PythonMissing = !PythonDestinationPath.exists();

        if HashChanged || PythonMissing {
            if HashChanged {
                println!("cargo:warning=requirements.txt changed — re-copying Python...");
            } else {
                println!("cargo:warning=Python314 folder missing — copying Python...");
            }

            if PythonDestinationPath.exists() {
                fs::remove_dir_all(&PythonDestinationPath)
                    .expect("Failed to remove old Python314 directory");
            }

            for Entry in fs::read_dir(&PythonSourcePath)
                .expect("Failed to read Python source directory")
            {
                let Entry = Entry.expect("Failed to read directory entry");
                let SourceEntry = Entry.path();
                let EntryName   = Entry.file_name();
                let NameStr     = EntryName.to_string_lossy();
                let DestEntry   = PythonDestinationPath.join(&EntryName);

                if SourceEntry.is_dir() {
                    if ShouldSkipDir(&NameStr) {
                        continue;
                    }
                    let IsLib = NameStr.eq_ignore_ascii_case("Lib");
                    CopyDirectoryRecursive(&SourceEntry, &DestEntry, IsLib)
                        .unwrap_or_else(|E| panic!("Failed to copy {}: {}", NameStr, E));
                } else {
                    let Ext = SourceEntry.extension().and_then(|E| E.to_str());
                    if ShouldSkipFile(&NameStr, Ext) || ShouldSkipRootFile(&NameStr) {
                        continue;
                    }
                    fs::copy(&SourceEntry, &DestEntry)
                        .unwrap_or_else(|E| panic!("Failed to copy file {}: {}", NameStr, E));
                }
            }

            fs::write(&LatestHashFile, &CurrentHash)
                .expect("Failed to write latest hash to saved-hashes/latest.txt");

            println!("cargo:warning=Python copied successfully. Hash saved: {}", CurrentHash);

        } else {
            println!("cargo:warning=requirements.txt unchanged — skipping Python copy.");
        }

        let ProjectRoot = SrcTauriPath.parent().unwrap();
        let BackendPy   = ProjectRoot.join("backend.py");
        let PythonExe   = PythonDestinationPath.join("python.exe");

        println!("cargo:rerun-if-changed=../backend.py");

        CompileBackendPyc(&PythonExe, &BackendPy);

    } else {
        if !PythonDestinationPath.exists() {
            fs::create_dir_all(&PythonDestinationPath)
                .expect("Failed to create Python314 placeholder directory");
        }
    }

    tauri_build::build();
}