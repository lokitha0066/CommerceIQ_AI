import os
from urllib.parse import quote

import httpx


class StorageConfigurationError(Exception):
    pass


class StorageUploadError(Exception):
    pass


def use_supabase_storage() -> bool:
    backend = os.getenv("IMAGE_STORAGE_BACKEND", "local").strip().lower()
    if backend not in {"local", "supabase"}:
        raise StorageConfigurationError(
            "IMAGE_STORAGE_BACKEND must be 'local' or 'supabase'."
        )
    return backend == "supabase"


async def upload_image(
    object_path: str,
    content: bytes,
    content_type: str,
) -> str:
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "product-images").strip()
    if not supabase_url or not service_role_key or not bucket:
        raise StorageConfigurationError(
            "Supabase image storage requires SUPABASE_URL, "
            "SUPABASE_SERVICE_ROLE_KEY, and SUPABASE_STORAGE_BUCKET."
        )

    encoded_bucket = quote(bucket, safe="")
    encoded_path = quote(object_path, safe="/")
    endpoint = (
        f"{supabase_url}/storage/v1/object/"
        f"{encoded_bucket}/{encoded_path}"
    )
    headers = {
        "Authorization": f"Bearer {service_role_key}",
        "apikey": service_role_key,
        "Content-Type": content_type,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(endpoint, headers=headers, content=content)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise StorageUploadError(
            f"Supabase Storage rejected the image upload "
            f"(HTTP {exc.response.status_code}). Check that the bucket exists "
            "and the service-role key is valid."
        ) from exc
    except httpx.RequestError as exc:
        raise StorageUploadError(
            "Could not reach Supabase Storage."
        ) from exc

    return (
        f"{supabase_url}/storage/v1/object/public/"
        f"{encoded_bucket}/{encoded_path}"
    )
