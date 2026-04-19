use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::IntoResponse,
    Json,
};

use crate::routes::open::cache_path;
use crate::state::SharedState;
use serde::Deserialize;
use std::path::PathBuf;

/// GET /subtitle/:id — SRT içeriğini döner
pub async fn handler(Path(video_id): Path<String>) -> impl IntoResponse {
    let srt_path = cache_path(&video_id);

    match tokio::fs::read_to_string(&srt_path).await {
        Ok(content) => (StatusCode::OK, content),
        Err(_) => (StatusCode::NOT_FOUND, format!("SRT bulunamadı: {video_id}")),
    }
}

/// DELETE /subtitle/:id — Cache'den tüm video klasörünü siler, state'i sıfırlar
pub async fn delete_handler(
    Path(video_id): Path<String>,
    State(state): State<SharedState>,
) -> impl IntoResponse {
    {
        let mut s = state.lock().unwrap();
        if s.video_id.as_deref() == Some(&video_id) {
            if let Some(flag) = &s.cancel_flag {
                flag.store(true, std::sync::atomic::Ordering::Relaxed);
            }
            s.stage = "idle".into();
            s.chunk = None;
            s.chunk_max = None;
            s.video_id = None;
            s.message = None;
            s.cancel_flag = None;
        }
    }
    let base = directories::BaseDirs::new()
        .map(|b| b.cache_dir().join("chevren").join(&video_id))
        .unwrap_or_else(|| std::path::PathBuf::from(format!("/tmp/chevren/{video_id}")));

    if base.exists() {
        match tokio::fs::remove_dir_all(&base).await {
            Ok(_) => (StatusCode::OK, format!("Silindi: {video_id}")),
            Err(e) => (
                StatusCode::INTERNAL_SERVER_ERROR,
                format!("Silinemedi: {e}"),
            ),
        }
    } else {
        (
            StatusCode::NOT_FOUND,
            format!("Cache bulunamadı: {video_id}"),
        )
    }
}

#[derive(Deserialize)]
pub struct ReloadRequest {
    pub path: String,
}

pub async fn reload_handler(
    State(state): State<SharedState>,
    Json(req): Json<ReloadRequest>,
) -> impl IntoResponse {
    let path = PathBuf::from(&req.path);

    let track_id = {
        let s = state.lock().unwrap();
        s.sub_track_id
    };

    if let Some(id) = track_id {
        match crate::mpv::reload_subtitle(id).await {
            Ok(_) => (StatusCode::OK, "altyazı yenilendi".to_string()),
            Err(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()),
        }
    } else {
        match crate::mpv::add_subtitle(&path).await {
            Ok(new_id) => {
                let mut s = state.lock().unwrap();
                s.sub_track_id = Some(new_id);
                (StatusCode::OK, "altyazı eklendi".to_string())
            }
            Err(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()),
        }
    }
}
