# Per-install Postgres password for the bundled database. Kept separate from
# APP_SEED, which the panel uses as its data encryption key.
export APP_CALAGOPUS_PANEL_AIO_DB_PASSWORD="$(derive_entropy "env-${app_entropy_identifier}-DB_PASSWORD" | head -c32)"
