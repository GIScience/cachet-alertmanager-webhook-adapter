FROM ghcr.io/astral-sh/uv:0.12-python3.14-trixie-slim

# curl is required for the health check in the docker-compose file
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt update && \
    apt install -y --no-install-recommends curl

ARG UID=1003
ARG GID=$UID
ARG USER=adapter
RUN groupadd -g $GID $USER && \
    useradd -u $UID -g $GID -ms /bin/bash $USER
USER $USER
WORKDIR /app

ENV UV_NO_DEV=1

RUN --mount=type=cache,uid=$UID,gid=$GID,target=/home/$USER/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

COPY --chown=$USER README.md pyproject.toml uv.lock ./
COPY --chown=$USER conf conf/
COPY --chown=$USER src src/
RUN --mount=type=cache,uid=$UID,gid=$GID,target=/home/$USER/.cache/uv \
    uv sync --locked

ENTRYPOINT ["uv", "run"]
CMD ["start-adapter"]

EXPOSE 8002