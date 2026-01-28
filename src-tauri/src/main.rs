#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{Manager, PhysicalPosition};
use std::process::{Command, Child, Stdio};
use std::sync::Mutex;
use std::path::PathBuf;
use std::fs::OpenOptions;
use std::io::Write;

struct PythonProcess(Mutex<Option<Child>>);

fn log_to_file(message: &str) {
    if let Ok(mut file) = OpenOptions::new()
        .create(true)
        .append(true)
        .open("debug.log")
    {
        let _ = writeln!(file, "{}", message);
    }
}

#[tauri::command]
fn send_to_python(action: String, payload: String) -> Result<String, String> {
    let client = reqwest::blocking::Client::new();
    
    match client.post("http://localhost:8765/command")
        .json(&serde_json::json!({
            "action": action,
            "payload": payload
        }))
        .send()
    {
        Ok(_) => Ok("Success".to_string()),
        Err(e) => Err(e.to_string())
    }
}

fn get_python_and_script(app: &tauri::AppHandle) -> (PathBuf, PathBuf) {
    #[cfg(debug_assertions)]
    {
        (PathBuf::from("python"), PathBuf::from("backend.py"))
    }
    
    #[cfg(not(debug_assertions))]
    {
        let resource_path = app.path().resource_dir()
            .expect("Failed to get resource directory");
        let python_exe = resource_path.join("python-embed").join("pythonw.exe");
        let script = resource_path.join("backend.py");
        (python_exe, script)
    }
}

fn wait_for_backend() -> bool {
    log_to_file("Starting backend healthcheck...");
    let client = reqwest::blocking::Client::new();
    let max_attempts = 30;
    
    for i in 0..max_attempts {
        std::thread::sleep(std::time::Duration::from_millis(500));
        
        match client.get("http://localhost:8765/health").send() {
            Ok(_) => {
                log_to_file(&format!("Backend ready after {} attempts", i + 1));
                return true;
            }
            Err(e) => {
                log_to_file(&format!("Attempt {}/{}: {}", i + 1, max_attempts, e));
            }
        }
    }
    
    log_to_file("Backend failed to start!");
    false
}

