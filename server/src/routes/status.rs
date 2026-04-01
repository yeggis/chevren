use crate::routes::open::cache_path;
use crate::state::SharedState;
use axum::{
    extract::{Query, State},
    Json,
};
use serde::Deserialize;
use serde_json::{json, Value};

#[derive(Deserialize)]
pub struct StatusQuery {
    v: Option<String>,
}

pub async fn handler(
    State(state): State<SharedState>,
    Query(query): Query<StatusQuery>,
) -> Json<Value> {
    let s = state.lock().unwrap();

    if let Some(vid) = &query.v {
        let is_active = s.video_id.as_deref() == Some(vid.as_str()) && s.stage != "idle";
        if !is_active {
            return if cache_path(vid).exists() {
                Json(json!({
                    "stage": "ready",
                    "video_id": vid,
                    "chunk": null,
                    "chunk_max": null,
                    "message": null
                }))
            } else {
                Json(json!({
                    "stage": "idle",
                    "video_id": vid,
                    "chunk": null,
                    "chunk_max": null,
                    "message": null
                }))
            };
        }
    }

    Json(serde_json::to_value(&*s).unwrap())
}
