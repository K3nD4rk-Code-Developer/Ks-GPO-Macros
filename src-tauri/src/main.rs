#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;

use tauri::{AppHandle, Manager, PhysicalPosition};

struct PythonProcess(Mutex<Option<Child>>);
struct BackendPort(Mutex<u16>);

fn logs_dir() -> PathBuf {
    let dir = PathBuf::from("logs");
    let _ = fs::create_dir_all(&dir);
    dir
}

fn log(msg: &str) {
    let path = logs_dir().join("debug.txt");
    if let Ok(mut f) = OpenOptions::new().create(true).append(true).open(path) {
        let _ = writeln!(f, "{msg}");
    }
    println!("[launcher] {msg}");
}

fn resource_dir(app: &AppHandle) -> PathBuf {
    #[cfg(not(debug_assertions))]
    {
        app.path().resource_dir().expect("Failed to get resource dir")
    }
    #[cfg(debug_assertions)]
    {
        let _ = app;
        std::env::current_dir().expect("Failed to get current dir")
    }
}

fn is_position_visible(x: i64, y: i64, app: &AppHandle) -> bool {
    if let Ok(monitors) = app.available_monitors() {
        for monitor in monitors {
            let pos  = monitor.position();
            let size = monitor.size();
            let mx = pos.x as i64;
            let my = pos.y as i64;
            let mw = size.width as i64;
            let mh = size.height as i64;
            if x >= mx && x < mx + mw && y >= my && y < my + mh {
                return true;
            }
        }
    }
    false
}

fn kill_existing_backend() {
    log("Killing existing backend processes");
    #[cfg(target_os = "windows")]
    {
        let _ = Command::new("wmic")
            .args(&["process", "where", "CommandLine like '%backend.py%'", "delete"])
            .output();
    }
    #[cfg(not(target_os = "windows"))]
    {
        let _ = Command::new("pkill").args(&["-f", "backend.py"]).output();
    }
    std::thread::sleep(std::time::Duration::from_millis(500));
    log("Existing backend processes killed");
}

fn kill_all_backend_processes(launcher_pid: u32) {
    log("Nuclear kill: all backend processes");
    #[cfg(target_os = "windows")]
    {
        let _ = Command::new("wmic")
            .args(&["process", "where", "CommandLine like '%backend.py%'", "delete"])
            .output();
        let pid_pattern = format!("CommandLine like '%--pid {}%'", launcher_pid);
        let _ = Command::new("wmic")
            .args(&["process", "where", &pid_pattern, "delete"])
            .output();
        let _ = Command::new("taskkill")
            .args(&["/F", "/IM", "pythonw.exe", "/T"])
            .output();
    }
    #[cfg(not(target_os = "windows"))]
    {
        let _ = Command::new("pkill").args(&["-f", "backend.py"]).output();
        let _ = Command::new("pkill")
            .args(&["-f", &format!("--pid {}", launcher_pid)])
            .output();
    }
    std::thread::sleep(std::time::Duration::from_millis(800));
    log("Nuclear kill complete");
}

#[cfg_attr(debug_assertions, allow(dead_code))]
fn spawn_backend_process(app: &AppHandle, launcher_pid: u32) -> Child {
    let res_dir = resource_dir(app);
    let python_exe = res_dir.join("Python314").join("pythonw.exe");
    let script = res_dir.join("backend.py");

    log(&format!("Python exe: {:?} (exists: {})", python_exe, python_exe.exists()));
    log(&format!("Script:     {:?} (exists: {})", script, script.exists()));

    if !python_exe.exists() {
        panic!("Python executable not found at: {:?}", python_exe);
    }
    if !script.exists() {
        panic!("Backend script not found at: {:?}", script);
    }

    let prod_logs = res_dir.join("logs");
    let _ = fs::create_dir_all(&prod_logs);

    let stdout_file = fs::File::create(prod_logs.join("python_stdout.txt"))
        .expect("Failed to create stdout log");
    let stderr_file = fs::File::create(prod_logs.join("python_stderr.txt"))
        .expect("Failed to create stderr log");

    Command::new(&python_exe)
        .arg(&script)
        .arg("--pid")
        .arg(launcher_pid.to_string())
        .current_dir(&res_dir)
        .stdout(Stdio::from(stdout_file))
        .stderr(Stdio::from(stderr_file))
        .spawn()
        .unwrap_or_else(|e| panic!("Failed to spawn backend: {e}"))
}

