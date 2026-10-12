import os
import unittest
from unittest.mock import patch

import httpx

from storage import (
    StorageConfigurationError,
    StorageUploadError,
    upload_image,
    use_supabase_storage,
)

AsyncClient = httpx.AsyncClient


class StorageTests(unittest.IsolatedAsyncioTestCase):
    def test_local_storage_is_the_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(use_supabase_storage())

    async def test_supabase_storage_requires_valid_configuration(self):
        with patch.dict(
            os.environ,
            {"IMAGE_STORAGE_BACKEND": "unknown"},
            clear=True,
        ):
            with self.assertRaises(StorageConfigurationError):
                use_supabase_storage()

        with patch.dict(
            os.environ,
            {"SUPABASE_URL": "https://example.supabase.co"},
            clear=True,
        ):
            with self.assertRaises(StorageConfigurationError):
                await upload_image("products/user/image.webp", b"image", "image/webp")

    async def test_upload_returns_public_object_url(self):
        requests = []

        def handle_request(request):
            requests.append(request)
            return httpx.Response(200, json={"Key": "product-images/image.webp"})

        transport = httpx.MockTransport(handle_request)
        with (
            patch.dict(
                os.environ,
                {
                    "SUPABASE_URL": "https://example.supabase.co/",
                    "SUPABASE_SERVICE_ROLE_KEY": "secret",
                    "SUPABASE_STORAGE_BUCKET": "product-images",
                },
            ),
            patch(
                "storage.httpx.AsyncClient",
                side_effect=lambda **kwargs: AsyncClient(
                    transport=transport,
                    **kwargs,
                ),
            ),
        ):
            image_url = await upload_image(
                "products/user id/image.webp",
                b"image-bytes",
                "image/webp",
            )

        self.assertEqual(
            image_url,
            "https://example.supabase.co/storage/v1/object/public/"
            "product-images/products/user%20id/image.webp",
        )
        self.assertEqual(requests[0].method, "POST")
        self.assertEqual(requests[0].headers["authorization"], "Bearer secret")
        self.assertEqual(requests[0].content, b"image-bytes")

    async def test_storage_http_errors_are_reported(self):
        transport = httpx.MockTransport(
            lambda request: httpx.Response(403, text="forbidden")
        )
        with (
            patch.dict(
                os.environ,
                {
                    "SUPABASE_URL": "https://example.supabase.co",
                    "SUPABASE_SERVICE_ROLE_KEY": "secret",
                },
            ),
            patch(
                "storage.httpx.AsyncClient",
                side_effect=lambda **kwargs: AsyncClient(
                    transport=transport,
                    **kwargs,
                ),
            ),
        ):
            with self.assertRaisesRegex(StorageUploadError, "HTTP 403"):
                await upload_image(
                    "products/user/image.webp",
                    b"image-bytes",
                    "image/webp",
                )
