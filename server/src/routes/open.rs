use axum::{Json, http::StatusCode};
use directories::BaseDirs;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use tokio::process::Command;

use crate::mpv;

#[derive(Deserialize)]
pub struct OpenRequest {
    pub url: String,
}

#[derive(Serialize)]
pub struct OpenResponse {
    pub status: String,
    pub message: String,
}

pub async fn handler(
    Json(req): Json<OpenRequest>,
) -> Result<Json<OpenResponse>, (StatusCode, Json<OpenResponse>)> {
    let video_id = extract_video_id(&req.url).ok_or_else(|| {
        error_response("Geçersiz YouTube URL'si")
    })?;

    let srt_path = cache_path(&video_id);

    if !srt_path.exists() {
        tracing::info!("Cache yok, pipeline başlatılıyor: {}", video_id);
        run_pipeline(&req.url, &srt_path).await.map_err(|e| {
            error_response(&format!("Pipeline hatası: {e}"))
        })?;
    } else {
        tracing::info!("Cache bulundu: {}", srt_path.display());
    }

    mpv::open_with_subtitle(&req.url, &srt_path).await.map_err(|e| {
        error_response(&format!("mpv hatası: {e}"))
    })?;

    Ok(Json(OpenResponse {
        status: "ok".into(),
        message: "mpv açıldı".into(),
    }))
}

fn extract_video_id(url: &str) -> Option<String> {
    let url = url::Url::parse(url).ok()?;
    url.query_pairs()
        .find(|(k, _)| k == "v")
        .map(|(_, v)| v.into_owned())
}

pub fn cache_path(video_id: &str) -> PathBuf {
    BaseDirs::new()
        .map(|b| b.cache_dir().join("chevren").join(format!("{video_id}.srt")))
        .unwrap_or_else(|| PathBuf::from(format!("/tmp/{video_id}.srt")))
}

async fn run_pipeline(url: &str, srt_path: &PathBuf) -> anyhow::Result<()> {
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

fn error_response(msg: &str) -> (StatusCode, Json<OpenResponse>) {
    (
        StatusCode::INTERNAL_SERVER_ERROR,
        Json(OpenResponse {
            status: "error".into(),
            message: msg.into(),
        }),
    )
}

#[derive(Deserialize)]
pub struct GenerateRequest {
    pub url: String,
}

pub async fn generate_handler(
    Json(req): Json<GenerateRequest>,
) -> Result<Json<OpenResponse>, (StatusCode, Json<OpenResponse>)> {
    let video_id = extract_video_id(&req.url).ok_or_else(|| {
        error_response("Geçersiz YouTube URL'si")
    })?;

    let srt_path = cache_path(&video_id);

    if srt_path.exists() {
        return Ok(Json(OpenResponse {
            status: "ok".into(),
            message: "cache'den hazır".into(),
        }));
    }

    run_pipeline(&req.url, &srt_path).await.map_err(|e| {
        error_response(&format!("Pipeline hatası: {e}"))
    })?;

    Ok(Json(OpenResponse {
        status: "ok".into(),
        message: "altyazı üretildi".into(),
    }))
}
