FROM quay.io/jupyter/scipy-notebook:2024-04-01

# make sure jupyterhub version matches
RUN mamba install -y jupyterhub==4.1.5 \
 && mamba clean -pity

# have to do a bit of manual install to avoid commonhealth-cloud pins
ARG PIP_CACHE_DIR=/tmp/pip-cache
RUN --mount=type=cache,target=${PIP_CACHE_DIR} \
    pip install tink \
 && pip install --no-deps commonhealth-cloud-storage-client

COPY . /src/
RUN --mount=type=cache,target=${PIP_CACHE_DIR} \
    pip install /src/
