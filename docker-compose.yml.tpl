version: '3.7'

# DB config
x-dbconfig_env: &dbconfig_env
  DB_HOST: db
  DB_USER: &dbuser postgres
  DB_DATABASE: &dbname pvarki
  DB_PASSWORD: &dbpass {{.Env.DB_PASSWORD}} # pragma: allowlist secret
  DB_PORT: &dbport 5432

# Mailer config (don't ask about some of the key names)
x-mailconfig_env: &mailconfig_env
  MAIL_FROM: "{{getenv "MAIL_FROM" "noreply@pvarki.fi"}}"
  #SUPPRESS_SEND: 1 # If you need to suppress for a moment
  MAIL_USERNAME: "{{.Env.MAIL_USERNAME}}" # MUST be set even if not used
  MAIL_PASSWORD: ""{{.Env.MAIL_PASSWORD}}" # MUST be set even if not used"
  USE_CREDENTIALS: "1" # Set to 1 if you need user/pass for the server
  MAIL_PORT: {{.Env.MAIL_PORT}}
  MAIL_SERVER: {{.Env.MAIL_SERVER}}
  MAIL_STARTTLS: "{{getenv "MAIL_STARTTLS" "1"}}" # Try to upgrade to TLS
  MAIL_SSL_TLS: "{{getenv "MAIL_SSL_TLS" "0"}}" # Force TLS

x-security_env: &security_env
  JWT_PRIVKEY_PATH: "0"
  JWT_PUBKEY_PATH: "/app/jwtRS256.pub"
  PIPELINE_TOKEN_KEYVAULT: "{{getenv "PIPELINE_TOKEN_KEYVAULT" "pvarki-shared-kv001"}}"
  # Use these while we cannot use security principals to access the keyvauls
  PIPELINE_SSHKEY_OVERRIDE: "{{getenv "PIPELINE_SSHKEY_OVERRIDE" ""}}"
  PIPELINE_TOKEN_OVERRIDE: "{{getenv "PIPELINE_TOKEN_OVERRIDE" ""}}"


services:
  db:
    image: postgres:15.1
    environment:
      POSTGRES_USER: *dbuser
      POSTGRES_DB: *dbname
      POSTGRES_PASSWORD: *dbpass # pragma: allowlist secret
      LC_COLLATE: "C.UTF-8"
    ports:
      - target: 5432
        published: *dbport
        protocol: tcp
        mode: host
    networks:
      - dbnet
    healthcheck:
      test: "pg_isready --dbname=$$POSTGRES_DB --username=$$POSTGRES_USER -q"
      interval: 5s
      timeout: 5s
      retries: 3
      start_period: 5s
    volumes:
      - 'db_data:/var/lib/postgresql/data'

  dbinit:
    image: pvarki/takbackend:migrations
    build:
      context: .
      dockerfile: Dockerfile
      target: migrations
    environment:
      <<: *dbconfig_env
    networks:
      - dbnet
    depends_on:
      db:
        condition: service_healthy

  api:
    image: pvarki/takbackend:latest
    build:
      context: .
      dockerfile: Dockerfile
      target: production
    environment:
      <<: *dbconfig_env
      <<: *mailconfig_env
      <<: *security_env
    volumes:
      - {{getenv "HOST_PUBKEY_PATH" "./jwt.pub"}}:/app/jwtRS256.pub
    depends_on:
      db:
        condition: service_healthy
      dbinit:
        condition: service_completed_successfully
    networks:
      - dbnet
    expose:
      - 8000
    ports:
      - "8000:8000"
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.fastapi.rule=Host(`{{.Env.SERVER_ADDRESS}}`)"
      - "traefik.http.routers.fastapi.tls=true"
      - "traefik.http.routers.fastapi.tls.certresolver=letsencrypt"

  traefik:
    image: traefik:v2.2
    networks:
      - dbnet
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
      - "./traefik.toml:/etc/traefik/traefik.toml"
      - "le_data:/letsencrypt"
      - "acme_data:/etc/traefik/acme"

networks:
  dbnet:

volumes:
  acme_data:
    driver: local
  le_data:
    driver: local
  db_data:
    driver: local
