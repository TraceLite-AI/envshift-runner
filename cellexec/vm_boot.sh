#!/usr/bin/env bash
# gh-vm cell: boot an Ubuntu 24.04 cloud image under QEMU/KVM on the runner and leave it running with ssh on
# 127.0.0.1:2222 (root, key auth). Exports CELL_SSH_* to $GITHUB_ENV for cell_run.py.
# Same realisation as sandbox-verify.yml "probe (QEMU/KVM guest)", plus ssh; noble instead of jammy so the
# guest python (3.12) matches the base cell.
set -euo pipefail
W="${RUNNER_TEMP:-/tmp}/vm"; mkdir -p "$W"; cd "$W"
sudo apt-get update -q >/dev/null && sudo apt-get install -y -q qemu-system-x86 qemu-utils cloud-image-utils >/dev/null
sudo chmod 666 /dev/kvm
rm -f key key.pub; ssh-keygen -q -t ed25519 -N '' -f key
curl -fsSL -o base.img https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img
qemu-img create -f qcow2 -F qcow2 -b base.img disk.qcow2 16G >/dev/null
{
  echo '#cloud-config'
  echo 'disable_root: false'
  echo 'ssh_pwauth: false'
  echo 'package_update: false'
  echo 'package_upgrade: false'
  echo 'ssh_authorized_keys:'
  echo "  - $(cat key.pub)"
} > user-data
cloud-localds seed.img user-data
qemu-system-x86_64 -enable-kvm -cpu host -m 4096 -smp 2 -display none -serial file:serial.log -monitor none \
  -daemonize -pidfile qemu.pid \
  -drive file=disk.qcow2,if=virtio -drive file=seed.img,if=virtio,format=raw \
  -netdev user,id=n0,hostfwd=tcp:127.0.0.1:2222-:22 -device virtio-net-pci,netdev=n0
SSH="ssh -i $W/key -p 2222 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o BatchMode=yes -o ConnectTimeout=10"
for i in $(seq 1 90); do
  if $SSH root@127.0.0.1 'cloud-init status --wait >/dev/null 2>&1; true' 2>/dev/null; then break; fi
  sleep 5
done
$SSH root@127.0.0.1 'systemd-detect-virt; python3 -V; uname -r' || { tail -c 4000 serial.log; exit 1; }
{
  echo "CELL_SSH_HOST=127.0.0.1"; echo "CELL_SSH_PORT=2222"; echo "CELL_SSH_USER=root"; echo "CELL_SSH_KEY=$W/key"
} >> "$GITHUB_ENV"
