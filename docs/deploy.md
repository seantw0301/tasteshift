# Deployment

Public demo lives under a sub-path (`/tasteshift`) of an existing site.

- **Front end**: static export (`frontend/out/`) copied into the site's web directory. No Node process on the server.
- **Backend**: FastAPI on `127.0.0.1:8010`, kept outside the web root so source and the virtualenv are not served as files.
- **Qloo key**: only on the server (harness config or the service's environment), never in the static bundle.

## One-time server setup (not automated)

```bash
python3 -m venv /opt/tasteshift-api/.venv
/opt/tasteshift-api/.venv/bin/pip install -r /opt/tasteshift-api/requirements.txt
```

`/etc/systemd/system/tasteshift-api.service`:

```ini
[Unit]
Description=TasteShift API
After=network.target

[Service]
WorkingDirectory=/opt/tasteshift-api
Environment=CORS_ORIGINS=https://demo.example.com
ExecStart=/opt/tasteshift-api/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8010
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

nginx, inside the site's `server` block:

```nginx
location /tasteshift/api/ {
    proxy_pass http://127.0.0.1:8010/api/;
}
```

## Each release

```bash
scripts/deploy.sh
```

Fill `DEPLOY_*` in `.env` first (see `.env.example`). The script runs tests, builds, and copies files with `rsync --delete`, so the two target directories must contain nothing else.
