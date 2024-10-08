import yaml
import requests
import click
import re
import logging
from oar.core.configstore import ConfigStore
from oar.cli.cmd_create_test_report import create_test_report

logger = logging.getLogger(__name__)


class ReleaseDetector:

    def __init__(self, minor_release):
        """
        Comopare the latest z-stream version from file generated by ART and the latest stable version
        from release stream, if they're different, it means new z-stream release resources are
        prepared, we can kick off QE release flow
        """
        self._minor_release = minor_release

        # TODO: create statebox object

    def get_latest_zstream_version(self):
        """
        Get the latest z-stream version from file generated by ART
        """
        url = f"https://raw.githubusercontent.com/openshift/release-tests/z-stream/_releases/{self._minor_release}/{self._minor_release}.z.yaml"
        resp = requests.get(url)
        if resp.ok:
            yamlobj = yaml.safe_load(resp.text)
            releases = list(yamlobj["releases"].keys())
            if len(releases):
                return releases[-1]
            else:
                return None
        else:
            return None

    def get_latest_stable_version(self):
        """
        Get the latest stable version from release stream
        """
        url = f"https://amd64.ocp.releases.ci.openshift.org/api/v1/releasestream/4-stable/latest?prefix={self._minor_release}"
        resp = requests.get(url)
        if resp.ok:
            return resp.json()["name"]
        else:
            return None

    def start(self):
        """
        Entrypoint of cli cmd
        """
        latest_zstream_version = self.get_latest_zstream_version()
        latest_stable_version = self.get_latest_stable_version()

        logger.info(f"latest z-stream version: {latest_zstream_version}")
        logger.info(f"latest stable version: {latest_stable_version}")

        if latest_zstream_version is None or latest_stable_version is None:
            logger.error("get latest versions failed")
            return

        if latest_zstream_version != latest_stable_version:
            logger.info(
                f"new z-stream release is detected: {latest_zstream_version}")
            # TODO: init statebox
            create_test_report.invoke(click.Context(
                command=create_test_report, obj={"cs": ConfigStore(latest_zstream_version)}))
            logger.info(f"test report is created for {latest_zstream_version}")
        else:
            logger.info("no new z-stream release found")


def validate_minor_release(ctx, param, value):
    pattern = re.compile(r"^4\.\d{1,2}$")
    if not pattern.match(value):
        raise click.BadParameter(f"Invalid OCP minor version {value}")
    return value


@click.command()
@click.option("-r", "--minor-release",
              help="Minor rlease of OCP e.g. 4.y",
              prompt="Please input the minor version of OCP",
              required=True,
              callback=validate_minor_release)
def start_release_detector(minor_release):
    ReleaseDetector(minor_release).start()
