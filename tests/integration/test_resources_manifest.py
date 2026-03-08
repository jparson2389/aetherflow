from aetherflow.core.resources_client import ResourcesClient
from aetherflow.core.resources_manifest import ResourceEntry, ResourceManifest


def test_resources_client_rejects_unsigned_manifest() -> None:
    client = ResourcesClient()
    manifest = ResourceManifest(
        version="1.0",
        signature="invalid",
        resources=[
            ResourceEntry(
                resource_id="profile.default",
                kind="profile",
                version="1.0.0",
                sha256="abc",
                size=32,
                premium=False,
            )
        ],
    )

    assert client.validate_manifest(manifest) is False
