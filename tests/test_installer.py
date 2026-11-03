"""Exercise release verification without the network or any privileged command."""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class Installer(unittest.TestCase):
    package_format = "deb"

    def setUp(self):
        required = "dpkg-deb" if self.package_format == "deb" else "rpmbuild"
        if not shutil.which(required):
            self.skipTest(f"{required} is not installed")
        self.temporary = tempfile.TemporaryDirectory(prefix="quotabar-installer-test-")
        self.addCleanup(self.temporary.cleanup)
        self.base = pathlib.Path(self.temporary.name)
        self.assets = self.base / "assets"
        self.assets.mkdir()
        self.bin = self.base / "bin"
        self.bin.mkdir()
        if self.package_format == "deb":
            stage = self.base / "package"
            (stage / "DEBIAN").mkdir(parents=True)
            self.control = stage / "DEBIAN/control"
            self.control.write_text("Package: quotabar\nVersion: 0.2.1-1\nArchitecture: all\n"
                                    "Maintainer: Test <test@example.invalid>\nDescription: Installer fixture\n")
            self.package = self.assets / "quotabar_0.2.1-1_all.deb"
        else:
            self.control = self.base / "fixture.spec"
            self.control.write_text("""Name: quotabar
Version: 0.2.1
Release: 1
Summary: Installer fixture
License: MIT
BuildArch: noarch
%description
Synthetic package for installer verification.
%install
mkdir -p %{buildroot}/usr/share/quotabar-fixture
printf test > %{buildroot}/usr/share/quotabar-fixture/test.txt
%files
/usr/share/quotabar-fixture/test.txt
""")
            self.package = self.assets / "quotabar-0.2.1-1.noarch.rpm"
        self.rebuild()
        self.write_manifest()
        (self.assets / "latest").write_text(json.dumps({"tag_name": "v0.2.1"}))
        # Only curl is mocked. Checksums and native package queries are real.
        (self.bin / "curl").write_text("""#!/usr/bin/python3
import os,pathlib,shutil,sys
args=sys.argv[1:]; output=args[args.index('--output')+1]; url=args[-1]
with open(os.environ['INSTALLER_CALLS'],'a') as log: log.write(url+'\\n')
shutil.copyfile(pathlib.Path(os.environ['INSTALLER_ASSETS'])/url.rsplit('/',1)[-1],output)
""")
        (self.bin / "curl").chmod(0o755)
        (self.bin / "sudo").write_text('#!/bin/sh\nprintf "unexpected sudo" > "$INSTALLER_SUDO"\nexit 99\n')
        (self.bin / "sudo").chmod(0o755)
        self.output = self.base / "download"
        self.env = {**os.environ, "PATH": f"{self.bin}:/usr/bin:/bin",
                    "INSTALLER_ASSETS": str(self.assets), "INSTALLER_CALLS": str(self.base / "calls"),
                    "INSTALLER_SUDO": str(self.base / "sudo-called")}

    def write_manifest(self):
        digest = hashlib.sha256(self.package.read_bytes()).hexdigest()
        (self.assets / "SHA256SUMS").write_text(f"{digest}  {self.package.name}\n")

    def rebuild(self):
        if self.package_format == "deb":
            argv = ["dpkg-deb", "--build", str(self.control.parent.parent), str(self.package)]
        else:
            argv = ["rpmbuild", "-bb", "--define", f"_topdir {self.base / 'rpmbuild'}", str(self.control)]
        subprocess.run(argv, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if self.package_format == "rpm":
            built = max((self.base / "rpmbuild/RPMS").rglob("*.rpm"), key=lambda p: p.stat().st_mtime_ns)
            shutil.copyfile(built, self.package)

    def run_installer(self, *args, download=True):
        argv = ["bash", str(ROOT / "install.sh"), "--format", self.package_format, *args]
        if download:
            argv += ["--download-only", str(self.output)]
        result = subprocess.run(argv, env=self.env, text=True, capture_output=True, timeout=10)
        self.assertFalse((self.base / "sudo-called").exists(), "Verification must not invoke sudo")
        return result

    def test_latest_release_download_and_real_checksum(self):
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.output / self.package.name).read_bytes(), self.package.read_bytes())
        self.assertIn('/releases/download/v0.2.1/', (self.base / 'calls').read_text())

    def test_pinned_version_does_not_query_latest(self):
        result = self.run_installer('--version', '0.2.1')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('/releases/latest', (self.base / 'calls').read_text())

    def test_tampered_package_is_rejected(self):
        self.package.write_bytes(self.package.read_bytes() + b'tampered')
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Checksum mismatch', result.stderr)
        self.assertFalse(self.output.exists())

    def test_duplicate_checksum_is_rejected(self):
        path = self.assets / 'SHA256SUMS'
        path.write_text(path.read_text() * 2)
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('duplicate', result.stderr)

    def test_wrong_package_with_matching_checksum_is_rejected(self):
        key = 'Package' if self.package_format == 'deb' else 'Name'
        self.control.write_text(self.control.read_text().replace(f'{key}: quotabar', f'{key}: other'))
        self.rebuild()
        self.write_manifest()
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('package name', result.stderr)

    def test_wrong_version_with_matching_checksum_is_rejected(self):
        self.control.write_text(self.control.read_text().replace('Version: 0.2.1', 'Version: 0.2.2'))
        self.rebuild()
        self.write_manifest()
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('package version', result.stderr)

    def test_invalid_format_is_rejected_before_network(self):
        result = self.run_installer('--format', 'unknown')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.base / 'calls').exists())

    def test_os_auto_detection_uses_native_format(self):
        from platform import freedesktop_os_release
        native = 'rpm' if freedesktop_os_release().get('ID') == 'fedora' else 'deb'
        if native != self.package_format:
            self.skipTest('Other distribution format')
        result = self.run_installer('--format', 'auto')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.output / self.package.name).exists())

    def test_invalid_release_metadata_is_rejected(self):
        (self.assets / 'latest').write_text(json.dumps({'tag_name': '../../untrusted'}))
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('invalid GitHub release', result.stderr)

    def test_invalid_version_is_rejected_before_network(self):
        result = self.run_installer('--version', '../other')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.base / 'calls').exists())

    @unittest.skipIf(os.geteuid() == 0, 'Desktop installer intentionally rejects root')
    def test_unsupported_gnome_is_rejected_before_network(self):
        manager = 'dnf' if self.package_format == 'rpm' else 'apt-get'
        (self.bin / manager).write_text('#!/bin/sh\nexit 99\n')
        (self.bin / manager).chmod(0o755)
        (self.bin / 'gnome-shell').write_text('#!/bin/sh\nprintf "GNOME Shell 47.0\\n"\n')
        (self.bin / 'gnome-shell').chmod(0o755)
        result = self.run_installer(download=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('GNOME 48-51 is required', result.stderr)
        self.assertFalse((self.base / 'calls').exists())


class RpmInstaller(Installer):
    package_format = "rpm"


if __name__ == '__main__':
    unittest.main()
