from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def read(relative_path: str) -> str:
    return (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")


def test_frontend_proxy_has_api_routing_spa_fallback_and_security_limits():
    config = read("frontend/nginx.production.conf")

    assert "location /api/" in config
    assert "proxy_pass http://backend:8000/;" in config
    assert "try_files $uri $uri/ /index.html;" in config
    assert "Content-Security-Policy" in config
    assert "frame-ancestors 'none'" in config
    assert "X-Content-Type-Options" in config
    assert "Referrer-Policy" in config
    assert "client_max_body_size" in config
    assert "proxy_connect_timeout" in config
    assert "proxy_read_timeout" in config


def test_edge_proxy_has_https_security_headers():
    config = read("deploy/production/Caddyfile")

    assert "reverse_proxy frontend:8080" in config
    assert "Strict-Transport-Security" in config
    assert "X-Content-Type-Options" in config
    assert "Referrer-Policy" in config
    assert "X-Frame-Options" in config


def test_reference_runtime_does_not_use_development_servers():
    compose = read("docker-compose.production.example.yml")
    backend_dockerfile = read("backend/Dockerfile")
    frontend_dockerfile = read("frontend/Dockerfile")

    assert "--reload" not in compose
    assert "--reload" not in backend_dockerfile
    assert "npm run dev" not in frontend_dockerfile
    assert "npm run preview" not in frontend_dockerfile
    assert 'VITE_API_BASE_URL: /api' in compose
    assert 'VITE_PUBLIC_DEMO: "0"' in compose
