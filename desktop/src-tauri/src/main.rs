#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Child, Stdio};
use std::sync::Mutex;
use tauri::{Manager, Emitter};

struct BackendState {
    child: Mutex<Option<Child>>,
}

impl Default for BackendState {
    fn default() -> Self {
        Self { child: Mutex::new(None) }
    }
}

fn find_backend_root() -> Option<std::path::PathBuf> {
    let mut candidates: Vec<std::path::PathBuf> = Vec::new();
    if let Ok(cwd) = std::env::current_dir() {
        candidates.push(cwd.clone());
        candidates.push(cwd.join("backend"));
        candidates.push(cwd.join(".."));
        candidates.push(cwd.join("../.."));
    }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(parent) = exe.parent() {
            let p = parent.to_path_buf();
            candidates.push(p.clone());
            candidates.push(p.join(".."));
            candidates.push(p.join("../.."));
            candidates.push(p.join("../../.."));
            candidates.push(p.join("../../../.."));
        }
    }
    // common source/install locations
    if let Ok(home) = std::env::var("HOME") {
        candidates.push(std::path::PathBuf::from(format!("{home}/Documents/AI")));
        candidates.push(std::path::PathBuf::from(format!("{home}/.local/share/nexus-ai")));
    }
    candidates.push(std::path::PathBuf::from("/home/david/Documents/AI"));

    for c in candidates {
        let c = if c.is_absolute() { c } else { std::env::current_dir().unwrap_or_default().join(c) };
        let script = c.join("backend").join("run_backend.py");
        if script.exists() {
            // return repo/root that contains backend/
            if c.join("backend").is_dir() {
                return Some(c);
            }
        }
        // maybe c itself is backend dir
        let script2 = c.join("run_backend.py");
        if script2.exists() && c.file_name().and_then(|s| s.to_str()) == Some("backend") {
            return c.parent().map(|p| p.to_path_buf());
        }
    }
    None
}

#[tauri::command]
fn start_backend(app: tauri::AppHandle, state: tauri::State<'_, BackendState>) -> Result<String, String> {
    let mut child_guard = state.child.lock().map_err(|e| e.to_string())?;

    if child_guard.is_some() {
        return Ok("already_running".to_string());
    }

    let root = find_backend_root().ok_or_else(|| "Could not locate NEXUS AI backend directory".to_string())?;
    let backend_dir = root.join("backend");
    let backend_script = backend_dir.join("run_backend.py");
    if !backend_script.exists() {
        return Err(format!("Backend script not found at {}", backend_script.display()));
    }

    // Prefer project venv python, fall back to system python3/python
    let venv_python = root.join(".venv").join("bin").join("python");
    let python_cmd = if venv_python.exists() {
        venv_python.to_string_lossy().to_string()
    } else if cfg!(target_os = "windows") {
        "python".to_string()
    } else {
        "python3".to_string()
    };

    let mut cmd = std::process::Command::new(&python_cmd);
    cmd.arg(&backend_script)
        .current_dir(&backend_dir)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    // Ensure backend can import app package
    cmd.env("PYTHONPATH", &backend_dir);

    let child = cmd.spawn().map_err(|e| format!("failed to start backend ({}): {}", python_cmd, e))?;

    *child_guard = Some(child);
    let _ = app.emit("backend_started", serde_json::json!({ "status": "started", "backend_dir": backend_dir.to_string_lossy() }));

    Ok("started".to_string())
}

#[tauri::command]
fn stop_backend(state: tauri::State<'_, BackendState>) -> Result<String, String> {
    let mut child_guard = state.child.lock().map_err(|e| e.to_string())?;

    if let Some(mut child) = child_guard.take() {
        let _ = child.kill();
        let _ = child.wait();
        Ok("stopped".to_string())
    } else {
        Ok("not_running".to_string())
    }
}

#[tauri::command]
fn backend_status(state: tauri::State<'_, BackendState>) -> Result<String, String> {
    let mut child_guard = state.child.lock().map_err(|e| e.to_string())?;
    match child_guard.as_mut() {
        Some(child) => match child.try_wait() {
            Ok(Some(_)) => Ok("stopped".to_string()),
            Ok(None) => Ok("running".to_string()),
            Err(e) => Err(format!("error checking backend: {}", e)),
        },
        None => Ok("not_running".to_string()),
    }
}

fn main() {
    tauri::Builder::default()
        .manage(BackendState::default())
        .invoke_handler(tauri::generate_handler![start_backend, stop_backend, backend_status])
        .setup(|app| {
            let _window = app.get_webview_window("main");
            #[cfg(debug_assertions)]
            {
                if let Some(w) = app.get_webview_window("main") {
                    let _ = w.open_devtools();
                }
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
