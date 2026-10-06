use std::io::{Read, Write};
use std::net::TcpStream;
#[cfg(windows)]
use std::os::windows::process::CommandExt;
use std::path::PathBuf;
use std::process::Command;
use std::time::Duration;
fn port_up(port: u16) -> bool {
    TcpStream::connect(("127.0.0.1", port)).is_ok()
}
    const UI_BUILD_MARKER: &str =
    r#"<meta name="grok-remote-ui-build" content="2026-09-12-quiet-copy"/>"#;
fn home() -> PathBuf {
    PathBuf::from(
        std::env::var("USERPROFILE")
            .or_else(|_| std::env::var("HOME"))
            .unwrap_or_default(),
    )
}
fn plugin_root() -> PathBuf {
    if let Ok(p) = std::env::var("GROK_PLUGIN_ROOT") {
        let b = PathBuf::from(p);
        if b.is_dir() {
            return b;
        }
    }
    home().join(".grok").join("plugins").join("grok-remote")
}
fn repo_root() -> PathBuf {
    let built = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").join("..");
    let exe_dirs = std::env::current_exe()
        .ok()
        .map(|e| e.ancestors().skip(1).take(5).map(PathBuf::from).collect::<Vec<_>>())
        .unwrap_or_default();
    std::env::var("GROK_REMOTE_ROOT")
        .ok()
        .map(PathBuf::from)
        .into_iter()
        .chain([built.clone(), plugin_root()])
        .chain(exe_dirs)
        .find(|d| d.join("server.py").is_file())
        .unwrap_or(built)
}
#[cfg(windows)]
fn ensure_script() -> Option<PathBuf> {
    [
        repo_root().join("scripts").join("ensure-running.ps1"),
        plugin_root().join("scripts").join("ensure-running.ps1"),
        repo_root().join("start.ps1"),
        plugin_root().join("start.ps1"),
    ]
    .into_iter()
    .find(|p| p.is_file())
}
fn read_secret_file(p: &PathBuf) -> Option<String> {
    let t = std::fs::read_to_string(p).ok()?;
    let s = t.trim();
    if s.len() >= 16 {
        Some(s.to_string())
    } else {
        None
    }
}
fn secret_from_cmd(p: &PathBuf) -> Option<String> {
    let txt = std::fs::read_to_string(p).ok()?;
    let tag = "GROK_AGENT_SECRET=";
    let i = txt.find(tag)? + tag.len();
    let rest = &txt[i..];
    let end = rest.find(char::is_whitespace).unwrap_or(rest.len());
    let k = rest[..end].trim().to_string();
    if k.is_empty() {
        None
    } else {
        Some(k)
    }
}
fn ui_secret() -> String {
    if let Ok(s) = std::env::var("GROK_AGENT_SECRET") {
        if !s.is_empty() {
            return s;
        }
    }
    for p in [
        plugin_root().join(".ui-secret"),
        repo_root().join(".ui-secret"),
        plugin_root().join("logs").join("run-agent.cmd"),
    ] {
        if p.file_name().and_then(|n| n.to_str()) == Some("run-agent.cmd") {
            if let Some(k) = secret_from_cmd(&p) {
                return k;
            }
        } else if let Some(k) = read_secret_file(&p) {
            return k;
        }
    }
    String::new()
}
fn expected_ui_marker() -> String {
    let txt = std::fs::read_to_string(repo_root().join("web").join("index.html")).unwrap_or_default();
    if let Some(i) = txt.find(r#"name="grok-remote-ui-build""#) {
        if let Some(start) = txt[..i].rfind('<') {
            if let Some(end) = txt[i..].find('>') {
                return txt[start..i + end + 1].to_string();
            }
        }
    }
    UI_BUILD_MARKER.to_string()
}
fn served_ui_is_current(ui_port: u16) -> bool {
    if !repo_root().join("web").join("index.html").is_file() {
        return true;
    }
    let marker = expected_ui_marker();
    let Ok(mut stream) = TcpStream::connect(("127.0.0.1", ui_port)) else {
        return false;
    };
    let _ = stream.set_read_timeout(Some(Duration::from_secs(3)));
    let _ = stream.set_write_timeout(Some(Duration::from_secs(3)));
    let secret = ui_secret();
    let target = if secret.is_empty() {
        "/".to_string()
    } else {
        format!("/?key={secret}")
    };
    let request =
        format!("GET {target} HTTP/1.0\r\nHost: 127.0.0.1:{ui_port}\r\nConnection: close\r\n\r\n");
    if stream.write_all(request.as_bytes()).is_err() {
        return false;
    }
    let mut response = String::new();
    stream.read_to_string(&mut response).is_ok() && response.contains(&marker)
}
#[cfg(not(windows))]
fn ctl(args: &[&str]) -> bool {
    let script = repo_root().join("grok_remote_ctl.py");
    if !script.is_file() {
        return false;
    }
    let _ = std::fs::create_dir_all(repo_root().join("logs"));
    let log = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(repo_root().join("logs").join("desktop-hub.log"));
    let mut cmd = Command::new("python3");
    cmd.arg(&script).args(args).current_dir(repo_root()).stdin(std::process::Stdio::null());
    if let Ok(f) = log {
        if let Ok(f2) = f.try_clone() {
            cmd.stdout(f).stderr(f2);
        }
    }
    cmd.status().map(|s| s.success()).unwrap_or(false)
}
#[cfg(not(windows))]
fn restart_repo_ui() -> bool {
    ctl(&["restart"])
}
#[cfg(not(windows))]
fn spawn_stack() {
    let cwd = std::env::var("GROK_REMOTE_CWD").unwrap_or_default();
    let mut args = vec!["start", "--force", "--reason", "desktop"];
    if !cwd.is_empty() {
        args.extend(["--cwd", cwd.as_str()]);
    }
    let _ = ctl(&args);
}
#[cfg(windows)]
fn restart_repo_ui() -> bool {
    let script = repo_root().join("scripts").join("restart-ui-only.ps1");
    if !script.is_file() {
        return false;
    }
    let mut cmd = Command::new("powershell.exe");
    cmd.args([
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        &script.to_string_lossy(),
    ]);
    cmd.current_dir(repo_root());
    #[cfg(windows)]
    {
        cmd.creation_flags(0x08000000);
    }
    cmd.status().map(|status| status.success()).unwrap_or(false)
}
#[cfg(windows)]
fn spawn_stack() {
    let Some(ps1) = ensure_script() else {
        return;
    };
    let cwd = std::env::var("GROK_REMOTE_CWD").unwrap_or_else(|_| {
        home()
            .join("Documents")
            .join("ai")
            .to_string_lossy()
            .into_owned()
    });
    let root = ps1
        .parent()
        .and_then(|p| {
            if p.ends_with("scripts") {
                p.parent()
            } else {
                Some(p)
            }
        })
        .map(PathBuf::from)
        .unwrap_or_else(plugin_root);
    let name = ps1.file_name().and_then(|n| n.to_str()).unwrap_or("");
    let mut cmd = Command::new("powershell.exe");
    if name.eq_ignore_ascii_case("ensure-running.ps1") {
        cmd.args([
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            &ps1.to_string_lossy(),
            "-IgnoreConfig",
            "-Reason",
            "desktop",
            "-Cwd",
            &cwd,
        ]);
    } else {
        cmd.args([
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            &ps1.to_string_lossy(),
            "-Cwd",
            &cwd,
            "-AlwaysApprove",
            "-UiPort",
            "2421",
            "-Port",
            "2419",
            "-NoLeader",
        ]);
    }
    cmd.current_dir(root);
    cmd.env("GROK_PROJECT_DIR", &cwd);
    #[cfg(windows)]
    {
        cmd.creation_flags(0x08000000);
    }
    let _ = cmd.spawn();
}
fn ui_url(ui_port: u16) -> String {
    let secret = ui_secret();
    let mut url = format!(
        "http://127.0.0.1:{}/?auto=1&desktop=1&layout=desktop&v={}",
        ui_port,
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_millis())
            .unwrap_or(0)
    );
    if !secret.is_empty() {
        url.push_str("&key=");
        url.push_str(&secret);
    }
    url
}
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let ui_port: u16 = std::env::var("GROK_REMOTE_UI_PORT")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(2421);
    if port_up(ui_port) && !served_ui_is_current(ui_port) {
        let _ = restart_repo_ui();
    }
    if !port_up(ui_port) {
        spawn_stack();
    }
    let url = ui_url(ui_port);
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .setup(move |app| {
            use tauri::Manager;
            if let Some(w) = app.get_webview_window("main") {
                if let Ok(u) = url.parse() {
                    let _ = w.navigate(u);
                }
                let w2 = w.clone();
                std::thread::spawn(move || {
                    for i in 0..80 {
                        if port_up(ui_port) {
                            if i > 0 {
                                if let Ok(u) = ui_url(ui_port).parse() {
                                    let _ = w2.navigate(u);
                                }
                            }
                            return;
                        }
                        if i == 2 || i == 16 {
                            spawn_stack();
                        }
                        std::thread::sleep(Duration::from_millis(500));
                    }
                });
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running Grok Remote desktop");
}
