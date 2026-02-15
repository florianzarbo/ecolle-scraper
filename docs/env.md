# .env configuration

This project is configured via environment variables (typically stored in a `.env` file).

Only the variables that are **not commented out** in `.env.example` are required; commented ones are optional.

## Setup

1. Copy the template:

        cp .env.example .env


2. Edit `.env` and set the required values.
3. Do **not** commit `.env` (it contains secrets).

## Required variables

### `BASE_URL`

Base URL of your institution's e-colle website.

- Example:

  
        BASE_URL="https://ecolle.example.com"
  

- Notes: Include `https://` and use the site's base URL (no extra path unless required by your institution).

***

### `COLLES_USERNAME`

Your e-colle username (used to authenticate and fetch your colle agenda).

- Example:

        COLLES_USERNAME=YourUsername

***

### `COLLES_PASSWORD`

Your e-colle password (used to authenticate).

- Example:

        COLLES_PASSWORD=YourPassword

- Security: Treat as a secret; prefer secret storage (CI secrets, systemd credentials, etc.) when possible.

***

### `NUMBER_OF_COLLES_TO_SHOW`

How many upcoming colles to display/send.

- Example:

        NUMBER_OF_COLLES_TO_SHOW=1


- Type: integer (`1`, `2`, `3`, …)

***

### `NTFY_TOPIC`

The ntfy topic to publish notifications to.

- Example:

        NTFY_TOPIC=YourTopicName


- Tip: If using a public ntfy server, use a random topic name to reduce the risk of others guessing it.

***

### `NTFY_TITLE`

The title used for notifications.

- Example:

        NTFY_TITLE="Today's colles"


- Tip: Keep quotes if there are spaces.

***

## Optional variables

### `NTFY_SERVER`

URL of your ntfy instance.

- Default: `https://ntfy.sh`
- Set this only if you use a custom/self-hosted ntfy server.
- Example:

        NTFY_SERVER=https://ntfy.example.org

***

### `SELF_SIGNED_CERTIFICATE`

Enable only if your server uses a self-signed TLS certificate.

- Default: `False`
- Example:

        SELF_SIGNED_CERTIFICATE=true

***

### `ROOT_CA_PATH`

Path to the Root CA file (PEM) that signed your TLS certificate.

- Example:

        ROOT_CA_PATH=/path/to/rootCA.pem

***

## Example `.env`

```env
BASE_URL="https://ecolle.example.com"
COLLES_USERNAME=alice
COLLES_PASSWORD=change-me
NUMBER_OF_COLLES_TO_SHOW=2

NTFY_TOPIC=mp2i-9f3a2c1d
NTFY_TITLE="Today's colles"

# Optional:
# NTFY_SERVER=https://ntfy.example.org
# SELF_SIGNED_CERTIFICATE=true
# ROOT_CA_PATH=/etc/ssl/my-rootCA.pem
```

## Troubleshooting

- Authentication errors: Double-check `BASE_URL`, `COLLES_USERNAME`, and `COLLES_PASSWORD`.
- No notifications: Verify `NTFY_TOPIC` (and `NTFY_SERVER` if you set it).
- TLS issues with self-hosted ntfy: Set `SELF_SIGNED_CERTIFICATE=true` and provide a valid `ROOT_CA_PATH`.
