# Webservice for HERMES

```
docker build -t hermes-ws .
docker run --name hermes-ws -p 8088:8000 --network rt-ramsis_default --env-file .env -e POSTGRES_HOST=hermes-postgres --restart unless-stopped -d hermes-ws:latest
```