use axum::{extract::Path, http::StatusCode, response::IntoResponse};

use crate::routes::open::cache_path;

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
