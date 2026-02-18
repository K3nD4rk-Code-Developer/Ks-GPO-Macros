#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{Manager, PhysicalPosition};
use std::process::{Command, Child, Stdio};
use std::sync::Mutex;
use std::path::PathBuf;
use std::fs::{self, OpenOptions};
use std::io::Write;

struct PythonProcess(Mutex<Option<Child>>);

fn get_logs_dir() -> PathBuf {
    let logs_dir = PathBuf::from("logs");
    if !logs_dir.exists() {
        let _ = fs::create_dir_all(&logs_dir);
    }
    logs_dir
}

fn log_to_file(message: &str) {
    let log_path = get_logs_dir().join("debug.txt");
    if let Ok(mut file) = OpenOptions::new()
        .create(true)
        .append(true)
        .open(log_path)
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

#[allow(unused_variables)]
fn get_python_and_script(app: &tauri::AppHandle) -> (PathBuf, PathBuf) {
    #[cfg(debug_assertions)]
    {
        (PathBuf::from("python"), PathBuf::from("backend.py"))
    }

    #[cfg(not(debug_assertions))]
    {
        let resource_path = app
            .path()
            .resource_dir()
            .expect("Failed to get resource directory");

        let python_exe = resource_path
            .join("Python314")
            .join("pythonw.exe");

        let script = resource_path.join("backend.py");

        (python_exe, script)
    }
}

fn kill_existing_backend() {
    log_to_file("Killing any existing backend processes...");

    #[cfg(target_os = "windows")]
    {
        let _ = Command::new("wmic")
            .args(&["process", "where", "CommandLine like '%backend.py%'", "delete"])
            .output();
        std::thread::sleep(std::time::Duration::from_millis(500));
    }

    #[cfg(not(target_os = "windows"))]
    {
        let _ = Command::new("pkill")
            .args(&["-f", "backend.py"])
            .output();
        std::thread::sleep(std::time::Duration::from_millis(500));
    }

    log_to_file("Existing backend processes killed.");
}

fn read_backend_port(resource_dir: &PathBuf, pid: u32) -> u16 {
    let port_file = resource_dir.join(format!("port_{}.json", pid));
    log_to_file(&format!("Looking for port file: {:?}", port_file));

    for attempt in 1..=20 {
        if let Ok(content) = std::fs::read_to_string(&port_file) {
            if let Ok(val) = serde_json::from_str::<serde_json::Value>(&content) {
                if let Some(port) = val.get("port").and_then(|p| p.as_u64()) {
                    log_to_file(&format!("Found port {} on attempt {}", port, attempt));
                    return port as u16;
                }
            }
        }
        log_to_file(&format!("Port file not ready yet (attempt {}/20), retrying...", attempt));
        std::thread::sleep(std::time::Duration::from_millis(500));
    }

    log_to_file("WARNING: Could not read port file, falling back to 8765");
    8765
}

fn wait_for_backend(port: u16) -> bool {
    log_to_file(&format!("Starting backend healthcheck on port {}...", port));
    let client = reqwest::blocking::Client::new();
    let max_attempts = 30;
    
    for i in 0..max_attempts {
        std::thread::sleep(std::time::Duration::from_millis(500));
        
        match client.get(&format!("http://localhost:{}/health", port)).send() {
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
    let logs_dir = get_logs_dir();
    let _ = std::fs::remove_file(logs_dir.join("debug.txt"));
    log_to_file("=== APP STARTING ===");

    let launcher_pid = std::process::id();
    log_to_file(&format!("Launcher PID: {}", launcher_pid));
    
    tauri::Builder::default()
        .setup(move |app| {
            log_to_file("In setup function");
            kill_existing_backend();

            let resource_dir = {
                #[cfg(not(debug_assertions))]
                {
                    app.path().resource_dir().expect("Failed to get resource directory")
                }
                #[cfg(debug_assertions)]
                {
                    std::env::current_dir().expect("Failed to get current dir")
                }
            };

            log_to_file(&format!("Resource dir: {:?}", resource_dir));

            let python_process = if cfg!(debug_assertions) {
                log_to_file("DEBUG MODE");
                
                #[cfg(target_os = "windows")]
                let python_cmd = "python";
                
                #[cfg(not(target_os = "windows"))]
                let python_cmd = "python3";
                
                match Command::new(python_cmd)
                    .arg("backend.py")
                    .arg("--pid")
                    .arg(launcher_pid.to_string())
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
                
                let production_logs_dir = resource_dir.join("logs");
                let _ = fs::create_dir_all(&production_logs_dir);
                
                let stdout_log = production_logs_dir.join("python_stdout.txt");
                let stderr_log = production_logs_dir.join("python_stderr.txt");
                
                let stdout_file = std::fs::File::create(&stdout_log)
                    .expect("Failed to create stdout log");
                let stderr_file = std::fs::File::create(&stderr_log)
                    .expect("Failed to create stderr log");
                
                match Command::new(&python_exe)
                    .arg(&script)
                    .arg("--pid")
                    .arg(launcher_pid.to_string())
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

            let backend_port = read_backend_port(&resource_dir, launcher_pid);
            log_to_file(&format!("This instance will use port {}", backend_port));

            if !wait_for_backend(backend_port) {
                log_to_file("PANIC: Backend didn't start in time");
                
                let stderr_log = resource_dir.join("logs").join("python_stderr.txt");
                if let Ok(errors) = std::fs::read_to_string(&stderr_log) {
                    log_to_file(&format!("Python errors: {}", errors));
                }
                
                panic!("Backend failed to start within 15 seconds!");
            }
            
            log_to_file("Backend is running!");

            let main_window = app.get_webview_window("main").unwrap();

            main_window
                .eval(&format!(
                    "window.__LAUNCHER_PID__ = '{}'; window.__BACKEND_PORT__ = {};",
                    launcher_pid, backend_port
                ))
                .expect("Failed to inject launcher globals");

            if let Ok(Some(monitor)) = main_window.current_monitor() {
                let monitor_size = monitor.size();
                let scale = monitor.scale_factor();
                let width = (monitor_size.width as f64 / scale * 0.365) as u32;
                let height = (monitor_size.height as f64 / scale * 0.475) as u32;
                let _ = main_window.set_size(tauri::LogicalSize::new(width, height));
                let _ = main_window.center();
            }

            let main_window_clone = main_window.clone();
            std::thread::spawn(move || {
                let client = reqwest::blocking::Client::new();
                loop {
                    std::thread::sleep(std::time::Duration::from_secs(1));
                    
                    if let Ok(response) = client
                        .get(&format!("http://localhost:{}/state", backend_port))
                        .send()
                    {
                        if let Ok(state) = response.json::<serde_json::Value>() {
                            if let Some(always_on_top) = state
                                .get("alwaysOnTop")
                                .and_then(|v| v.as_bool())
                            {
                                let _ = main_window_clone.set_always_on_top(always_on_top);
                            }
                        }
                    }
                }
            });

            let stats_window = app.get_webview_window("stats");

            if let Some(stats_win) = stats_window {
                if let Ok(Some(monitor)) = stats_win.current_monitor() {
                    let monitor_size = monitor.size();
                    let scale = monitor.scale_factor();
                    let width = (monitor_size.width as f64 / scale * 0.125) as u32;
                    let height = (monitor_size.height as f64 / scale * 0.1) as u32;
                    let _ = stats_win.set_size(tauri::LogicalSize::new(width, height));

                    let store = tauri_plugin_store::StoreBuilder::new(app.handle(), "stats_position.json")
                        .build()
                        .expect("Failed to build store");

                    if let (Some(x), Some(y)) = (
                        store.get("x").and_then(|v: serde_json::Value| v.as_i64()),
                        store.get("y").and_then(|v: serde_json::Value| v.as_i64()),
                    ) {
                        let _ = stats_win.set_position(PhysicalPosition::new(x as i32, y as i32));
                    } else {
                        let screen_width = monitor_size.width as i32;
                        let window_width = (width as f64 * scale) as i32;
                        let x = (screen_width - window_width) / 2;
                        let _ = stats_win.set_position(PhysicalPosition::new(x, 20));
                    }
                }

                let stats_win_clone = stats_win.clone();
                stats_win.on_window_event(move |event| {
                    if let tauri::WindowEvent::Moved(pos) = event {
                        if let Ok(store) = tauri_plugin_store::StoreBuilder::new(
                            stats_win_clone.app_handle(),
                            "stats_position.json",
                        )
                        .build()
                        {
                            store.set("x", serde_json::json!(pos.x));
                            store.set("y", serde_json::json!(pos.y));
                            let _ = store.save();
                        }
                    }
                });
                
                std::thread::spawn(move || {
                    let client = reqwest::blocking::Client::new();
                    std::thread::sleep(std::time::Duration::from_secs(2));

                    loop {
                        std::thread::sleep(std::time::Duration::from_secs(1));

                        if let Ok(response) = client
                            .get(&format!("http://localhost:{}/state", backend_port))
                            .send()
                        {
                            if let Ok(state) = response.json::<serde_json::Value>() {
                                let show_debug = state
                                    .get("showDebugOverlay")
                                    .and_then(|v| v.as_bool())
                                    .unwrap_or(false);

                                if show_debug {
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
        .on_window_event(move |window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                if window.label() == "main" {

                    api.prevent_close();

                    let app_handle = window.app_handle().clone();

                    let resource_dir_for_cleanup = {
                        #[cfg(not(debug_assertions))]
                        { app_handle.path().resource_dir().ok() }
                        #[cfg(debug_assertions)]
                        { std::env::current_dir().ok() }
                    };

                    if let Some(dir) = &resource_dir_for_cleanup {
                        let port_file = dir.join(format!("port_{}.json", launcher_pid));
                        let _ = std::fs::remove_file(&port_file);
                        log_to_file(&format!("Cleaned up port file for PID {}", launcher_pid));
                    }

                    std::thread::spawn(move || {
                        if let Some(process) = app_handle.try_state::<PythonProcess>() {
                            if let Ok(mut process_guard) = process.0.lock() {
                                if let Some(mut child) = process_guard.take() {
                                    #[cfg(target_os = "windows")]
                                    {
                                        let pid = child.id();
                                        let _ = Command::new("taskkill")
                                            .args(&["/F", "/T", "/PID", &pid.to_string()])
                                            .output();
                                    }
                                    #[cfg(not(target_os = "windows"))]
                                    { let _ = child.kill(); }
                                    let _ = child.wait();
                                    log_to_file("Backend terminated");
                                }
                            }
                        }
                        log_to_file("Exiting application...");
                        app_handle.exit(0);
                    });
                }
            }
        })
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_store::Builder::default().build())
        .invoke_handler(tauri::generate_handler![send_to_python])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}