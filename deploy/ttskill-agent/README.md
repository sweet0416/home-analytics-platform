# ttskill-agent bootstrap container

The Docker build downloads the pinned official package and verifies its SHA256
before installing it. The package is intentionally not committed to Git.

Build and inspect:

```bash
docker compose --profile ttskill build ttskill-agent
docker compose --profile ttskill run --rm ttskill-agent status --json
```

The official CLI generates a callback at `127.0.0.1:8765`. When Chrome is on
another machine, create an SSH tunnel from Windows to the Docker VM:

```powershell
ssh -N -L 8765:127.0.0.1:8765 root@192.168.100.249
```

Keep that window open, then run on the Docker VM:

```bash
docker compose --profile ttskill run --rm --service-ports ttskill-agent login --env prod
```

Do not put tokens or credentials in Git.
