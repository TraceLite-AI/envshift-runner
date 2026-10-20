#!/usr/bin/env bash
# gh-microvm cell: boot the Firecracker CI Ubuntu 24.04 rootfs with a tap network and sshd, leave it running,
# export CELL_SSH_* to $GITHUB_ENV. Kernel/rootfs lookup is the one from sandbox-verify.yml; networking and
# the ssh key follow Firecracker's docs/getting-started.md (guest IP is derived from the MAC by fcnet-setup).
set -euo pipefail
W="${RUNNER_TEMP:-/tmp}/fc"; mkdir -p "$W"; cd "$W"
sudo chmod 666 /dev/kvm
sudo apt-get update -q >/dev/null && sudo apt-get install -y -q squashfs-tools >/dev/null
A=x86_64; R=https://github.com/firecracker-microvm/firecracker/releases
L=$(basename "$(curl -fsSLI -o /dev/null -w '%{url_effective}' $R/latest)")
curl -fsSL "$R/download/$L/firecracker-$L-$A.tgz" | tar -xz; mv "release-$L-$A/firecracker-$L-$A" fc
K=""; U=""
for CI in ${L%.*} v1.16 v1.15 v1.14 v1.13 v1.12 v1.11 v1.10; do
  K=$(curl -s "http://spec.ccfc.min.s3.amazonaws.com/?prefix=firecracker-ci/$CI/$A/vmlinux-&list-type=2" | grep -oP "(?<=<Key>)(firecracker-ci/$CI/$A/vmlinux-[0-9]+\.[0-9]+\.[0-9]{1,3})(?=</Key>)" | sort -V | tail -1 || true)
  U=$(curl -s "http://spec.ccfc.min.s3.amazonaws.com/?prefix=firecracker-ci/$CI/$A/ubuntu-&list-type=2" | grep -oP "(?<=<Key>)(firecracker-ci/$CI/$A/ubuntu-[0-9]+\.[0-9]+\.squashfs)(?=</Key>)" | sort -V | tail -1 || true)
  [ -n "$K" ] && [ -n "$U" ] && break
done
echo "kernel=$K rootfs=$U" >&2
curl -fsSL -o vmlinux "https://s3.amazonaws.com/spec.ccfc.min/$K"
curl -fsSL -o root.squashfs "https://s3.amazonaws.com/spec.ccfc.min/$U"
sudo rm -rf rootfs; sudo unsquashfs -q -d rootfs root.squashfs
rm -f key key.pub; ssh-keygen -q -t ed25519 -N '' -f key
sudo mkdir -p rootfs/root/.ssh && sudo cp key.pub rootfs/root/.ssh/authorized_keys && sudo chmod 600 rootfs/root/.ssh/authorized_keys
echo "nameserver 8.8.8.8" | sudo tee rootfs/etc/resolv.conf >/dev/null || true
sudo chown -R root:root rootfs
rm -f rootfs.ext4; truncate -s 4G rootfs.ext4 && sudo mkfs.ext4 -q -d rootfs -F rootfs.ext4
# tap network (guest 172.16.0.2, host 172.16.0.1) + NAT so the guest has the same egress as the other cells
TAP=tap0
sudo ip link del $TAP 2>/dev/null || true
sudo ip tuntap add dev $TAP mode tap user "$(id -u)"
sudo ip addr add 172.16.0.1/30 dev $TAP && sudo ip link set dev $TAP up
HOSTIF=$(ip -o route get 8.8.8.8 | awk '{for(i=1;i<=NF;i++) if($i=="dev"){print $(i+1); exit}}')
sudo sysctl -q -w net.ipv4.ip_forward=1
sudo iptables -t nat -A POSTROUTING -o "$HOSTIF" -j MASQUERADE
sudo iptables -P FORWARD ACCEPT
cat > vm.json <<JSON
{"boot-source": {"kernel_image_path": "vmlinux", "boot_args": "console=ttyS0 reboot=k panic=1 pci=off"},
 "drives": [{"drive_id": "rootfs", "path_on_host": "rootfs.ext4", "is_root_device": true, "is_read_only": false}],
 "network-interfaces": [{"iface_id": "net1", "guest_mac": "06:00:AC:10:00:02", "host_dev_name": "$TAP"}],
 "machine-config": {"vcpu_count": 2, "mem_size_mib": 4096}}
JSON
setsid nohup ./fc --no-api --config-file vm.json > serial.log 2>&1 < /dev/null &
echo $! > fc.pid
SSH="ssh -i $W/key -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o BatchMode=yes -o ConnectTimeout=5"
for i in $(seq 1 60); do
  if $SSH root@172.16.0.2 true 2>/dev/null; then break; fi
  sleep 3
done
$SSH root@172.16.0.2 'ip route add default via 172.16.0.1 dev eth0 2>/dev/null; systemd-detect-virt; ls /sys/bus/pci/devices 2>/dev/null | wc -l; python3 -V; uname -r' \
  || { tail -c 4000 serial.log; exit 1; }
{
  echo "CELL_SSH_HOST=172.16.0.2"; echo "CELL_SSH_PORT=22"; echo "CELL_SSH_USER=root"; echo "CELL_SSH_KEY=$W/key"
} >> "$GITHUB_ENV"
