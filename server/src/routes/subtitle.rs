use axum::{extract::Path, http::StatusCode, response::IntoResponse};

use crate::routes::open::cache_path;

/// GET /subtitle/:id — SRT içeriğini döner
pub async fn handler(Path(video_id): Path<String>) -> impl IntoResponse {
    let srt_path = cache_path(&video_id);

    match tokio::fs::read_to_string(&srt_path).await {
        Ok(content) => (StatusCode::OK, content),
        Err(_) => (StatusCode::NOT_FOUND, format!("SRT bulunamadı: {video_id}")),
    }
}

/// DELETE /subtitle/:id — Cache'den SRT siler
pub async fn delete_handler(Path(video_id): Path<String>) -> impl IntoResponse {
    let srt_path = cache_path(&video_id);

    match tokio::fs::remove_file(&srt_path).await {
        Ok(_) => (StatusCode::OK, format!("Silindi: {video_id}")),
        Err(_) => (StatusCode::NOT_FOUND, format!("SRT bulunamadı: {video_id}")),
    }
}

use axum::Json;
use serde::Deserialize;
use std::path::PathBuf;

#[derive(Deserialize)]
pub struct ReloadRequest {
    pub path: String,
}

pub async fn reload_handler(Json(req): Json<ReloadRequest>) -> impl IntoResponse {
    let path = PathBuf::from(&req.path);
    match crate::mpv::update_subtitle(&path).await {
        Ok(_) => (StatusCode::OK, "altyazı güncellendi".to_string()),
        Err(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()),
    }
}
