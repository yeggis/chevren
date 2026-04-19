use crate::state::SharedState;
use axum::{extract::State, http::StatusCode, response::IntoResponse};
use std::sync::atomic::Ordering;

/// GET /cancel/check — pipeline tarafından sorgulanır
pub async fn check_handler(State(state): State<SharedState>) -> impl IntoResponse {
    let flag = {
        let s = state.lock().unwrap();
        s.cancel_flag
            .as_ref()
            .map(|f| f.load(Ordering::Relaxed))
            .unwrap_or(false)
    };
    if flag {
        (StatusCode::OK, "cancel")
    } else {
        (StatusCode::OK, "ok")
    }
}
