#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{Manager, PhysicalPosition};
use std::process::{Command, Child};
use std::sync::Mutex;

struct PythonProcess(Mutex<Option<Child>>);

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

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            #[cfg(target_os = "windows")]
            let python_cmd = "python";
            
            #[cfg(not(target_os = "windows"))]
            let python_cmd = "python3";
            
            let python_process = Command::new(python_cmd)
                .arg("backend.py")
                .spawn()
                .expect("Failed to start Python backend");
            
            app.manage(PythonProcess(Mutex::new(Some(python_process))));
            
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
                                    // Center at top of screen
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
            
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                // Kill Python process when main window is closed
                if window.label() == "main" {
                    if let Some(python_process) = window.app_handle().try_state::<PythonProcess>() {
                        if let Ok(mut process_guard) = python_process.0.lock() {
                            if let Some(mut child) = process_guard.take() {
                                let _ = child.kill();
                                let _ = child.wait();
                                println!("Python backend terminated");
                            }
                        }
                    }
                }
            }
        })
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![send_to_python])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}