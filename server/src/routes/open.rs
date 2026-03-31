use crate::mpv;
use crate::state::SharedState;
use axum::{extract::State, http::StatusCode, Json};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::process::Stdio;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::Command;

#[derive(Deserialize)]
pub struct OpenRequest {
    pub url: String,
}

#[derive(Deserialize)]
pub struct GenerateRequest {
    pub url: String,
}

#[derive(Serialize)]
pub struct OpenResponse {
    pub status: String,
    pub message: String,
}

// ── /open — mpv modu (değişmedi) ────────────────────────────────────────────
pub async fn handler(
    State(_state): State<SharedState>,
    Json(req): Json<OpenRequest>,
) -> Result<Json<OpenResponse>, (StatusCode, Json<OpenResponse>)> {
    let video_id =
        extract_video_id(&req.url).ok_or_else(|| error_response("Geçersiz YouTube URL'si"))?;
    let srt_path = cache_path(&video_id);
    if !srt_path.exists() {
        run_pipeline_blocking(&req.url, &srt_path)
            .await
            .map_err(|e| error_response(&format!("Pipeline hatası: {e}")))?;
    }
    mpv::open_with_subtitle(&req.url, &srt_path)
        .await
        .map_err(|e| error_response(&format!("mpv hatası: {e}")))?;
    Ok(Json(OpenResponse {
        status: "ok".into(),
        message: "mpv açıldı".into(),
    }))
}

// ── /generate — extension için, anında döner, arka planda çalışır ───────────
pub async fn generate_handler(
    State(state): State<SharedState>,
    Json(req): Json<GenerateRequest>,
) -> Result<Json<OpenResponse>, (StatusCode, Json<OpenResponse>)> {
    // Zaten çalışıyorsa reddet
    {
        let s = state.lock().unwrap();
        let busy = matches!(
            s.stage.as_str(),
            "downloading" | "transcribing" | "translating"
        );
        if busy {
            return Err(error_response("Pipeline zaten çalışıyor"));
        }
    }

    let video_id =
        extract_video_id(&req.url).ok_or_else(|| error_response("Geçersiz YouTube URL'si"))?;
    let srt_path = cache_path(&video_id);

    if srt_path.exists() {
        let mut s = state.lock().unwrap();
        s.stage = "ready".into();
        s.video_id = Some(video_id);
        s.chunk = None;
        s.message = None;
        return Ok(Json(OpenResponse {
            status: "ok".into(),
            message: "cache'den hazır".into(),
        }));
    }

    // Arka planda başlat
    let state_clone = state.clone();
    let url = req.url.clone();
    tokio::spawn(async move {
        run_pipeline_tracked(url, state_clone).await;
    });

    Ok(Json(OpenResponse {
        status: "ok".into(),
        message: "pipeline başlatıldı".into(),
    }))
}

// ── Arka plan pipeline — stdout'u parse eder, state günceller ────────────────
async fn run_pipeline_tracked(url: String, state: SharedState) {
    let child = Command::new("chevren")
        .args(["--no-play", &url])
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn();

    let mut child = match child {
        Ok(c) => c,
        Err(e) => {
            let mut s = state.lock().unwrap();
            s.stage = "error".into();
            s.message = Some(e.to_string());
            return;
        }
    };

    if let Some(stdout) = child.stdout.take() {
        let mut lines = BufReader::new(stdout).lines();
        while let Ok(Some(line)) = lines.next_line().await {
            if let Some(json_str) = line.strip_prefix("CHEVREN_STATUS:") {
                if let Ok(val) = serde_json::from_str::<serde_json::Value>(json_str) {
                    let mut s = state.lock().unwrap();
                    if let Some(stage) = val["stage"].as_str() {
                        s.stage = stage.to_string();
                    }
                    s.chunk = val.get("chunk").and_then(|v| v.as_u64()).map(|n| n as u32);
                    s.video_id = val
                        .get("video_id")
                        .and_then(|v| v.as_str())
                        .map(String::from);
                    s.message = val
                        .get("message")
                        .and_then(|v| v.as_str())
                        .map(String::from);
                }
            }
        }
    }

    match child.wait().await {
        Ok(status) if status.success() => {
            let mut s = state.lock().unwrap();
            if s.stage != "ready" {
                s.stage = "ready".into();
            }
        }
        _ => {
            let mut s = state.lock().unwrap();
            if s.stage != "ready" {
                s.stage = "error".into();
                s.message = Some("Pipeline başarısız oldu".into());
            }
        }
    }
}

// ── Blocking pipeline — mpv modu için ────────────────────────────────────────
async fn run_pipeline_blocking(url: &str, srt_path: &PathBuf) -> anyhow::Result<()> {
    if let Some(parent) = srt_path.parent() {
        tokio::fs::create_dir_all(parent).await?;
    }
    let status = Command::new("chevren")
        .args(["--no-play", url])
        .status()
        .await?;
    if !status.success() {
        anyhow::bail!("chevren pipeline başarısız oldu");
    }
    Ok(())
}

// ── Yardımcılar ───────────────────────────────────────────────────────────────
pub fn extract_video_id(url: &str) -> Option<String> {
    let url = url::Url::parse(url).ok()?;
    url.query_pairs()
        .find(|(k, _)| k == "v")
        .map(|(_, v)| v.into_owned())
}

pub fn cache_path(video_id: &str) -> PathBuf {
    directories::BaseDirs::new()
        .map(|b| {
            b.cache_dir()
                .join("chevren")
                .join(format!("{video_id}.srt"))
        })
        .unwrap_or_else(|| PathBuf::from(format!("/tmp/{video_id}.srt")))
}

fn error_response(msg: &str) -> (StatusCode, Json<OpenResponse>) {
    (
        StatusCode::INTERNAL_SERVER_ERROR,
        Json(OpenResponse {
            status: "error".into(),
            message: msg.into(),
        }),
    )
}
