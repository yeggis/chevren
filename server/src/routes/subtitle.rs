use axum::{extract::Path, http::StatusCode, response::IntoResponse};

use crate::routes::open::cache_path;

/// GET /subtitle/:id — SRT içeriğini döner
pub async fn handler(Path(video_id): Path<String>) -> impl IntoResponse {
    let srt_path = cache_path(&video_id);

    match tokio::fs::read_to_string(&srt_path).await {
        Ok(content) => (StatusCode::OK, content),
        Err(_) => (
            StatusCode::NOT_FOUND,
            format!("SRT bulunamadı: {video_id}"),
        ),
    }
}

/// DELETE /subtitle/:id — Cache'den SRT siler
pub async fn delete_handler(Path(video_id): Path<String>) -> impl IntoResponse {
    let srt_path = cache_path(&video_id);

    match tokio::fs::remove_file(&srt_path).await {
        Ok(_) => (StatusCode::OK, format!("Silindi: {video_id}")),
        Err(_) => (
            StatusCode::NOT_FOUND,
            format!("SRT bulunamadı: {video_id}"),
        ),
    }
}
