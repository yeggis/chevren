mod mpv;
mod routes;
mod state;

use axum::{
    routing::{get, post},
    Router,
};
use tower_http::cors::{Any, CorsLayer};
use tracing_subscriber::fmt;

#[tokio::main]
async fn main() {
    fmt::init();

    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    let shared_state = state::new_shared();

    let app = Router::new()
        .route("/status", get(routes::status::handler))
        .route("/pipeline/status", post(routes::pipeline_status::handler))
        .route("/open", post(routes::open::handler))
        .route("/generate", post(routes::open::generate_handler))
        .route("/subtitle/reload", post(routes::subtitle::reload_handler))
        .route(
            "/subtitle/:id",
            get(routes::subtitle::handler).delete(routes::subtitle::delete_handler),
        )
        .route("/mpv/command", post(routes::mpv_cmd::handler))
        .route("/restart", post(routes::restart::handler))
        .route("/config/lang", post(routes::config_lang::handler))
        .route("/cancel/check", get(routes::cancel::check_handler))
        .with_state(shared_state)
        .layer(cors);

    let listener = tokio::net::TcpListener::bind("127.0.0.1:7373")
        .await
        .expect("Port 7373 açılamadı");

    tracing::info!("chevren-server 127.0.0.1:7373 üzerinde çalışıyor");
    axum::serve(listener, app).await.unwrap();
}
