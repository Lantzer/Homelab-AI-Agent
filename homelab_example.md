# Homelab

## Overview

A self-hosted homelab built around a small cluster of repurposed enterprise hardware,
running a mix of virtualization, containerized services, and home automation. Accessible
remotely via Tailscale and managed through a centralized dashboard.

---

## Hardware

| Device | Details |
|---|---|
| **Dell OptiPlex 7060** | Primary server — Intel i7-8700, 32 GB RAM, 1 TB NVMe SSD |
| **Raspberry Pi 4 (8GB)** | Secondary node — lightweight services & DNS |
| **Netgear Nighthawk RAX50** | Main router — Wi-Fi 6, handles DHCP and routing |
| **TP-Link TL-SG108PE** | 8-port PoE switch — powers the Pi and IP cameras |
| **Synology DS223j** | 2-bay NAS — 8 TB total, used for backups and media |
| **CyberPower CP1500** | UPS — protects server, NAS, and switch from outages |

### Physical Network Topology

```
ISP Modem
    │
Nighthawk Router (192.168.1.1)
    │
TP-Link PoE Switch
    ├── Dell OptiPlex 7060  (192.168.1.20)
    ├── Raspberry Pi 4      (192.168.1.21)
    ├── Synology NAS        (192.168.1.30)
    └── IP Camera x2        (192.168.1.40-41)
```

---

## Dell OptiPlex 7060 — Primary Server

**OS:** Proxmox VE 8  
**Storage:** 1 TB NVMe (OS + VMs) + 2 TB HDD (bulk storage)  
**Purpose:** Runs the majority of self-hosted services via VMs and LXC containers

### Virtual Machines

| VM | OS | Purpose |
|---|---|---|
| **docker-host** | Debian 12 | Runs all Docker containers |
| **pihole-vm** | Ubuntu 22.04 | Dedicated Pi-hole DNS server |
| **dev-sandbox** | Arch Linux | Personal dev environment, SSH in |

### Docker Containers (on docker-host VM)

| Container | Purpose | Access |
|---|---|---|
| **Traefik** | Reverse proxy + SSL termination | Internal only |
| **Portainer** | Docker management UI | `https://portainer.lab.local` |
| **Nextcloud** | Self-hosted cloud storage | `https://cloud.lab.local` |
| **Jellyfin** | Media server — movies & TV | `https://media.lab.local` |
| **Vaultwarden** | Self-hosted Bitwarden password manager | `https://vault.lab.local` |
| **Gitea** | Self-hosted Git server | `https://git.lab.local` |
| **Uptime Kuma** | Service health monitoring | `https://status.lab.local` |
| **HomePage** | Central dashboard | `https://home.lab.local` |

---

## Raspberry Pi 4 — Secondary Node

**OS:** Raspberry Pi OS Lite (64-bit)  
**Purpose:** Lightweight always-on tasks that don't need the OptiPlex running

### Services

| Service | Purpose |
|---|---|
| **Pi-hole** | Network-wide DNS ad blocking (backup instance) |
| **Mosquitto** | MQTT broker for Home Assistant sensors |
| **zigbee2mqtt** | Zigbee coordinator — bridges Zigbee devices to MQTT |
| **Unbound** | Recursive DNS resolver upstream of Pi-hole |

---

## Networking

### Pi-hole

Both Pi-hole instances run in an active/passive setup. The OptiPlex VM is primary;
the Pi 4 takes over if it goes down. The router hands out both IPs as DNS servers.

- **Primary DNS:** `192.168.1.20` (OptiPlex VM)
- **Secondary DNS:** `192.168.1.21` (Pi 4)
- **Upstream resolver:** Unbound (recursive, no third-party DNS)
- **Admin panel:** `http://192.168.1.20/admin`

### VLANs

| VLAN | ID | Subnet | Purpose |
|---|---|---|---|
| **Main** | 1 | `192.168.1.0/24` | Trusted devices, servers |
| **IoT** | 20 | `192.168.20.0/24` | Smart home devices, cameras |
| **Guest** | 30 | `192.168.30.0/24` | Guest Wi-Fi — internet only |

IoT devices are isolated from the main network; Home Assistant is the only host
allowed to cross from Main → IoT.

### Local DNS / Hostnames

All `*.lab.local` hostnames resolve via Pi-hole's Local DNS to `192.168.1.20`.
Traefik routes traffic to the correct container based on hostname.

---

## Remote Access

### Tailscale

Tailscale provides secure remote access to the entire homelab without port forwarding.
The OptiPlex acts as a subnet router, advertising `192.168.1.0/24` to the Tailnet so
all LAN devices are reachable remotely.

```bash
# Advertise subnet via Tailscale
sudo tailscale up --advertise-routes=192.168.1.0/24

# Check connected devices
tailscale status
```

### SSH Access

```bash
# Local
ssh user@192.168.1.20

# Remote (via Tailscale)
ssh user@100.x.x.x
```

---

## Storage & Backups

### Synology NAS

The DS223j runs two 4 TB drives in SHR (Synology Hybrid RAID) for single-drive
redundancy. It serves three purposes:

- **Media storage** — Jellyfin library source via NFS mount
- **Nextcloud external storage** — user files backed up here
- **Docker volume backups** — nightly rsync from the OptiPlex

### Backup Strategy

| What | How | Frequency | Destination |
|---|---|---|---|
| Docker volumes | `rsync` script | Nightly | Synology NAS |
| Nextcloud data | Built-in backup app | Daily | NAS + Backblaze B2 |
| Proxmox VMs | Proxmox Backup Server | Weekly | NAS |
| NAS itself | Hyper Backup | Weekly | Backblaze B2 |

---

## Home Automation

Home Assistant runs in Docker on the OptiPlex and manages:

- **Zigbee devices** — lights, motion sensors, door sensors (via zigbee2mqtt on the Pi)
- **IP cameras** — two PoE cameras streamed via Frigate (NVR container)
- **Automations** — lights on motion, morning routines, presence detection

**Config directory:** `/opt/docker/homeassistant/`  
**Web UI:** `https://home-assistant.lab.local`

---

## Maintenance

### Updating Containers

```bash
cd /opt/docker
docker compose pull && docker compose up -d
# prune old images
docker image prune -f
```

### Useful Commands

```bash
# Check all running containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check Proxmox VM status
qm list

# Disk usage
df -h

# Check UPS status (via NUT)
upsc cyberpower
```

---

## Planned / Future

- [ ] Set up Authentik for SSO across all services
- [ ] Migrate from local SSL certs to Let's Encrypt via Traefik + Cloudflare DNS challenge
- [ ] Add a third Pi-hole instance for true HA DNS
- [ ] Explore running a local LLM with Ollama + Open WebUI
- [ ] Set up Grafana + Prometheus for system metrics dashboards
- [ ] Add a 10 GbE link between the OptiPlex and NAS
