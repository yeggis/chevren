use serde::Serialize;
use std::sync::atomic::AtomicBool;
use std::sync::{Arc, Mutex};

#[derive(Clone, Serialize, Default)]
pub struct PipelineState {
    pub stage: String,
    pub chunk: Option<u32>,
    pub chunk_max: Option<u32>,
    pub video_id: Option<String>,
    pub message: Option<String>,
    pub sub_track_id: Option<i64>,
    #[serde(skip)]
    pub cancel_flag: Option<Arc<AtomicBool>>,
}

pub type SharedState = Arc<Mutex<PipelineState>>;

pub fn new_shared() -> SharedState {
    Arc::new(Mutex::new(PipelineState {
        stage: "idle".into(),
        ..Default::default()
    }))
}
