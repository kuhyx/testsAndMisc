# LAN blocker: what to do when the internet breaks

This PC (`192.168.1.43`, wired `enp6s0`) does three jobs for the home network
(Orange Światłowód Funbox at `192.168.1.1`, both Ethernet and WiFi):

| Job         | What it means                                                                                           | Script                         |
| ----------- | ------------------------------------------------------------------------------------------------------- | ------------------------------ |
| DHCP server | hands every device its IP address                                                                       | `setup_dns_blocker.sh dhcp`    |
| DNS blocker | answers DNS, blocked names get `0.0.0.0`                                                                | `setup_dns_blocker.sh setup`   |
| Gateway     | other devices' internet traffic goes through this PC, DNS is forced to the blocker, DoH/DoT are dropped | `setup_dns_blocker.sh gateway` |

**The PC itself never depends on any of this.** Its own address is static
(`192.168.1.43/24`, gateway `192.168.1.1`, set in NetworkManager), its own
traffic goes straight to the Funbox, and the firewall `output` chain accepts
everything. Only the OTHER devices go through the PC.

All commands below are run on the PC and use full paths, so they can be copied as-is.

---

## 1. Other devices have no internet, the PC is fine

Most likely the gateway layer. Turn it off (one command, safe, keeps DHCP and
DNS blocking):

```bash
sudo ~/src/testsAndMisc/linux_configuration/features/setup_dns_blocker.sh gateway-off
```

Then on each device: WiFi off and on again (it picks up the new lease with the
Funbox as gateway). Phone: pull down the quick settings, WiFi off, WiFi on.

Still broken? Turn off DHCP serving too, and give DHCP back to the Funbox
(section 3, steps 2 to 4):

```bash
sudo ~/src/testsAndMisc/linux_configuration/features/setup_dns_blocker.sh dhcp-off
```

## 2. The PC itself has no internet

Check in this order. Stop at the first one that fixes it.

1. Cable / Funbox: is the Funbox on, is the cable in `enp6s0`? `ping -c3 192.168.1.1`
2. Route: `ip route get 1.1.1.1` must say `via 192.168.1.1 dev enp6s0`.
   If not: `sudo nmcli con up 'Wired connection 1'`
