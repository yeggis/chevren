mod mpv;
mod routes;

use axum::{Router, routing::{get, post}};
use tower_http::cors::{CorsLayer, Any};
use tracing_subscriber::fmt;

#[tokio::main]
async fn main() {
    fmt::init();

    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    let app = Router::new()
        .route("/status",          get(routes::status::handler))
        .route("/open",            post(routes::open::handler))
        .route("/generate", post(routes::open::generate_handler))
        .route("/subtitle/:id",    get(routes::subtitle::handler))
        .route("/mpv/command",     post(routes::mpv_cmd::handler))
        .layer(cors);

    let listener = tokio::net::TcpListener::bind("127.0.0.1:7373")
        .await
        .expect("Port 7373 açılamadı");

    tracing::info!("chevren-server 127.0.0.1:7373 üzerinde çalışıyor");
    axum::serve(listener, app).await.unwrap();
}
