FROM quay.io/jupyter/scipy-notebook:2024-04-01

# make sure jupyterhub version matches
RUN mamba install -y jupyterhub==4.1.5 \
 && mamba clean -pity

ARG PIP_CACHE_DIR=/tmp/pip-cache
COPY . /src/
RUN --mount=type=cache,uid=1000,target=${PIP_CACHE_DIR} \
    cd /src/ && \
    pip install -r requirements.txt .