3. Raw internet: `ping -c3 1.1.1.1`. Works but names fail? It is DNS, go to 4.
4. DNS: `getent hosts example.com`. If that fails while step 3 works:
   `sudo tailscale down` (the PC resolves through Tailscale's 100.100.100.100),
   test again, then `sudo tailscale up` once fixed.
5. Firewall (last resort, removes ALL filtering until next apply):
   `sudo nft delete table ip lan_gateway; sudo nft delete table inet filter`
   Restore later with `sudo /home/kuhy/src/testsAndMisc/linux_configuration/features/setup_wireguard_ssh.sh allow-dns`.

## 3. The PC is off, dead or being reinstalled

Every device except nextcloud-pi and the P110 plug loses internet AT ONCE
(the PC is their gateway), and new devices get no address. Hand DHCP back
to the Funbox:

1. On a phone or laptop, set a **static** IP on the WiFi so you can reach the
   Funbox without DHCP: IP `192.168.1.200`, mask `255.255.255.0`
   (prefix 24), gateway `192.168.1.1`, DNS `1.1.1.1`.
2. Open `http://192.168.1.1`, log in (password on the sticker under the Funbox).
3. Find the LAN / DHCP settings and tick **"włącz serwer DHCP"**, then **Zapisz**.
4. Switch the phone/laptop back to DHCP (automatic). Every device now gets
   the Funbox as DHCP, DNS and gateway: internet works, nothing is blocked.
5. Toggle WiFi on EVERY other device (or unplug/replug its cable). Until they
   do, they keep the dead PC as gateway for up to ~2 hours.

When the PC is back:

```bash
sudo ~/src/testsAndMisc/linux_configuration/features/setup_dns_blocker.sh status
```

Then untick "włącz serwer DHCP" again and run
`sudo /home/kuhy/src/testsAndMisc/linux_configuration/features/setup_dns_blocker.sh dhcp`, then
`sudo /home/kuhy/src/testsAndMisc/linux_configuration/features/setup_dns_blocker.sh gateway`.

## 4. The Funbox itself

No Funbox setting was changed on 2026-10-25 (its LAN IPv6 router
advertisements are already off: it does not answer router solicitations).
Never factory-reset it: that wipes the WireGuard 51820 and 80/443 port
forwards and re-enables its DHCP next to the PC's.

## 5. Health check (all on the PC)

```bash
sudo ~/src/testsAndMisc/linux_configuration/features/setup_dns_blocker.sh status
sudo ~/src/testsAndMisc/linux_configuration/features/setup_wireguard_ssh.sh verify
dig +short @192.168.1.43 www.ubereats.com    # must print 0.0.0.0
```

## 6. Check that a device really goes through the blocker (Linux laptop)

1. Turn WiFi off and on (or replug the cable).
2. `ip route | grep default` must say `via 192.168.1.43`.
3. `resolvectl status`: no VPN/tun link, no IPv6 DNS server listed.
4. `resolvectl flush-caches`; in Chrome open `chrome://net-internals/#dns`
   and click "Clear host cache".
5. `nslookup www.ubereats.com 8.8.8.8` must print `0.0.0.0` (proves even a
   hand-picked DNS server is redirected to the blocker).
6. Open ubereats.com in Chrome and Firefox: it must fail.

If a browser loads NOTHING at all, it is set to strict "secure DNS" (Chrome:
Settings, Privacy, Use secure DNS; Firefox: Settings, Privacy, DNS over
HTTPS). Turn that off; the DoH block is doing its job. If Uber Eats still
loads, see which hostname served it (DevTools, Network) and check it with
`dig @192.168.1.43 <that host>`: the blocklist matches exact names, so a
missing one goes into hosts-blocker's custom list.

### Work laptop with Cloudflare WARP

Gateway mode drops the WARP tunnel (WireGuard and MASQUE ingress, UDP to the
consumer-WARP ranges), because WARP carries all traffic past the DNS block.
WARP fails CLOSED: blocked, even stuck at "Connecting", it leaves the laptop
with no internet. So the laptop runs `warp-home` (user timer, every 30 s): at
home with no window open it turns WARP off, and plain internet with the
blocklist comes back. On any other network (office) it never touches WARP.

- Mon/Fri 09:00-15:30 at home: `warp-home on` asks the PC, then connects.
  The PC opens WARP for the LAN until 15:30 sharp, then closes by itself.
  Outside that window the PC refuses. `warp-home off` / `warp-home status`.
- Window closed early (the PC firewall was re-applied): `warp-home on` again.
- PC side by hand: `sudo warp-window open|close|status`.
- Emergency, WARP needed outside the window:
  `sudo ~/src/testsAndMisc/linux_configuration/features/setup_dns_blocker.sh gateway-off`
  lifts the whole gateway (all gateway blocking goes with it); `gateway` restores it.
- The block is IPv4-only: it holds while the Funbox hands out no IPv6 route
  (`ip -6 route` on the laptop shows no default).

## 7. Change log

- 2026-10-25: refresh timer fixed (repos moved to `~/src`, it had failed
  nightly since 2026-09-11); dnsmasq upstream moved from the Funbox to
  1.1.1.1 + 9.9.9.9; AAAA answers stripped (blocked names used to leak their
  real IPv6 address); Firefox DoH canary + DoH hostnames blocked; DHCP lease
  12h -> 2h; gateway mode added (nextcloud-pi and the P110 plug exempt).
- 2026-10-25: WARP tunnel dropped at the gateway (work laptop bypassed the
  DNS block through it); Mon/Fri 09:00-15:30 window via `warp-home on`.
