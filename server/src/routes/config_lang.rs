use axum::{http::StatusCode, Json};
use serde::Deserialize;
use serde_json::Value;
use std::fs;

#[derive(Deserialize)]
pub struct LangRequest {
    pub lang: String,
}

pub async fn handler(Json(req): Json<LangRequest>) -> StatusCode {
    let lang = req.lang.trim().to_lowercase();
    if lang != "tr" && lang != "en" {
        return StatusCode::BAD_REQUEST;
    }

    let config_path = match directories::BaseDirs::new() {
        Some(b) => b.config_dir().join("chevren").join("config.json"),
        None => return StatusCode::INTERNAL_SERVER_ERROR,
    };

    let mut data: Value = if config_path.exists() {
        match fs::read_to_string(&config_path) {
            Ok(s) => serde_json::from_str(&s).unwrap_or(Value::Object(Default::default())),
            Err(_) => return StatusCode::INTERNAL_SERVER_ERROR,
        }
    } else {
        Value::Object(Default::default())
    };

    data["target_lang"] = Value::String(lang);

    match fs::write(&config_path, serde_json::to_string_pretty(&data).unwrap()) {
        Ok(_) => StatusCode::OK,
        Err(_) => StatusCode::INTERNAL_SERVER_ERROR,
    }
}
