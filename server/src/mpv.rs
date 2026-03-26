use std::path::PathBuf;
use tokio::io::AsyncWriteExt;
use tokio::net::UnixStream;

const MPV_SOCKET: &str = "/tmp/chevren-mpv.sock";

pub async fn open_with_subtitle(url: &str, srt_path: &PathBuf) -> anyhow::Result<()> {
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
    let mut stream = UnixStream::connect(MPV_SOCKET).await
        .map_err(|_| anyhow::anyhow!("mpv IPC socket bulunamadı — mpv çalışıyor mu?"))?;

    let payload = serde_json::json!({ "command": command });
    let mut msg = serde_json::to_string(&payload)?;
    msg.push('\n');

    stream.write_all(msg.as_bytes()).await?;
    Ok(())
}
