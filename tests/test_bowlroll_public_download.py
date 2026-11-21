"""Test access restrictions and archive boundaries without external requests."""
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.bowlroll_public_download import main


class PublicCameraDownloadTests(unittest.TestCase):
    def page(self, control="permission", key="false"):
        return io.BytesIO((f'<div id="initialize" data-download_control="{control}" '
                           f'data-download_key="{key}" data-csrf_token="test" '
                           'data-user_name="author"></div>').encode())

    def test_restricted_download_stops_before_requesting_file(self):
        for control, key in (("login", "false"), ("expired", "false"), ("permission", "true")):
            with self.subTest(control=control, key=key), tempfile.TemporaryDirectory() as temporary:
                opener = Mock()
                opener.open.return_value = self.page(control, key)
                output = Path(temporary) / "new"
                with patch("sys.argv", ["download", "--file-id", "1", "--output-dir", str(output)]), patch("scripts.bowlroll_public_download.build_opener", return_value=opener):
                    with self.assertRaises(RuntimeError):
                        main()
                self.assertEqual(opener.open.call_count, 1)
                self.assertFalse(output.exists())

    def archive(self, name):
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as archive:
            archive.writestr(name, "test camera data")
        return data.getvalue()

    def run_download(self, output, member):
        opener = Mock()
        result = json.dumps({"status": "success", "url": "https://storage.example/鏡頭.zip"}).encode()
        opener.open.side_effect = [self.page(), io.BytesIO(result), io.BytesIO(self.archive(member))]
        with patch("sys.argv", ["download", "--file-id", "1", "--output-dir", str(output)]), patch("scripts.bowlroll_public_download.build_opener", return_value=opener), patch("builtins.print"):
            main()
        return opener

    def test_rejects_zip_escape_before_creating_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "new"
            with self.assertRaises(ValueError):
                self.run_download(output, "../../escaped.vmd")
            self.assertFalse(output.exists())
            self.assertFalse((Path(temporary) / "escaped.vmd").exists())

    def test_public_download_encodes_unicode_url_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "new"
            opener = self.run_download(output, "camera.vmd")
            url = opener.open.call_args_list[2].args[0].full_url
            self.assertIn("%", url)
            url.encode("ascii")
            self.assertTrue((output / "original-camera-package.zip").is_file())
            self.assertTrue((output / "extracted" / "camera.vmd").is_file())
            source = json.loads((output / "source.json").read_text(encoding="utf-8"))
            self.assertEqual(source["source_page"], "https://bowlroll.net/file/1")


if __name__ == "__main__":
    unittest.main()
