#!/bin/bash
# VM and network sysctl tuning.
#
# Sourced by optimize_arch_desktop.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

# ===================================================================
# 3. Memory & swap tuning via sysctl
# ===================================================================
tweak_vm_sysctl() {
	# SYSCTL_DROPIN_DIR defaults to the real directory and is overridden only
	# by the test harness, which runs un-jailed in ci_mirror.sh and in CI.
	local dropin="${SYSCTL_DROPIN_DIR:-/etc/sysctl.d}/90-desktop-performance.conf"

	# Desktop workloads: low swappiness, aggressive VFS caching, tuned dirty ratios
	local -A params=(
		["vm.swappiness"]="10"
		["vm.vfs_cache_pressure"]="50"
		["vm.dirty_ratio"]="15"
		["vm.dirty_background_ratio"]="5"
		["vm.dirty_writeback_centisecs"]="1500"
		["vm.page-cluster"]="0"
	)

	local needs_update=false
	local key
	for key in "${!params[@]}"; do
		local current
		current=$(sysctl -n "$key" 2>/dev/null || true)
		if [[ $current != "${params[$key]}" ]]; then
			needs_update=true
			break
		fi
	done

	if [[ $needs_update == "false" && -f $dropin ]]; then
		log_ok "VM sysctl parameters already tuned — skipping."
		return 0
	fi

	cat >"$dropin" <<'VMEOF'
# Desktop performance tuning — managed by optimize_arch_desktop.sh
#
# vm.swappiness=10          — prefer keeping data in RAM over swapping
# vm.vfs_cache_pressure=50  — favor keeping inode/dentry caches (speeds up file operations)
# vm.dirty_ratio=15         — allow up to 15% RAM dirty before synchronous writeback
# vm.dirty_background_ratio=5  — start async writeback at 5% dirty
# vm.dirty_writeback_centisecs=1500  — flush dirty pages every 15s (less I/O churn)
# vm.page-cluster=0         — read one page at a time from swap (reduces latency on SSD)
vm.swappiness = 10
vm.vfs_cache_pressure = 50
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
vm.dirty_writeback_centisecs = 1500
vm.page-cluster = 0
VMEOF

	sysctl --system >/dev/null 2>&1
	return 0
}

# ===================================================================
# 4. Network: TCP BBR + fastopen + buffer tuning
# ===================================================================
tweak_network_sysctl() {
	local dropin="${SYSCTL_DROPIN_DIR:-/etc/sysctl.d}/91-desktop-network.conf"

	# Check if BBR module is available
	if ! modprobe tcp_bbr 2>/dev/null; then
		log_warn "tcp_bbr kernel module unavailable — skipping network tuning."
		return 0
	fi

	local -A params=(
		["net.core.default_qdisc"]="fq"
		["net.ipv4.tcp_congestion_control"]="bbr"
		["net.ipv4.tcp_fastopen"]="3"
		["net.core.rmem_max"]="16777216"
		["net.core.wmem_max"]="16777216"
		["net.ipv4.tcp_rmem"]="4096 1048576 16777216"
		["net.ipv4.tcp_wmem"]="4096 1048576 16777216"
		["net.ipv4.tcp_mtu_probing"]="1"
	)

	local needs_update=false
	local key
	for key in "${!params[@]}"; do
		local current
		current=$(sysctl -n "$key" 2>/dev/null || true)
		# Normalize whitespace for comparison (kernel uses tabs)
		current=$(echo "$current" | xargs)
		local expected
		expected=$(echo "${params[$key]}" | xargs)
		if [[ $current != "$expected" ]]; then
			needs_update=true
			break
		fi
	done

	if [[ $needs_update == "false" && -f $dropin ]]; then
		log_ok "Network sysctl parameters already tuned — skipping."
		return 0
	fi

	cat >"$dropin" <<'NETEOF'
# Network performance tuning — managed by optimize_arch_desktop.sh
#
# BBR congestion control — better throughput and lower latency than cubic
# TCP fastopen — saves one RTT on repeated connections (both client and server)
# Larger buffers — helps on high-bandwidth or high-latency links
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
net.ipv4.tcp_fastopen = 3
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 1048576 16777216
net.ipv4.tcp_wmem = 4096 1048576 16777216
net.ipv4.tcp_mtu_probing = 1
NETEOF

	sysctl --system >/dev/null 2>&1
	return 0
}
