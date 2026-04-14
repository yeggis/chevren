use crate::mpv;
use crate::state::SharedState;
use axum::{extract::State, http::StatusCode, Json};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
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
    State(state): State<SharedState>,
    Json(req): Json<OpenRequest>,
) -> Result<Json<OpenResponse>, (StatusCode, Json<OpenResponse>)> {
    let video_id =
        extract_video_id(&req.url).ok_or_else(|| error_response("Geçersiz YouTube URL'si"))?;
    let srt_path = cache_path(&video_id);
    if !srt_path.exists() {
        // generate_handler zaten çalışıyorsa, bitmesini bekle
        loop {
            let busy = {
                let s = state.lock().unwrap();
                matches!(s.stage.as_str(), "downloading" | "transcribing" | "translating")
            };
            if !busy { break; }
            tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
        }
        // Bekleme sonrası hâlâ yoksa kendi pipeline'ını çalıştır
        if !srt_path.exists() {
            run_pipeline_blocking(&req.url, &srt_path)
                .await
                .map_err(|e| error_response(&format!("Pipeline hatası: {e}")))?;
        }
    }
    mpv::open_with_subtitle(&req.url, &srt_path, &state)
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

    // State'i hemen kilitle ve güncelle (race condition koruması)
    {
        let mut s = state.lock().unwrap();
        s.stage = "downloading".into();
        s.video_id = Some(video_id.clone());
        s.chunk = None;
        s.chunk_max = None;
        s.message = None;
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

// ── Arka plan pipeline — artık sadece bekler, status Python tarafından HTTP ile güncellenir ─
async fn run_pipeline_tracked(url: String, state: SharedState) {
    let status = Command::new("chevren")
        .args(["--no-play", &url])
        .status()
        .await;

    match status {
        Ok(s) if s.success() => {
            let mut s = state.lock().unwrap();
            if s.stage != "ready" && s.stage != "error" {
                s.stage = "ready".into();
            }
        }
        _ => {
            let mut s = state.lock().unwrap();
            if s.stage != "ready" {
                s.stage = "error".into();
                if s.message.is_none() {
                    s.message = Some("Pipeline başarısız oldu".into());
                }
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
