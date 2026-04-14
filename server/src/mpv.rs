use std::path::PathBuf;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::net::UnixStream;

const MPV_SOCKET: &str = "/tmp/chevren-mpv.sock";

async fn mpv_running() -> bool {
    UnixStream::connect(MPV_SOCKET).await.is_ok()
}

pub async fn open_with_subtitle(
    url: &str,
    srt_path: &PathBuf,
    state: &crate::state::SharedState,
) -> anyhow::Result<()> {
    if mpv_running().await {
        // MPV zaten çalışıyor — altyazıyı ekle
        let track_id = add_subtitle(srt_path).await?;
        state.lock().unwrap().sub_track_id = Some(track_id);
        return Ok(());
    }

    tokio::process::Command::new("mpv")
        .args([
            url,
            "--input-ipc-server=/tmp/chevren-mpv.sock",
            &format!("--sub-file={}", srt_path.display()),
        ])
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .spawn()?;
    Ok(())
}

pub async fn send_command(command: &[serde_json::Value]) -> anyhow::Result<()> {
    let mut stream = UnixStream::connect(MPV_SOCKET)
        .await
        .map_err(|_| anyhow::anyhow!("mpv IPC socket bulunamadı — mpv çalışıyor mu?"))?;
    let payload = serde_json::json!({ "command": command });
    let mut msg = serde_json::to_string(&payload)?;
    msg.push('\n');
    stream.write_all(msg.as_bytes()).await?;
    Ok(())
}

pub async fn send_command_with_response(
    command: &[serde_json::Value],
) -> anyhow::Result<serde_json::Value> {
    let stream = UnixStream::connect(MPV_SOCKET)
        .await
        .map_err(|_| anyhow::anyhow!("mpv IPC socket bulunamadı"))?;
    let (reader, mut writer) = stream.into_split();
    let mut reader = BufReader::new(reader);

    let payload = serde_json::json!({ "command": command });
    let mut msg = serde_json::to_string(&payload)?;
    msg.push('\n');
    writer.write_all(msg.as_bytes()).await?;

    let mut response = String::new();
    for _ in 0..20 {
        response.clear();
        reader.read_line(&mut response).await?;
        let trimmed = response.trim();
        if trimmed.is_empty() {
            continue;
        }
        if let Ok(val) = serde_json::from_str::<serde_json::Value>(trimmed) {
            if val.get("error").is_some() {
                return Ok(val);
            }
        }
    }
    Err(anyhow::anyhow!("MPV yanıtı alınamadı (event loop timeout)"))
}

pub async fn add_subtitle(srt_path: &PathBuf) -> anyhow::Result<i64> {
    let cmd = vec![
        serde_json::Value::String("sub-add".into()),
        serde_json::Value::String(srt_path.display().to_string()),
        serde_json::Value::String("select".into()),
    ];
    let resp = send_command_with_response(&cmd).await?;
    // Response format: {"data": 2, "error": "success"}
    if let Some(id) = resp.get("data").and_then(|v| v.as_i64()) {
        Ok(id)
    } else {
        Err(anyhow::anyhow!("Altyazı ID'si alınamadı: {:?}", resp))
    }
}

pub async fn reload_subtitle(track_id: i64) -> anyhow::Result<()> {
    let cmd = vec![
        serde_json::Value::String("sub-reload".into()),
        serde_json::Value::Number(track_id.into()),
    ];
    send_command(&cmd).await
}
