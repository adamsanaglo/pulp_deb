from pathlib import Path

# A pure-standard-lib implementation of reading KEY=VALUE pairs out of an .env file.
# Currently the only setting is SIGNER_HOST.
settings = {"SIGNER_HOST": "127.0.0.1"}
env_file = Path(__file__).parent / ".env"
if env_file.is_file():
    with env_file.open("r") as f:
        for line in f:
            key, value = line.split("=", 1)
            settings[key.strip()] = value.strip()
