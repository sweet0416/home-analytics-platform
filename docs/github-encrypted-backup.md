# GitHub Encrypted Backup

HAP supports optional encrypted remote backups to GitHub Releases.

This feature is disabled by default.
Local Docker backups continue to work even when GitHub backup is disabled or misconfigured.

## Why not commit the database

Do not commit `hap.db` or plain `.db` backups to the source repository.

The database can contain lottery history, future fund or stock data, PVE and Docker metadata,
logs, task records, and other private operational data.
Remote backups must be encrypted before upload.

## Backup Flow

```text
SQLite backup
-> gzip compression
-> AES-GCM encryption
-> .db.gz.enc file
-> GitHub Release asset
```

## Recommended GitHub Setup

Create a separate private repository for encrypted backups, for example:

```text
sweet0416/hap-backups
```

Do not use the main source-code repository unless you intentionally want backup assets and source
code to share the same audit history.

## Token Permissions

Use a GitHub fine-grained personal access token limited to the backup repository.

Repository access:

```text
Only selected repositories -> sweet0416/hap-backups
```

Repository permissions:

```text
Contents: Read and write
```

Why:

- HAP reads a release by tag before upload.
- HAP creates the release if it does not exist.
- HAP uploads encrypted backup files as release assets.

GitHub's REST documentation states that reading releases/assets needs `Contents` read permission,
while creating releases and editing release assets need `Contents` write permission.

## Portainer Environment Variables

Add these variables to the `hap-backend` service in the Portainer stack:

```text
GITHUB_BACKUP_ENABLED=true
GITHUB_BACKUP_REPO=sweet0416/hap-backups
GITHUB_BACKUP_TOKEN=github_pat_xxx
GITHUB_BACKUP_RELEASE_TAG=hap-backups
GITHUB_BACKUP_ENCRYPTION_PASSPHRASE=<long-random-secret>
```

Keep these unchanged unless needed:

```text
GITHUB_BACKUP_TIMEOUT_SECONDS=30
```

## Encryption Passphrase

Use a long random value. Store it outside HAP, for example in your password manager.

If this passphrase is lost, encrypted GitHub backups cannot be decrypted.

The passphrase is not shown in the HAP UI and should never be committed to GitHub.

## Current Behavior

- Manual "create backup" creates a local Docker backup only.
- Scheduled backup creates a local Docker backup first.
- If GitHub backup is enabled and fully configured, the scheduled backup uploads an encrypted `.db.gz.enc` file.
- If GitHub upload fails, the local Docker backup remains successful and the remote status is marked failed.

## Restore Policy

Remote restore is intentionally not automatic yet.

The future restore flow should require:

- Download encrypted asset.
- Decrypt with the passphrase.
- Verify the SQLite file.
- Create a fresh pre-restore backup.
- Stop backend writes.
- Replace database.
- Restart service.
- Record an audit log.

This avoids accidental data loss.

## Official References

- GitHub REST API: Create a release
  https://docs.github.com/en/rest/releases/releases?apiVersion=2022-11-28#create-a-release
- GitHub REST API: Get a release by tag name
  https://docs.github.com/en/rest/releases/releases?apiVersion=2022-11-28#get-a-release-by-tag-name
- GitHub REST API: Upload a release asset
  https://docs.github.com/en/rest/releases/assets?apiVersion=2022-11-28#upload-a-release-asset
