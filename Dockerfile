FROM ghcr.io/astral-sh/uv:0.9-python3.13-bookworm-slim

SHELL ["/bin/bash", "-c"]

RUN apt update && \
    apt install -y curl

WORKDIR /app

ENV UV_NO_DEV=1

COPY pyproject.toml pyproject.toml
COPY uv.lock uv.lock

RUN uv sync --locked --no-install-project

COPY . /app
RUN uv sync --locked

ENTRYPOINT ["uv", "run"]
CMD ["start-adapter"]

EXPOSE 8002