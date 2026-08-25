# add sbin for sshd
export PATH=$PATH:/usr/sbin
# activate default env in login shells
export MAMBA_ROOT_PREFIX="${MAMBA_ROOT_PREFIX:-/srv/.pixi/envs/default}"
eval "$($MAMBA_ROOT_PREFIX/bin/mamba shell hook -s bash)"
mamba activate $MAMBA_ROOT_PREFIX
