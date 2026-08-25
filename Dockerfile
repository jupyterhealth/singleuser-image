FROM ghcr.io/prefix-dev/pixi:0.77.1 AS build
# git needed for dev lightcone
RUN pixi global install git

# copy source code, pixi.toml and pixi.lock to the container
COPY pixi* /srv/
WORKDIR /srv/
RUN pixi install
COPY install-opencode.sh /srv/
RUN pixi run install-opencode

FROM debian:13

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        ca-certificates \
        git \
        nano \
        procps \
        vim \
        wget \
 && rm -rf /var/lib/apt/lists/*
 
ARG UID=1000
RUN useradd -m -u 1000 jovyan
COPY --from=build --chown=1000:1000 /srv/.pixi/envs/default /srv/.pixi/envs/default
COPY mamba.sh /etc/profile.d/
COPY entrypoint.sh /entrypoint.sh
COPY mambarc /srv/.pixi/envs/default/.condarc

ENV PYTHONUNBUFFERED=1 \
    MAMBA_ROOT_PREFIX=/srv/.pixi/envs/default \
    PATH=/srv/.pixi/envs/default/bin:$PATH:/usr/sbin \
    SHELL=/usr/bin/bash
WORKDIR /home/jovyan
RUN chsh jovyan --shell /bin/bash
USER $UID

ENTRYPOINT ["/entrypoint.sh"]
CMD ["jupyterhub-singleuser"]
