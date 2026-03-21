"""Tests for brother_printer.network_query module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from python_pkg.brother_printer.network_query import (
    _build_network_result,
    _check_snmp_connectivity,
    _snmpget_cmd,
    _snmpwalk_cmd,
    query_network_snmp,
    snmp_walk,
)


class TestSnmpwalkCmd:
    def test_builds_correct_command(self) -> None:
        cmd = _snmpwalk_cmd("/usr/bin/snmpwalk", "public", 5, "1.2.3.4", "1.3.6")
        assert cmd == [
            "/usr/bin/snmpwalk",
            "-v",
            "2c",
            "-c",
            "public",
            "-t",
            "5",
            "-OQvs",
            "1.2.3.4",
            "1.3.6",
        ]


class TestSnmpgetCmd:
    def test_builds_correct_command(self) -> None:
        cmd = _snmpget_cmd("/usr/bin/snmpget", "public", 5, "1.2.3.4", "1.3.6")
        assert cmd == [
            "/usr/bin/snmpget",
            "-v",
            "2c",
            "-c",
            "public",
            "-t",
            "5",
            "1.2.3.4",
            "1.3.6",
        ]


class TestSnmpWalk:
    @patch("python_pkg.brother_printer.network_query.shutil.which", return_value=None)
    def test_no_snmpwalk(self, _mock: MagicMock) -> None:
        assert snmp_walk("1.2.3.4", "1.3.6", "public", 5) == []

    @patch("python_pkg.brother_printer.network_query.subprocess.run")
    @patch(
        "python_pkg.brother_printer.network_query.shutil.which",
        return_value="/usr/bin/snmpwalk",
    )
    def test_success(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout='  "Brother HL-1110"  \n  "SN123"  \n',
        )
        result = snmp_walk("1.2.3.4", "1.3.6", "public", 5)
        assert result == ["Brother HL-1110", "SN123"]

    @patch("python_pkg.brother_printer.network_query.subprocess.run")
    @patch(
        "python_pkg.brother_printer.network_query.shutil.which",
        return_value="/usr/bin/snmpwalk",
    )
    def test_empty_lines_stripped(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="   \n  value  \n   \n")
        result = snmp_walk("1.2.3.4", "1.3.6", "public", 5)
        assert result == ["value"]

    @patch("python_pkg.brother_printer.network_query.subprocess.run")
    @patch(
        "python_pkg.brother_printer.network_query.shutil.which",
        return_value="/usr/bin/snmpwalk",
    )
    def test_timeout(self, _w: MagicMock, mock_run: MagicMock) -> None:
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("snmpwalk", 15)
        assert snmp_walk("1.2.3.4", "1.3.6", "public", 5) == []

    @patch("python_pkg.brother_printer.network_query.subprocess.run")
    @patch(
        "python_pkg.brother_printer.network_query.shutil.which",
        return_value="/usr/bin/snmpwalk",
    )
    def test_oserror(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = OSError("fail")
        assert snmp_walk("1.2.3.4", "1.3.6", "public", 5) == []


class TestCheckSnmpConnectivity:
    @patch(
        "python_pkg.brother_printer.network_query.shutil.which",
        return_value=None,
    )
    def test_no_snmpget(self, _mock: MagicMock) -> None:
        result = _check_snmp_connectivity("1.2.3.4", "public", 5)
        assert result is not None
        assert "snmpget not found" in result

    @patch("python_pkg.brother_printer.network_query.subprocess.run")
    @patch(
        "python_pkg.brother_printer.network_query.shutil.which",
        return_value="/usr/bin/snmpget",
    )
    def test_success(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock()
        assert _check_snmp_connectivity("1.2.3.4", "public", 5) is None

    @patch("python_pkg.brother_printer.network_query.subprocess.run")
    @patch(
        "python_pkg.brother_printer.network_query.shutil.which",
        return_value="/usr/bin/snmpget",
    )
    def test_timeout(self, _w: MagicMock, mock_run: MagicMock) -> None:
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("snmpget", 10)
        result = _check_snmp_connectivity("1.2.3.4", "public", 5)
        assert result is not None
        assert "Cannot reach" in result

    @patch("python_pkg.brother_printer.network_query.subprocess.run")
    @patch(
        "python_pkg.brother_printer.network_query.shutil.which",
        return_value="/usr/bin/snmpget",
    )
    def test_called_process_error(self, _w: MagicMock, mock_run: MagicMock) -> None:
        import subprocess

        mock_run.side_effect = subprocess.CalledProcessError(1, "snmpget")
        result = _check_snmp_connectivity("1.2.3.4", "public", 5)
        assert result is not None

    @patch("python_pkg.brother_printer.network_query.subprocess.run")
    @patch(
        "python_pkg.brother_printer.network_query.shutil.which",
        return_value="/usr/bin/snmpget",
    )
    def test_oserror(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = OSError("fail")
        result = _check_snmp_connectivity("1.2.3.4", "public", 5)
        assert result is not None


class TestBuildNetworkResult:
    @patch("python_pkg.brother_printer.network_query.snmp_walk")
    def test_builds_result(self, mock_walk: MagicMock) -> None:
        mock_walk.return_value = ["Test Value"]
        result = _build_network_result("1.2.3.4", "public", 5)
        assert result.ip == "1.2.3.4"
        assert result.product == "Test Value"

    @patch("python_pkg.brother_printer.network_query.snmp_walk")
    def test_empty_values(self, mock_walk: MagicMock) -> None:
        mock_walk.return_value = []
        result = _build_network_result("1.2.3.4", "public", 5)
        assert result.product == "Unknown"
        assert result.serial == ""


class TestQueryNetworkSnmp:
    @patch("python_pkg.brother_printer.network_query._build_network_result")
    @patch(
        "python_pkg.brother_printer.network_query._check_snmp_connectivity",
        return_value=None,
    )
    def test_success(self, _c: MagicMock, mock_build: MagicMock) -> None:
        from python_pkg.brother_printer.data_classes import NetworkResult

        mock_build.return_value = NetworkResult(ip="1.2.3.4")
        result = query_network_snmp("1.2.3.4")
        assert result.ip == "1.2.3.4"
        assert result.error == ""

    @patch(
        "python_pkg.brother_printer.network_query._check_snmp_connectivity",
        return_value="Error msg",
    )
    def test_connectivity_error(self, _c: MagicMock) -> None:
        result = query_network_snmp("1.2.3.4")
        assert result.error == "Error msg"
