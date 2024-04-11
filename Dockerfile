FROM quay.io/jupyter/scipy-notebook:2024-04-01

# make sure jupyterhub version matches
RUN mamba install jupyterhub==4.1.5 \
 && mamba clean -pity

# have to do a bit of manual install to avoid commonhealth-cloud pins
RUN pip install --no-cache tink \
 && pip install --no-deps commonhealth-cloud-storage-client
