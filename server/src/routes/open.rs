use crate::mpv;
use crate::state::SharedState;
use axum::{extract::State, http::StatusCode, Json};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use tokio::process::Command;

#[derive(Deserialize)]
pub struct OpenRequest {
    pub url: String,
}

#[derive(Deserialize)]
pub struct GenerateRequest {
    pub url: String,
}

#[derive(Serialize)]
pub struct OpenResponse {
    pub status: String,
    pub message: String,
}

// ── /open — mpv modu (değişmedi) ────────────────────────────────────────────
pub async fn handler(
    State(state): State<SharedState>,
    Json(req): Json<OpenRequest>,
) -> Result<Json<OpenResponse>, (StatusCode, Json<OpenResponse>)> {
    let video_id =
        extract_video_id(&req.url).ok_or_else(|| error_response("Geçersiz YouTube URL'si"))?;
    let srt_path = cache_path(&video_id);
    if !srt_path.exists() {
        // generate_handler zaten çalışıyorsa, bitmesini bekle
        loop {
            let busy = {
                let s = state.lock().unwrap();
                matches!(s.stage.as_str(), "downloading" | "transcribing" | "translating")
            };
            if !busy { break; }
            tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
        }
        // Bekleme sonrası hâlâ yoksa kendi pipeline'ını çalıştır
        if !srt_path.exists() {
            run_pipeline_blocking(&req.url, &srt_path)
                .await
                .map_err(|e| error_response(&format!("Pipeline hatası: {e}")))?;
        }
    }
    mpv::open_with_subtitle(&req.url, &srt_path, &state)
        .await
        .map_err(|e| error_response(&format!("mpv hatası: {e}")))?;
    Ok(Json(OpenResponse {
        status: "ok".into(),
        message: "mpv açıldı".into(),
    }))
}

// ── /generate — extension için, anında döner, arka planda çalışır ───────────
pub async fn generate_handler(
    State(state): State<SharedState>,
    Json(req): Json<GenerateRequest>,
) -> Result<Json<OpenResponse>, (StatusCode, Json<OpenResponse>)> {
    // Zaten çalışıyorsa reddet
    {
        let s = state.lock().unwrap();
        let busy = matches!(
            s.stage.as_str(),
            "downloading" | "transcribing" | "translating"
        );
        if busy {
            return Err(error_response("Pipeline zaten çalışıyor"));
        }
    }

    let video_id =
        extract_video_id(&req.url).ok_or_else(|| error_response("Geçersiz YouTube URL'si"))?;
    let target_lang = read_target_lang().unwrap_or_else(|| "tr".to_string());
    let srt_path = cache_path_for_lang(&video_id, &target_lang);

    // Cache'de bu dil için SRT varsa pipeline çalıştırma
    let cache_hit = srt_path.metadata().map(|m| m.len() > 0).unwrap_or(false);
    if cache_hit {
        let mut s = state.lock().unwrap();
        s.stage = "ready".into();
        s.video_id = Some(video_id);
        s.chunk = None;
        s.message = None;
        return Ok(Json(OpenResponse {
            status: "ok".into(),
            message: "cache'den hazır".into(),
        }));
    }

    let cancel_flag = std::sync::Arc::new(std::sync::atomic::AtomicBool::new(false));
    {
        let mut s = state.lock().unwrap();
        s.stage = "downloading".into();
        s.video_id = Some(video_id.clone());
        s.chunk = None;
        s.chunk_max = None;
        s.message = None;
        s.cancel_flag = Some(cancel_flag.clone());
    }

    // Arka planda başlat
    let state_clone = state.clone();
    let url = req.url.clone();
    tokio::spawn(async move {
        run_pipeline_tracked(url, state_clone).await;
    });

    Ok(Json(OpenResponse {
        status: "ok".into(),
        message: "pipeline başlatıldı".into(),
    }))
}

// ── Arka plan pipeline — artık sadece bekler, status Python tarafından HTTP ile güncellenir ─
async fn run_pipeline_tracked(url: String, state: SharedState) {
    // cancel_flag state içinde tutuluyor, ayrıca parametre gerekmez
    let status = Command::new("chevren")
        .args(["--no-play", &url])
        .status()
        .await;

    match status {
        Ok(s) if s.success() => {
            let mut s = state.lock().unwrap();
            if s.stage != "ready" && s.stage != "error" {
                s.stage = "ready".into();
            }
        }
        _ => {
            let mut s = state.lock().unwrap();
            if s.stage != "ready" {
                s.stage = "error".into();
                if s.message.is_none() {
                    s.message = Some("Pipeline başarısız oldu".into());
                }
            }
        }
    }
}
// ── Blocking pipeline — mpv modu için ────────────────────────────────────────
async fn run_pipeline_blocking(url: &str, srt_path: &PathBuf) -> anyhow::Result<()> {
    if let Some(parent) = srt_path.parent() {
        tokio::fs::create_dir_all(parent).await?;
    }
    let status = Command::new("chevren")
        .args(["--no-play", url])
        .status()
        .await?;
    if !status.success() {
        anyhow::bail!("chevren pipeline başarısız oldu");
    }
    Ok(())
}

// ── Yardımcılar ───────────────────────────────────────────────────────────────
pub fn extract_video_id(url: &str) -> Option<String> {
    let url = url::Url::parse(url).ok()?;
    url.query_pairs()
        .find(|(k, _)| k == "v")
        .map(|(_, v)| v.into_owned())
}

pub fn cache_path(video_id: &str) -> PathBuf {
    cache_path_for_lang(video_id, &read_target_lang().unwrap_or_else(|| "tr".to_string()))
}

pub fn cache_path_for_lang(video_id: &str, target_lang: &str) -> PathBuf {
    let base = directories::BaseDirs::new()
        .map(|b| b.cache_dir().join("chevren").join(video_id))
        .unwrap_or_else(|| PathBuf::from(format!("/tmp/chevren/{video_id}")));
    let target = base.join(format!("{target_lang}.srt"));
    let en = base.join("en.srt");
    let non_empty = |p: &std::path::Path| {
        p.metadata().map(|m| m.len() > 0).unwrap_or(false)
    };
    if non_empty(&target) {
        target
    } else if non_empty(&en) {
        en
    } else {
        base.join(format!("{target_lang}.srt"))
    }
}

fn read_target_lang() -> Option<String> {
    let config_path = directories::BaseDirs::new()?
        .config_dir()
        .join("chevren")
        .join("config.json");
    let text = std::fs::read_to_string(config_path).ok()?;
    let val: serde_json::Value = serde_json::from_str(&text).ok()?;
    val.get("target_lang")?.as_str().map(|s| s.to_string())
}

fn error_response(msg: &str) -> (StatusCode, Json<OpenResponse>) {
    (
        StatusCode::INTERNAL_SERVER_ERROR,
        Json(OpenResponse {
            status: "error".into(),
            message: msg.into(),
        }),
    )
}