fn main() {
    let _ = std::fs::remove_file("debug.log");
    log_to_file("=== APP STARTING ===");
    
    tauri::Builder::default()
        .setup(|app| {
            log_to_file("In setup function");
            
            let python_process = if cfg!(debug_assertions) {
                log_to_file("DEBUG MODE");
                
                #[cfg(target_os = "windows")]
                let python_cmd = "python";
                
                #[cfg(not(target_os = "windows"))]
                let python_cmd = "python3";
                
                match Command::new(python_cmd)
                    .arg("backend.py")
                    .spawn()
                {
                    Ok(child) => {
                        log_to_file("Python backend started in debug mode");
                        child
                    }
                    Err(e) => {
                        log_to_file(&format!("Failed to start debug backend: {}", e));
                        panic!("Failed to start Python backend: {}", e);
                    }
                }
            } else {
                log_to_file("PRODUCTION MODE");
                
                let (python_exe, script) = get_python_and_script(&app.handle());
                let resource_dir = app.path().resource_dir().unwrap();
                
                log_to_file(&format!("Python exe: {:?}", python_exe));
                log_to_file(&format!("Script: {:?}", script));
                log_to_file(&format!("Python exists: {}", python_exe.exists()));
                log_to_file(&format!("Script exists: {}", script.exists()));
                
                if !python_exe.exists() {
                    log_to_file("ERROR: Python executable not found!");
                    panic!("Python executable not found at: {:?}", python_exe);
                }
                
                if !script.exists() {
                    log_to_file("ERROR: Backend script not found!");
                    panic!("Backend script not found at: {:?}", script);
                }
                
                log_to_file(&format!("Working directory: {:?}", resource_dir));
                
                let stdout_log = resource_dir.join("python_stdout.log");
                let stderr_log = resource_dir.join("python_stderr.log");
                
                log_to_file(&format!("Python stdout will be in: {:?}", stdout_log));
                log_to_file(&format!("Python stderr will be in: {:?}", stderr_log));
                
                let stdout_file = std::fs::File::create(&stdout_log)
                    .expect("Failed to create stdout log");
                let stderr_file = std::fs::File::create(&stderr_log)
                    .expect("Failed to create stderr log");
                
                match Command::new(&python_exe)
                    .arg(&script)
                    .current_dir(&resource_dir)
                    .stdout(Stdio::from(stdout_file))
                    .stderr(Stdio::from(stderr_file))
                    .spawn()
                {
                    Ok(child) => {
                        log_to_file("Python backend spawned successfully");
                        child
                    }
                    Err(e) => {
                        log_to_file(&format!("Failed to spawn backend: {}", e));
                        panic!("Failed to start Python backend: {}", e);
                    }
                }
            };
            
            app.manage(PythonProcess(Mutex::new(Some(python_process))));
            
            log_to_file("Waiting for backend...");
            if !wait_for_backend() {
                log_to_file("PANIC: Backend didn't start in time");
                
                let resource_dir = app.path().resource_dir().unwrap();
                let stderr_log = resource_dir.join("python_stderr.log");
                if let Ok(errors) = std::fs::read_to_string(&stderr_log) {
                    log_to_file(&format!("Python errors: {}", errors));
                }
                
                panic!("Backend failed to start within 15 seconds!");
            }
            
            log_to_file("Backend is running!");
            
            let main_window = app.get_webview_window("main").unwrap();
            let stats_window = app.get_webview_window("stats");
            
            let main_window_clone = main_window.clone();
            std::thread::spawn(move || {
                let client = reqwest::blocking::Client::new();
                loop {
                    std::thread::sleep(std::time::Duration::from_secs(1));
                    
                    if let Ok(response) = client.get("http://localhost:8765/state").send() {
                        if let Ok(state) = response.json::<serde_json::Value>() {
                            if let Some(always_on_top) = state.get("alwaysOnTop").and_then(|v| v.as_bool()) {
                                let _ = main_window_clone.set_always_on_top(always_on_top);
                            }
                        }
                    }
                }
            });
            
            if let Some(stats_win) = stats_window {
                std::thread::spawn(move || {
                    let client = reqwest::blocking::Client::new();
                    std::thread::sleep(std::time::Duration::from_secs(2));
                    
                    loop {
                        std::thread::sleep(std::time::Duration::from_secs(1));
                        
                        if let Ok(response) = client.get("http://localhost:8765/state").send() {
                            if let Ok(state) = response.json::<serde_json::Value>() {
                                let is_running = state.get("isRunning").and_then(|v| v.as_bool()).unwrap_or(false);
                                let show_debug = state.get("showDebugOverlay").and_then(|v| v.as_bool()).unwrap_or(false);
                                
                                if is_running && show_debug {
                                    if let Ok(monitor) = stats_win.current_monitor() {
                                        if let Some(monitor) = monitor {
                                            if let Ok(size) = stats_win.outer_size() {
                                                let screen_width = monitor.size().width as i32;
                                                let window_width = size.width as i32;
                                                let x = (screen_width - window_width) / 2;
                                                let _ = stats_win.set_position(PhysicalPosition::new(x, 20));
                                            }
                                        }
                                    }
                                    let _ = stats_win.show();
                                } else {
                                    let _ = stats_win.hide();
                                }
                            }
                        }
                    }
                });
            }
            
            log_to_file("Setup complete!");
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                if window.label() == "main" {
                    log_to_file("Main window close requested, terminating backend...");
                    
                    // Prevent the window from closing immediately
                    api.prevent_close();
                    
                    let app_handle = window.app_handle().clone();
                    
                    // Spawn a thread to handle cleanup
                    std::thread::spawn(move || {
                        if let Some(python_process) = app_handle.try_state::<PythonProcess>() {
                            if let Ok(mut process_guard) = python_process.0.lock() {
                                if let Some(mut child) = process_guard.take() {
                                    #[cfg(target_os = "windows")]
                                    {
                                        let pid = child.id();
                                        log_to_file(&format!("Killing Python process PID: {}", pid));
                                        let _ = Command::new("taskkill")
                                            .args(&["/F", "/T", "/PID", &pid.to_string()])
                                            .output();
                                    }
                                    
                                    #[cfg(not(target_os = "windows"))]
                                    {
                                        let _ = child.kill();
                                    }
                                    
                                    let _ = child.wait();
                                    log_to_file("Backend terminated");
                                }
                            }
                        }
                        
                        // Now exit the app
                        log_to_file("Exiting application...");
                        app_handle.exit(0);
                    });
                }
            }
        })
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![send_to_python])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}