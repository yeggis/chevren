use axum::{Json, http::StatusCode};
use serde::{Deserialize, Serialize};

use crate::mpv;

#[derive(Deserialize)]
pub struct MpvRequest {
    pub command: Vec<serde_json::Value>,
}

#[derive(Serialize)]
pub struct MpvResponse {
    pub status: String,
}

pub async fn handler(
    Json(req): Json<MpvRequest>,
) -> Result<Json<MpvResponse>, (StatusCode, Json<MpvResponse>)> {
    mpv::send_command(&req.command).await.map_err(|e| {
        tracing::warn!("mpv komutu gönderilemedi: {e}");
        (
            StatusCode::SERVICE_UNAVAILABLE,
            Json(MpvResponse { status: format!("mpv hatası: {e}") }),
        )
    })?;

    Ok(Json(MpvResponse { status: "ok".into() }))
}