fn read_backend_port(res_dir: &PathBuf, pid: u32) -> u16 {
    let port_file = res_dir.join(format!("port_{pid}.json"));
    log(&format!("Looking for port file: {port_file:?}"));

    for attempt in 1..=20 {
        if let Ok(content) = fs::read_to_string(&port_file) {
            if let Ok(val) = serde_json::from_str::<serde_json::Value>(&content) {
                if let Some(port) = val.get("port").and_then(|p| p.as_u64()) {
                    log(&format!("Found port {port} on attempt {attempt}"));
                    return port as u16;
                }
            }
        }
        log(&format!("Port file not ready (attempt {attempt}/20), retrying..."));
        std::thread::sleep(std::time::Duration::from_millis(500));
    }

    log("WARNING: Could not read port file, falling back to 8765");
    8765
}

fn wait_for_backend(port: u16) -> bool {
    log(&format!("Waiting for backend on port {port}..."));
    let client = reqwest::blocking::Client::new();

    for i in 0..30 {
        std::thread::sleep(std::time::Duration::from_millis(500));
        if client
            .get(&format!("http://localhost:{port}/health"))
            .send()
            .is_ok()
        {
            log(&format!("Backend ready after {} attempts", i + 1));
            return true;
        }
        log(&format!("Health check attempt {}/{}", i + 1, 30));
    }

    log("Backend failed to start in time");
    false
}

fn store_child(app: &AppHandle, child: Child) {
    if let Some(proc) = app.try_state::<PythonProcess>() {
        if let Ok(mut guard) = proc.0.lock() {
            *guard = Some(child);
            log("Child process stored successfully");
        }
    }
}

fn inject_backend_globals(win: &tauri::WebviewWindow, pid: u32, port: u16) {
    let _ = win.eval(&format!(
        "window.__LAUNCHER_PID__ = '{}'; window.__BACKEND_PORT__ = {};",
        pid, port
    ));
}

fn terminate_child(app: &AppHandle) {
    if let Some(proc) = app.try_state::<PythonProcess>() {
        if let Ok(mut guard) = proc.0.lock() {
            if let Some(mut child) = guard.take() {
                log(&format!("Terminating child PID: {}", child.id()));

                #[cfg(target_os = "windows")]
                {
                    let pid = child.id();
                    let _ = Command::new("taskkill")
                        .args(&["/F", "/T", "/PID", &pid.to_string()])
                        .output();
                }
                #[cfg(not(target_os = "windows"))]
                {
                    let _ = child.kill();
                }

                let start = std::time::Instant::now();
                loop {
                    match child.try_wait() {
                        Ok(Some(status)) => {
                            log(&format!("Child exited with: {status}"));
                            break;
                        }
                        Ok(None) => {
                            if start.elapsed().as_secs() > 5 {
                                log("Child did not exit in 5s, forcing kill");
                                let _ = child.kill();
                                let _ = child.wait();
                                break;
                            }
                            std::thread::sleep(std::time::Duration::from_millis(100));
                        }
                        Err(e) => {
                            log(&format!("Error waiting for child: {e}"));
                            break;
                        }
                    }
                }

                log("Child process terminated");
            } else {
                log("WARNING: No stored child process to terminate");
            }
        }
    }
}

