"""Exercise Git preservation and the SSH/Docker delivery boundaries."""

import argparse
import importlib.util
import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "sync-presentation.py"
SPEC = importlib.util.spec_from_file_location("sync_presentation", SCRIPT)
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


class RepositoryDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.share = self.root / "share.git"
        self.source = self.root / "source"
        self.target = self.root / "target with spaces"
        sync.run(["git", "init", "--bare", str(self.share)])
        sync.run(["git", "init", "-b", "main", str(self.source)])
        self.configure(self.source)
        self.file = self.source / "app.py"
        self.file.write_text("initial\n")
        self.commit(self.source, "initial")
        sync.run(["git", "remote", "add", "share", str(self.share)], cwd=self.source)
        sync.run(["git", "push", "share", "main"], cwd=self.source)
        sync.run(
            [
                "git",
                "clone",
                "-b",
                "main",
                "-o",
                "share",
                str(self.share),
                str(self.target),
            ]
        )
        self.configure(self.target)
        self.args = argparse.Namespace()

    def configure(self, path):
        sync.run(["git", "config", "user.name", "Sync test"], cwd=path)
        sync.run(["git", "config", "user.email", "sync-test@example.invalid"], cwd=path)

    def commit(self, path, message):
        sync.run(["git", "add", "app.py"], cwd=path)
        sync.run(["git", "commit", "-m", message], cwd=path)

    def deliver(self):
        # Substitute only the network boundary; execute the real remote script.
        with patch.object(
            sync,
            "remote",
            side_effect=lambda args, script, **kw: sync.run(
                ["bash", "-seuo", "pipefail"], stdin=script
            ),
        ):
            return sync.sync_repo(
                self.args, self.source, str(self.target), "main", presentation=True
            )

    def test_committed_update_preserves_destination_untracked_files_and_local_edits(
        self,
    ):
        (self.target / "private-config").write_text("keep")
        self.file.write_text("updated\n")
        self.commit(self.source, "update")
        self.file.write_text("uncommitted local work\n")
        revision = self.deliver()
        self.assertEqual((self.target / "app.py").read_text(), "updated\n")
        self.assertEqual((self.target / "private-config").read_text(), "keep")
        self.assertEqual(self.file.read_text(), "uncommitted local work\n")
        self.assertEqual(
            sync.run(["git", "rev-parse", "HEAD"], cwd=self.target), revision
        )

    def test_dirty_destination_fails_without_overwriting_its_work(self):
        (self.target / "app.py").write_text("destination work\n")
        with self.assertRaises(subprocess.CalledProcessError):
            self.deliver()
        self.assertEqual((self.target / "app.py").read_text(), "destination work\n")

    def test_diverged_destination_fails_without_resetting_its_commit(self):
        (self.target / "app.py").write_text("destination commit\n")
        self.commit(self.target, "destination")
        before = sync.run(["git", "rev-parse", "HEAD"], cwd=self.target)
        self.file.write_text("source commit\n")
        self.commit(self.source, "source")
        with self.assertRaises(subprocess.CalledProcessError):
            self.deliver()
        self.assertEqual(
            sync.run(["git", "rev-parse", "HEAD"], cwd=self.target), before
        )


class ImageDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.args = argparse.Namespace(
            build=[],
            image=["protocolguard:main"],
            build_host="MyServer-Local",
            presentation_host="ServerISecLab-Presentation",
            analysis_tag="protocolguard:latest",
        )

    def test_matching_image_skips_transfer_and_verifies_backend_alias(self):
        with (
            patch.object(
                sync,
                "image_ids",
                side_effect=[
                    {"protocolguard:main": "sha256:current"},
                    {"protocolguard:main": "sha256:current"},
                    {
                        "protocolguard:main": "sha256:current",
                        "protocolguard:latest": "sha256:current",
                    },
                ],
            ),
            patch.object(sync, "remote") as remote,
        ):
            sync.sync_images(self.args)
        self.assertEqual(remote.call_count, 1)
        self.assertEqual(
            remote.call_args.args[1],
            "docker image tag protocolguard:main protocolguard:latest",
        )

    def test_changed_image_transfers_directly_and_rejects_destination_id_mismatch(self):
        with (
            patch.object(
                sync,
                "image_ids",
                side_effect=[
                    {"protocolguard:main": "sha256:new"},
                    {"protocolguard:main": "sha256:old"},
                    {
                        "protocolguard:main": "sha256:wrong",
                        "protocolguard:latest": "sha256:wrong",
                    },
                ],
            ),
            patch.object(sync, "remote") as remote,
        ):
            with self.assertRaisesRegex(ValueError, "Destination image ID mismatch"):
                sync.sync_images(self.args)
        transfer = remote.call_args_list[0]
        self.assertIn("docker image save protocolguard:main | ssh", transfer.args[1])
        self.assertIn(
            "ServerISecLab-Presentation 'docker image load'", transfer.args[1]
        )

    def test_missing_source_image_fails_before_delivery(self):
        with (
            patch.object(sync, "image_ids", return_value={"protocolguard:main": ""}),
            patch.object(sync, "remote") as remote,
        ):
            with self.assertRaisesRegex(ValueError, "Images missing"):
                sync.sync_images(self.args)
            remote.assert_not_called()

    def test_transfer_failure_propagates_before_alias_retagging(self):
        with (
            patch.object(
                sync,
                "image_ids",
                side_effect=[
                    {"protocolguard:main": "sha256:new"},
                    {"protocolguard:main": ""},
                ],
            ),
            patch.object(
                sync, "remote", side_effect=subprocess.CalledProcessError(1, "transfer")
            ) as remote,
        ):
            with self.assertRaises(subprocess.CalledProcessError):
                sync.sync_images(self.args)
            self.assertEqual(remote.call_count, 1)

    def test_ssh_runs_pipeline_with_pipefail_on_build_host(self):
        with patch.object(sync, "run", return_value="") as run:
            sync.remote(
                self.args, "docker image save example | ssh target 'docker image load'"
            )
        argv = run.call_args.args[0]
        self.assertEqual(argv[-2], "MyServer-Local")
        self.assertEqual(shlex.split(argv[-1]), ["bash", "-seuo", "pipefail"])
        self.assertIn("docker image save", run.call_args.kwargs["stdin"])


if __name__ == "__main__":
    unittest.main()
