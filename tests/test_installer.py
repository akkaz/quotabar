"""Exercise release verification without the network or any privileged command."""
import hashlib
import json
import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class Installer(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="quotabar-installer-test-")
        self.addCleanup(self.temporary.cleanup)
        self.base = pathlib.Path(self.temporary.name)
        self.assets = self.base / "assets"
        self.assets.mkdir()
        self.bin = self.base / "bin"
        self.bin.mkdir()
        stage = self.base / "package"
        (stage / "DEBIAN").mkdir(parents=True)
        self.control = stage / "DEBIAN/control"
        self.control.write_text("Package: quotabar\nVersion: 0.2.1-1\nArchitecture: all\n"
                                "Maintainer: Test <test@example.invalid>\nDescription: Installer fixture\n")
        self.package = self.assets / "quotabar_0.2.1-1_all.deb"
        subprocess.run(["dpkg-deb", "--build", str(stage), str(self.package)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.write_manifest()
        (self.assets / "latest").write_text(json.dumps({"tag_name": "v0.2.1"}))
        # Only curl is mocked. Verification uses real sha256sum and dpkg-deb.
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

    def run_installer(self, *args, download=True):
        argv = ["bash", str(ROOT / "install.sh"), *args]
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
        self.control.write_text(self.control.read_text().replace('Package: quotabar', 'Package: other'))
        subprocess.run(['dpkg-deb', '--build', str(self.control.parent.parent), str(self.package)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.write_manifest()
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Unexpected Debian package name', result.stderr)

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
        (self.bin / 'gnome-shell').write_text('#!/bin/sh\nprintf "GNOME Shell 47.0\\n"\n')
        (self.bin / 'gnome-shell').chmod(0o755)
        result = self.run_installer(download=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('GNOME 48 is required', result.stderr)
        self.assertFalse((self.base / 'calls').exists())


if __name__ == '__main__':
    unittest.main()