fn full_shutdown(app: &AppHandle, launcher_pid: u32, res_dir: &PathBuf) {
    log("=== FULL SHUTDOWN INITIATED ===");
    terminate_child(app);
    kill_all_backend_processes(launcher_pid);
    cleanup_port_file(res_dir, launcher_pid);
    log("=== FULL SHUTDOWN COMPLETE ===");
}

fn cleanup_port_file(res_dir: &PathBuf, pid: u32) {
    let port_file = res_dir.join(format!("port_{pid}.json"));
    let _ = fs::remove_file(&port_file);
    log(&format!("Cleaned up port file for PID {pid}"));
}

fn setup_main_window(app: &AppHandle, backend_port: u16, launcher_pid: u32) {
    let Some(win) = app.get_webview_window("main") else { return };

    inject_backend_globals(&win, launcher_pid, backend_port);

    let store = tauri_plugin_store::StoreBuilder::new(app, "main_window.json")
        .build()
        .expect("Failed to build store");

    let mut restored = false;

    if let (Some(w), Some(h), Some(x), Some(y)) = (
        store.get("w").and_then(|v: serde_json::Value| v.as_f64()),
        store.get("h").and_then(|v: serde_json::Value| v.as_f64()),
        store.get("x").and_then(|v: serde_json::Value| v.as_i64()),
        store.get("y").and_then(|v: serde_json::Value| v.as_i64()),
    ) {
        let safe_w = w.max(400.0);
        let safe_h = h.max(300.0);

        if is_position_visible(x, y, app) {
            let _ = win.set_size(tauri::LogicalSize::new(safe_w, safe_h));
            let _ = win.set_position(tauri::LogicalPosition::new(x as f64, y as f64));
            log(&format!("main window: restored size={safe_w}x{safe_h} pos={x},{y}"));
            restored = true;
        } else {
            log("main window: saved position off-screen, using default");
        }
    }

    if !restored {
        if let Ok(Some(monitor)) = win.current_monitor() {
            let scale  = monitor.scale_factor();
            let msize  = monitor.size();
            let width  = (msize.width  as f64 / scale * 0.365) as u32;
            let height = (msize.height as f64 / scale * 0.475) as u32;
            let _ = win.set_size(tauri::LogicalSize::new(width, height));
            let _ = win.center();
            log("main window: using default size");
        }
    }

    let win_clone = win.clone();
    win.on_window_event(move |event| {
        if let tauri::WindowEvent::Resized(_) | tauri::WindowEvent::Moved(_) = event {
            if let (Ok(size), Ok(pos)) = (win_clone.inner_size(), win_clone.outer_position()) {
                if let Ok(Some(monitor)) = win_clone.current_monitor() {
                    let scale = monitor.scale_factor();
                    if let Ok(store) = tauri_plugin_store::StoreBuilder::new(
                        win_clone.app_handle(),
                        "main_window.json",
                    ).build() {
                        store.set("w", serde_json::json!(size.width as f64 / scale));
                        store.set("h", serde_json::json!(size.height as f64 / scale));
                        store.set("x", serde_json::json!(pos.x));
                        store.set("y", serde_json::json!(pos.y));
                        let _ = store.save();
                    }
                }
            }
        }
    });

    let win_clone2 = win.clone();
    std::thread::spawn(move || {
        let client = reqwest::blocking::Client::new();
        loop {
            std::thread::sleep(std::time::Duration::from_secs(1));
            if let Ok(res) = client
                .get(&format!("http://localhost:{backend_port}/state"))
                .send()
            {
                if let Ok(state) = res.json::<serde_json::Value>() {
                    if let Some(on_top) = state.get("alwaysOnTop").and_then(|v| v.as_bool()) {
                        let _ = win_clone2.set_always_on_top(on_top);
                    }
                }
            }
        }
    });
}

