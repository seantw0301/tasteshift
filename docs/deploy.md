# Deployment

Public demo lives under a sub-path (`/tasteshift`) of an existing site.

- **Front end**: static export (`frontend/out/`) copied into the site's web directory. No Node process on the server.
- **Backend**: FastAPI on `127.0.0.1:8010`, kept outside the web root so source and the virtualenv are not served as files.
- **Qloo key**: only on the server (harness config or the service's environment), never in the static bundle.

## One-time server setup

```bash
scripts/deploy.sh         # copies files
scripts/server_setup.sh   # venv, systemd service, nginx proxy, reload
```

`server_setup.sh` writes `tasteshift-api.service` and a `tasteshift.conf` in the site's nginx extension directory, tests the nginx config and reloads it only if the test passes.

## Each release

```bash
scripts/deploy.sh
```

Fill `DEPLOY_*` in `.env` first (see `.env.example`). The script runs tests, builds, and copies files with `rsync --delete`, so the two target directories must contain nothing else.
