# singleuser-image for Jupyter Health pre-mvp

This repo builds and publishes https://quay.io/repository/jupyterhealth/singleuser-premvp for the jupyter health pre-MVP

The image is based on the scipy-notebook Jupyter image,
adding dependencies for commonhealth cloud API access.

## Installation

To install the contents of the repository locally, do the following

```bash
git clone git@github.com:jupyterhealth/singleuser-image.git
cd singleuser-image.git
python -m venv .venv
source ./.venv/bin/activate
pip install -r requirements.txt
```

## Testing the storage delegate locally

Ensure you have access to the AWS cloud and populate `~/.aws/config` with

```ini
[default]
aws_access_key_id = <access key from AWS>
aws_secret_access_key = <secret access key from AWS>
```

Then, launch a local Redis database with

```bash
docker run -d --name redis -p 6379:6379 redis
```

and start a local notebook.
