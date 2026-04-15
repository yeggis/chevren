use axum::http::StatusCode;

pub async fn handler() -> StatusCode {
    tokio::spawn(async {
        tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
        std::process::exit(1);
    });
    StatusCode::NO_CONTENT
}
