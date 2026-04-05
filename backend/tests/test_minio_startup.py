from minio.error import S3Error

from app.services import minio_client as minio_module


def test_init_minio_ignores_bucket_already_owned(monkeypatch):
    calls = {"bucket_exists": 0, "make_bucket": 0}

    def fake_bucket_exists(bucket_name):
        calls["bucket_exists"] += 1
        return False

    def fake_make_bucket(bucket_name):
        calls["make_bucket"] += 1
        raise S3Error(
            None,
            "BucketAlreadyOwnedByYou",
            "bucket already exists",
            f"/{bucket_name}",
            "req-id",
            "host-id",
            bucket_name=bucket_name,
        )

    monkeypatch.setattr(minio_module.minio_client, "bucket_exists", fake_bucket_exists)
    monkeypatch.setattr(minio_module.minio_client, "make_bucket", fake_make_bucket)

    minio_module.init_minio()

    assert calls == {"bucket_exists": 1, "make_bucket": 1}
