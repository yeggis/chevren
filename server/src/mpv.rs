use std::path::PathBuf;
use tokio::io::AsyncWriteExt;
use tokio::net::UnixStream;

const MPV_SOCKET: &str = "/tmp/chevren-mpv.sock";

async fn mpv_running() -> bool {
    UnixStream::connect(MPV_SOCKET).await.is_ok()
}

pub async fn open_with_subtitle(url: &str, srt_path: &PathBuf) -> anyhow::Result<()> {
    if mpv_running().await {
        // MPV zaten çalışıyor — altyazıyı güncelle, yeni pencere açma
        let cmd = vec![
            serde_json::Value::String("sub-add".into()),
            serde_json::Value::String(srt_path.display().to_string()),
            serde_json::Value::String("select".into()),
        ];
        send_command(&cmd).await.ok();
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

pub async fn update_subtitle(srt_path: &PathBuf) -> anyhow::Result<()> {
    // Önce mevcut sub track'i kaldır, sonra yeni dosyayı ekle
    // sub-add ile "select" modu: zaten yüklüyse replace eder
    let cmd = serde_json::json!({
        "command": ["sub-add", srt_path.to_str().unwrap_or(""), "select"]
    });
    let mut stream = UnixStream::connect(MPV_SOCKET)
        .await
        .map_err(|_| anyhow::anyhow!("mpv çalışmıyor"))?;
    let mut msg = serde_json::to_string(&cmd)?;
    msg.push('\n');
    stream.write_all(msg.as_bytes()).await?;
    Ok(())
}
