use crate::state::SharedState;
use axum::{extract::State, http::StatusCode, Json};
use serde::Deserialize;

#[derive(Deserialize)]
pub struct PipelineStatusRequest {
    pub stage: String,
    pub chunk: Option<u32>,
    pub video_id: Option<String>,
    pub message: Option<String>,
}

pub async fn handler(
    State(state): State<SharedState>,
    Json(req): Json<PipelineStatusRequest>,
) -> StatusCode {
    let mut s = state.lock().unwrap();

    // Farklı bir video'dan gelen stale status'u yoksay, 
    // ama eğer mevcut iş bittiyse (ready/error) yeni videoya izin ver.
    if let (Some(current), Some(incoming)) = (&s.video_id, &req.video_id) {
        let is_finished = s.stage == "ready" || s.stage == "error";
        if current != incoming && !is_finished {
            return StatusCode::OK;
        }
    }

    s.stage = req.stage;
    if let Some(c) = req.chunk {
        s.chunk = Some(c);
        s.chunk_max = Some(s.chunk_max.unwrap_or(0).max(c));
    }
    if req.video_id.is_some() {
        s.video_id = req.video_id;
    }
    if req.message.is_some() {
        s.message = req.message;
    }
    StatusCode::OK
}