fn setup_stats_window(app: &AppHandle, backend_port: u16) {
    let Some(stats_win) = app.get_webview_window("stats") else { return };

    let store = tauri_plugin_store::StoreBuilder::new(app, "stats_position.json")
        .build()
        .expect("Failed to build store");

    if let Ok(Some(monitor)) = stats_win.current_monitor() {
        let scale  = monitor.scale_factor();
        let msize  = monitor.size();

        let default_width  = (msize.width  as f64 / scale * 0.125) as u32;
        let default_height = (msize.height as f64 / scale * 0.1)   as u32 + 6;

        let saved_w = store.get("w").and_then(|v: serde_json::Value| v.as_f64());
        let saved_h = store.get("h").and_then(|v: serde_json::Value| v.as_f64());

        let (width, height) = match (saved_w, saved_h) {
            (Some(w), Some(h)) => (w.max(100.0) as u32, h.max(50.0) as u32),
            _ => (default_width, default_height),
        };

        let _ = stats_win.set_size(tauri::LogicalSize::new(width, height));

        let saved_x = store.get("x").and_then(|v: serde_json::Value| v.as_i64());
        let saved_y = store.get("y").and_then(|v: serde_json::Value| v.as_i64());

        match (saved_x, saved_y) {
            (Some(x), Some(y)) if is_position_visible(x, y, app) => {
                let _ = stats_win.set_position(PhysicalPosition::new(x as i32, y as i32));
                log(&format!("stats window: restored pos={x},{y}"));
            }
            _ => {
                let x = ((msize.width as i32) - (width as f64 * scale) as i32) / 2;
                let _ = stats_win.set_position(PhysicalPosition::new(x, 20));
                log("stats window: using default position");
            }
        }
    }

    let stats_win_clone = stats_win.clone();
    stats_win.on_window_event(move |event| {
        match event {
            tauri::WindowEvent::Moved(pos) => {
                if let Ok(store) = tauri_plugin_store::StoreBuilder::new(
                    stats_win_clone.app_handle(),
                    "stats_position.json",
                ).build() {
                    store.set("x", serde_json::json!(pos.x));
                    store.set("y", serde_json::json!(pos.y));
                    let _ = store.save();
                }
            }
            tauri::WindowEvent::Resized(size) => {
                if let Ok(Some(monitor)) = stats_win_clone.current_monitor() {
                    let scale = monitor.scale_factor();
                    if let Ok(store) = tauri_plugin_store::StoreBuilder::new(
                        stats_win_clone.app_handle(),
                        "stats_position.json",
                    ).build() {
                        store.set("w", serde_json::json!(size.width as f64 / scale));
                        store.set("h", serde_json::json!(size.height as f64 / scale));
                        let _ = store.save();
                    }
                }
            }
            _ => {}
        }
    });

    std::thread::spawn(move || {
        let client = reqwest::blocking::Client::new();
        loop {
            std::thread::sleep(std::time::Duration::from_millis(1000));
            if let Ok(res) = client
                .get(&format!("http://localhost:{backend_port}/state"))
                .send()
            {
                if let Ok(state) = res.json::<serde_json::Value>() {
                    let show = state
                        .get("showDebugOverlay")
                        .and_then(|v| v.as_bool())
                        .unwrap_or(false);
                    if show {
                        let _ = stats_win.show();
                    } else {
                        let _ = stats_win.hide();
                    }
                }
            }
        }
    });
}

