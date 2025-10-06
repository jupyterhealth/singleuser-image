# make sure jupyterhub version matches
FROM quay.io/jupyter/scipy-notebook:2025-10-06

# install jupyterhub if we need to pin it
# RUN mamba install -y jupyterhub-core==5.2.1 \
 # && mamba clean -a

ARG PIP_CACHE_DIR=/tmp/pip-cache
COPY requirements.txt /src/requirements.txt
RUN --mount=type=cache,uid=1000,target=${PIP_CACHE_DIR} \
    pip install -r /src/requirements.txt
