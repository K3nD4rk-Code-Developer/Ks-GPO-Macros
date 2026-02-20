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
        log(&format!("Port file not ready (attempt {attempt}/20), retrying…"));
        std::thread::sleep(std::time::Duration::from_millis(500));
    }

    log("WARNING: Could not read port file, falling back to 8765");
    8765
}

fn wait_for_backend(port: u16) -> bool {
    log(&format!("Waiting for backend on port {port}…"));
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
        }
    }
}

fn inject_backend_globals(win: &tauri::WebviewWindow, pid: u32, port: u16) {
    let _ = win.eval(&format!(
        "window.__LAUNCHER_PID__ = '{}'; window.__BACKEND_PORT__ = {};",
        pid, port
    ));
}

fn setup_main_window(app: &AppHandle, backend_port: u16, launcher_pid: u32) {
    let Some(win) = app.get_webview_window("main") else { return };

    inject_backend_globals(&win, launcher_pid, backend_port);

    let store = tauri_plugin_store::StoreBuilder::new(app, "main_window.json")
        .build()
        .expect("Failed to build store");

    let restored = match (
        store.get("w").and_then(|v: serde_json::Value| v.as_f64()),
        store.get("h").and_then(|v: serde_json::Value| v.as_f64()),
        store.get("x").and_then(|v: serde_json::Value| v.as_i64()),
        store.get("y").and_then(|v: serde_json::Value| v.as_i64()),
    ) {
        (Some(w), Some(h), Some(x), Some(y)) => {
            let _ = win.set_size(tauri::LogicalSize::new(w, h));
            let _ = win.set_position(tauri::LogicalPosition::new(x as f64, y as f64));
            log(&format!("main window: restored size={w}x{h} pos={x},{y}"));
            true
        }
        _ => false,
    };

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
        match event {
            tauri::WindowEvent::Resized(_) | tauri::WindowEvent::Moved(_) => {
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
            _ => {}
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
            (Some(w), Some(h)) => (w as u32, h as u32),
            _ => (default_width, default_height),
        };

        let _ = stats_win.set_size(tauri::LogicalSize::new(width, height));
        log(&format!("stats window: size={width}x{height}"));

        match (
            store.get("x").and_then(|v: serde_json::Value| v.as_i64()),
            store.get("y").and_then(|v: serde_json::Value| v.as_i64()),
        ) {
            (Some(x), Some(y)) => {
                let _ = stats_win.set_position(PhysicalPosition::new(x as i32, y as i32));
                log(&format!("stats window: restored pos={x},{y}"));
            }
            _ => {
                let x = ((msize.width as i32) - (width as f64 * scale) as i32) / 2;
                let _ = stats_win.set_position(PhysicalPosition::new(x, 20));
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
        std::thread::sleep(std::time::Duration::from_secs(2));
        loop {
            std::thread::sleep(std::time::Duration::from_secs(1));
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

fn cleanup_port_file(res_dir: &PathBuf, pid: u32) {
    let port_file = res_dir.join(format!("port_{pid}.json"));
    let _ = fs::remove_file(&port_file);
    log(&format!("Cleaned up port file for PID {pid}"));
}

fn terminate_child(app: &AppHandle) {
    if let Some(proc) = app.try_state::<PythonProcess>() {
        if let Ok(mut guard) = proc.0.lock() {
            if let Some(mut child) = guard.take() {
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
                let _ = child.wait();
                log("Backend terminated");
            }
        }
    }
}

#[tauri::command]
fn send_to_python(action: String, payload: String) -> Result<String, String> {
    reqwest::blocking::Client::new()
        .post("http://localhost:8765/command")
        .json(&serde_json::json!({ "action": action, "payload": payload }))
        .send()
        .map(|_| "Success".to_string())
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn kill_conflicting_processes() -> serde_json::Value {
    let mut killed: u32 = 0;
    let own_pid = std::process::id().to_string();

    #[cfg(target_os = "windows")]
    {
        if let Ok(output) = Command::new("tasklist").args(&["/FO", "CSV", "/NH"]).output() {
            let text = String::from_utf8_lossy(&output.stdout);
            for line in text.lines() {
                let parts: Vec<&str> = line.split(',').collect();
                if parts.len() < 2 { continue; }
                let name    = parts[0].trim_matches('"').to_lowercase();
                let pid_str = parts[1].trim_matches('"');
                if pid_str == own_pid { continue; }
                if (name.starts_with("python") || name.starts_with("gpo")) && !pid_str.is_empty() {
                    let _ = Command::new("taskkill").args(&["/F", "/PID", pid_str]).output();
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
                    if let Some(pid) = line.split_whitespace().next() {
                        if pid == own_pid { continue; }
                        let _ = Command::new("kill").args(&["-9", pid]).output();
                        killed += 1;
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

        log("DEBUG: backend spawned via start_backend command");
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

    if let Some(win) = app.get_webview_window("main") {
        inject_backend_globals(&win, launcher_pid, port);
    }
    if let Some(win) = app.get_webview_window("hub") {
        inject_backend_globals(&win, launcher_pid, port);
    }

    if let Some(p) = app.try_state::<BackendPort>() {
        if let Ok(mut g) = p.0.lock() {
            *g = port;
        }
    }

    log(&format!("start_backend: port {port}"));
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

#[tauri::command]
fn open_macro_window(app: AppHandle, macro_name: String) -> Result<(), String> {
    let port = app
        .try_state::<BackendPort>()
        .and_then(|p| p.0.lock().ok().map(|g| *g))
        .unwrap_or(8765);

    log(&format!("open_macro_window: {macro_name}"));

    if let Some(hub) = app.get_webview_window("hub") {
        let _ = hub.hide();
    }

    match macro_name.as_str() {
        "fishing" => {
            if let Some(win) = app.get_webview_window("main") {
                inject_backend_globals(&win, std::process::id(), port);
                win.show().map_err(|e| e.to_string())?;
                win.set_focus().map_err(|e| e.to_string())?;
                setup_main_window(&app, port, std::process::id());
                setup_stats_window(&app, port);
            }
        }
        _ => {
            log(&format!("open_macro_window: no window configured for '{macro_name}'"));
        }
    }

    Ok(())
}

struct KeyAuthApp {
    name: &'static str,
    ownerid: &'static str,
}

fn keyauth_app_for(macro_name: &str) -> Option<KeyAuthApp> {
    match macro_name {
        "fishing" => None,
        "juzo"    => Some(KeyAuthApp { name: "K's Juzo Macro",   ownerid: "5ZmAhBPrGX" }),
        "mihawk"  => Some(KeyAuthApp { name: "K's Mihawk Macro", ownerid: "5ZmAhBPrGX" }),
        "rodger"  => Some(KeyAuthApp { name: "K's Roger Macro",  ownerid: "5ZmAhBPrGX" }),
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

    log(&format!("keyauth init response: {init_res}"));

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

    log(&format!("keyauth license response: {license_res}"));

    let success = license_res.get("success").and_then(|v| v.as_bool()).unwrap_or(false);

    if success {
        log("keyauth_verify: success");
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
        log(&format!("keyauth_verify: failed — {msg}"));
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
        .manage(BackendPort(Mutex::new(8765)))
        .setup(move |app| {
            #[allow(unused_variables)]
            let app = app;
            log("Setup running");

            #[cfg(not(debug_assertions))]
            {
                let res_dir = resource_dir(app.handle());

                kill_existing_backend();

                let child = spawn_backend_process(app.handle(), launcher_pid);
                store_child(app.handle(), child);

                let backend_port = read_backend_port(&res_dir, launcher_pid);
                log(&format!("Using port {backend_port}"));

                if let Some(p) = app.try_state::<BackendPort>() {
                    if let Ok(mut g) = p.0.lock() {
                        *g = backend_port;
                    }
                }

                if !wait_for_backend(backend_port) {
                    let stderr_log = res_dir.join("logs").join("python_stderr.txt");
                    if let Ok(errors) = fs::read_to_string(&stderr_log) {
                        log(&format!("Python stderr: {errors}"));
                    }
                    panic!("Backend failed to start within allotted time");
                }

                setup_main_window(app.handle(), backend_port, launcher_pid);
                setup_stats_window(app.handle(), backend_port);
            }

            #[cfg(debug_assertions)]
            {
                log("DEBUG: backend will be started by bootstrapper via start_backend command");
                if let Some(win) = app.get_webview_window("launcher") {
                    let _ = win.show();
                    let _ = win.set_focus();
                }
            }

            log("Setup complete");
            Ok(())
        })
        .on_window_event(move |window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                if window.label() == "main" {
                    api.prevent_close();

                    let app_handle = window.app_handle().clone();
                    let res_dir = resource_dir(&app_handle);

                    cleanup_port_file(&res_dir, launcher_pid);

                    std::thread::spawn(move || {
                        terminate_child(&app_handle);
                        log("Exiting application");
                        app_handle.exit(0);
                    });
                }
            }
        })
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_store::Builder::default().build())
        .invoke_handler(tauri::generate_handler![
            send_to_python,
            kill_conflicting_processes,
            start_backend,
            open_main_window,
            open_macro_window,
            keyauth_verify,
            get_saved_key,
            open_browser,
        ])
        .run(tauri::generate_context!())
        .expect("Error running Tauri application");
}