#[tauri::command]
fn send_to_python(app: AppHandle, action: String, payload: String) -> Result<String, String> {
    let port = app
        .try_state::<BackendPort>()
        .and_then(|p| p.0.lock().ok().map(|g| *g))
        .unwrap_or(8765);

    reqwest::blocking::Client::new()
        .post(format!("http://localhost:{port}/command"))
        .json(&serde_json::json!({ "action": action, "payload": payload }))
        .send()
        .map(|_| "Success".to_string())
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn kill_conflicting_processes(app: AppHandle) -> serde_json::Value {
    let mut killed: u32 = 0;
    let own_pid = std::process::id().to_string();
    let res_dir = resource_dir(&app);
    let res_dir_str = res_dir.to_string_lossy().to_lowercase();

    #[cfg(target_os = "windows")]
    {
        if let Ok(output) = Command::new("wmic")
            .args(&["process", "get", "ProcessId,Name,ExecutablePath", "/FORMAT:CSV"])
            .output()
        {
            let text = String::from_utf8_lossy(&output.stdout);
            for line in text.lines() {
                let parts: Vec<&str> = line.split(',').collect();
                if parts.len() < 4 { continue; }
                let exe_path = parts[1].trim().to_lowercase();
                let name     = parts[2].trim().to_lowercase();
                let pid_str  = parts[3].trim();

                if pid_str == own_pid { continue; }
                if exe_path.is_empty() { continue; }

                let in_our_dir = exe_path.starts_with(&res_dir_str);
                let is_target  = name.starts_with("python") || name.starts_with("gpo");

                if in_our_dir && is_target && !pid_str.is_empty() {
                    let _ = Command::new("taskkill").args(&["/F", "/PID", pid_str]).output();
                    log(&format!("Killed process {pid_str} ({name}) from {exe_path}"));
                    killed += 1;
                }
            }
        }
        std::thread::sleep(std::time::Duration::from_millis(600));
    }

    #[cfg(not(target_os = "windows"))]
    {
        for pattern in &["python", "gpo"] {
            if let Ok(output) = Command::new("pgrep").args(&["-i", "-l", pattern]).output() {
                let text = String::from_utf8_lossy(&output.stdout);
                for line in text.lines() {
                    let mut parts = line.split_whitespace();
                    let (Some(pid), Some(_name)) = (parts.next(), parts.next()) else { continue };
                    if pid == own_pid { continue; }
                    if let Ok(exe_link) = fs::read_link(format!("/proc/{pid}/exe")) {
                        let exe_str = exe_link.to_string_lossy().to_lowercase();
                        if exe_str.starts_with(&res_dir_str) {
                            let _ = Command::new("kill").args(&["-9", pid]).output();
                            killed += 1;
                        }
                    }
                }
            }
        }
        std::thread::sleep(std::time::Duration::from_millis(400));
    }

    log(&format!("kill_conflicting_processes: terminated {killed} process(es)"));
    serde_json::json!({ "killed": killed })
}

#[tauri::command]
fn reset_window_position(app: AppHandle) -> Result<(), String> {
    let app_dir = app.path().app_data_dir().map_err(|e| e.to_string())?;
    let _ = fs::remove_file(app_dir.join("main_window.json"));
    let _ = fs::remove_file(app_dir.join("stats_position.json"));
    log("Window position data reset");
    Ok(())
}

#[tauri::command]
fn launch_macro(app: AppHandle, macro_name: String) -> Result<serde_json::Value, String> {
    let launcher_pid = std::process::id();
    let res_dir = resource_dir(&app);

    log(&format!("launch_macro: {macro_name}"));

    kill_existing_backend();

    #[cfg(debug_assertions)]
    {
        let python_cmd = if cfg!(target_os = "windows") { "python" } else { "python3" };
        let child = Command::new(python_cmd)
            .arg("backend.py")
            .arg("--pid")
            .arg(launcher_pid.to_string())
            .spawn()
            .map_err(|e| format!("Failed to start debug backend: {e}"))?;
        log("DEBUG: backend spawned via launch_macro");
        store_child(&app, child);
    }

    #[cfg(not(debug_assertions))]
    {
        let child = spawn_backend_process(&app, launcher_pid);
        store_child(&app, child);
    }

    let port = read_backend_port(&res_dir, launcher_pid);

    if !wait_for_backend(port) {
        return Err("Backend did not start in time".to_string());
    }

    if let Some(p) = app.try_state::<BackendPort>() {
        if let Ok(mut g) = p.0.lock() {
            *g = port;
        }
    }

    for label in &["main", "hub", "stats"] {
        if let Some(win) = app.get_webview_window(label) {
            inject_backend_globals(&win, launcher_pid, port);
        }
    }

    match macro_name.as_str() {
        "fishing" => {
            if let Some(hub) = app.get_webview_window("hub") {
                let _ = hub.hide();
            }
            if let Some(win) = app.get_webview_window("main") {
                win.show().map_err(|e| e.to_string())?;
                win.set_focus().map_err(|e| e.to_string())?;
                setup_main_window(&app, port, launcher_pid);
                setup_stats_window(&app, port);
            }
        }
        _ => {
            log(&format!("launch_macro: no window configured for '{macro_name}'"));
        }
    }

    log(&format!("launch_macro: done, port {port}"));
    Ok(serde_json::json!({ "port": port }))
}

#[tauri::command]
fn start_backend(app: AppHandle) -> Result<serde_json::Value, String> {
    let launcher_pid = std::process::id();
    let res_dir = resource_dir(&app);

    kill_existing_backend();

    #[cfg(debug_assertions)]
    {
        let python_cmd = if cfg!(target_os = "windows") { "python" } else { "python3" };
        let child = Command::new(python_cmd)
            .arg("backend.py")
            .arg("--pid")
            .arg(launcher_pid.to_string())
            .spawn()
            .map_err(|e| format!("Failed to start debug backend: {e}"))?;
        store_child(&app, child);
    }

    #[cfg(not(debug_assertions))]
    {
        let child = spawn_backend_process(&app, launcher_pid);
        store_child(&app, child);
    }

    let port = read_backend_port(&res_dir, launcher_pid);
    if !wait_for_backend(port) {
        return Err("Backend did not start in time".to_string());
    }

    if let Some(p) = app.try_state::<BackendPort>() {
        if let Ok(mut g) = p.0.lock() {
            *g = port;
        }
    }

    Ok(serde_json::json!({ "port": port }))
}

#[tauri::command]
fn open_main_window(app: AppHandle) -> Result<(), String> {
    let port = app
        .try_state::<BackendPort>()
        .and_then(|p| p.0.lock().ok().map(|g| *g))
        .unwrap_or(8765);

    if let Some(hub) = app.get_webview_window("hub") {
        hub.show().map_err(|e| e.to_string())?;
        hub.set_focus().map_err(|e| e.to_string())?;
        inject_backend_globals(&hub, std::process::id(), port);
    }

    if let Some(launcher) = app.get_webview_window("launcher") {
        let _ = launcher.close();
    }

    log("open_main_window: hub shown, launcher closed");
    Ok(())
}

struct KeyAuthApp {
    name: &'static str,
    ownerid: &'static str,
}

fn keyauth_app_for(macro_name: &str) -> Option<KeyAuthApp> {
    match macro_name {
        "fishing" => None,
        "juzo"    => Some(KeyAuthApp { name: "Ks Juzo Macro",   ownerid: "5ZmAhBPrGX" }),
        "mihawk"  => Some(KeyAuthApp { name: "Ks Mihawk Macro", ownerid: "5ZmAhBPrGX" }),
        "roger"   => Some(KeyAuthApp { name: "Ks Roger Macro",  ownerid: "5ZmAhBPrGX" }),
        _         => None,
    }
}

#[tauri::command]
fn get_saved_key(app: AppHandle, macro_name: String) -> Option<String> {
    let store = tauri_plugin_store::StoreBuilder::new(&app, "keys.json").build().ok()?;
    store.get(&macro_name).and_then(|v: serde_json::Value| v.as_str().map(|s| s.to_string()))
}

#[tauri::command]
fn keyauth_verify(app: AppHandle, key: String, macro_name: String) -> Result<serde_json::Value, String> {
    log(&format!("keyauth_verify: key=*** macro={macro_name}"));

    let ka = match keyauth_app_for(&macro_name) {
        Some(k) => k,
        None => {
            log(&format!("keyauth_verify: {macro_name} is free, skipping"));
            return Ok(serde_json::json!({ "success": true, "free": true }));
        }
    };

    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(10))
        .build()
        .map_err(|e| format!("Failed to build client: {e}"))?;

    let params = [
        ("type",    "init"),
        ("name",    ka.name),
        ("ownerid", ka.ownerid),
        ("ver",     "1.0"),
    ];

    let init_res: serde_json::Value = client
        .post("https://keyauth.win/api/1.2/")
        .form(&params)
        .send()
        .map_err(|e| format!("Init request failed: {e}"))?
        .json()
        .map_err(|e| format!("Init parse failed: {e}"))?;

    if !init_res.get("success").and_then(|v| v.as_bool()).unwrap_or(false) {
        let msg = init_res.get("message").and_then(|v| v.as_str()).unwrap_or("Init failed");
        return Err(msg.to_string());
    }

    let session_id = init_res
        .get("sessionid")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    let license_params = [
        ("type",      "license"),
        ("key",       key.as_str()),
        ("name",      ka.name),
        ("ownerid",   ka.ownerid),
        ("sessionid", session_id.as_str()),
    ];

    let license_res: serde_json::Value = client
        .post("https://keyauth.win/api/1.2/")
        .form(&license_params)
        .send()
        .map_err(|e| format!("License request failed: {e}"))?
        .json()
        .map_err(|e| format!("License parse failed: {e}"))?;

    let success = license_res.get("success").and_then(|v| v.as_bool()).unwrap_or(false);

    if success {
        if let Ok(store) = tauri_plugin_store::StoreBuilder::new(&app, "keys.json").build() {
            store.set(macro_name.clone(), serde_json::json!(key));
            let _ = store.save();
        }
        Ok(serde_json::json!({ "success": true }))
    } else {
        let msg = license_res
            .get("message")
            .and_then(|v| v.as_str())
            .unwrap_or("Invalid or expired key");
        Err(msg.to_string())
    }
}

