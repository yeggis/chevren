use crate::state::SharedState;
use axum::{extract::State, Json};
use serde_json::Value;

pub async fn handler(State(state): State<SharedState>) -> Json<Value> {
    let s = state.lock().unwrap();
    Json(serde_json::to_value(&*s).unwrap())
}
