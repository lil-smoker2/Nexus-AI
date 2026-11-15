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

#[tauri::command]
fn start_backend(app: tauri::AppHandle, state: tauri::State<'_, BackendState>) -> Result<String, String> {
    let mut child_guard = state.child.lock().map_err(|e| e.to_string())?;

    if child_guard.is_some() {
        return Ok("already_running".to_string());
    }

    let backend_dir = if cfg!(debug_assertions) {
        std::env::current_dir().unwrap_or_default()
    } else {
        std::env::current_exe()
            .ok()
            .and_then(|p| p.parent().map(|p| p.to_path_buf()))
            .unwrap_or_default()
    };

    let python_cmd = if cfg!(target_os = "windows") { "python" } else { "python3" };
    let backend_script = backend_dir.join("../backend/run_backend.py");

    let child = std::process::Command::new(python_cmd)
        .arg(backend_script)
        .current_dir(backend_dir.join("../backend"))
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("failed to start backend: {}", e))?;

    *child_guard = Some(child);
    app.emit("backend_started", serde_json::json!({ "status": "started" }))
        .map_err(|e| e.to_string())?;

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