#[tauri::command]
fn open_browser(url: String) -> Result<(), String> {
    #[cfg(target_os = "windows")]
    Command::new("cmd").args(&["/C", "start", "", &url]).spawn().map_err(|e| e.to_string())?;
    #[cfg(target_os = "macos")]
    Command::new("open").arg(&url).spawn().map_err(|e| e.to_string())?;
    #[cfg(target_os = "linux")]
    Command::new("xdg-open").arg(&url).spawn().map_err(|e| e.to_string())?;
    Ok(())
}

fn main() {
    let _ = fs::remove_file(logs_dir().join("debug.txt"));
    log("=== APP STARTING ===");

    let launcher_pid = std::process::id();
    log(&format!("Launcher PID: {launcher_pid}"));

    tauri::Builder::default()
        .manage(PythonProcess(Mutex::new(None)))
        .manage(BackendPort(Mutex::new(8765_u16)))
        .setup(move |app| {
            log("Setup running");

            if let Some(win) = app.get_webview_window("launcher") {
                let _ = win.show();
                let _ = win.set_focus();
            }

            log("Setup complete");
            Ok(())
        })
        .on_window_event(move |window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                let label = window.label();

                if label == "main" || label == "hub" {
                    api.prevent_close();

                    let app_handle = window.app_handle().clone();
                    let res_dir = resource_dir(&app_handle);

                    std::thread::spawn(move || {
                        full_shutdown(&app_handle, launcher_pid, &res_dir);
                        log("Exiting application");
                        app_handle.exit(0);
                    });
                }
            }
        })
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_store::Builder::default().build())
        .plugin(tauri_plugin_updater::Builder::default().build())
        .invoke_handler(tauri::generate_handler![
            send_to_python,
            kill_conflicting_processes,
            reset_window_position,
            start_backend,
            launch_macro,
            open_main_window,
            keyauth_verify,
            get_saved_key,
            open_browser,
        ])
        .run(tauri::generate_context!())
        .expect("Error running Tauri application");
}