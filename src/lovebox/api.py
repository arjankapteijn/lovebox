"""Lovebox GraphQL API — inloggen, device-id ophalen en een afbeelding sturen.

Reverse-engineering van de API: zie de bronnen in de README.
"""

from __future__ import annotations

import base64

import requests

API_BASE = "https://app-api.loveboxlove.com"
GQL_URL = f"{API_BASE}/v1/graphql"
LOGIN_URL = f"{API_BASE}/v1/auth/loginWithPassword"


def login(email: str, password: str, *, timeout: float = 10) -> str:
    r = requests.post(
        LOGIN_URL,
        headers={"content-type": "application/json"},
        json={"email": email, "password": password},
        timeout=timeout,
    )
    r.raise_for_status()
    data = r.json()
    if "token" not in data:
        raise RuntimeError(f"Login mislukt: {data}")
    return data["token"]


def fetch_me(token: str, *, timeout: float = 10) -> tuple[str, list[dict]]:
    """Geef (device_id, boxes) terug — device_id is nodig voor sendPixNote."""
    query = "query me { me { _id device { _id } boxes { _id nickname hasColor } } }"
    r = requests.post(
        GQL_URL,
        headers={"Authorization": f"Bearer {token}", "content-type": "application/json"},
        json={"operationName": "me", "variables": {}, "query": query},
        timeout=timeout,
    )
    r.raise_for_status()
    body = r.json()
    if body.get("errors"):
        raise RuntimeError(f"me-query fout: {body['errors']}")
    me = body["data"]["me"]
    return me["device"]["_id"], me["boxes"]


def send_image(
    token: str, box_id: str, device_id: str, png_bytes: bytes, *, timeout: float = 20
) -> dict:
    b64 = "data:image/png;base64," + base64.b64encode(png_bytes).decode()
    mutation = """
    mutation sendPixNote(
      $base64: String
      $recipient: String
      $options: JSON
      $contentType: [String]
    ) {
      sendPixNote(
        base64: $base64
        recipient: $recipient
        options: $options
        contentType: $contentType
      ) {
        _id
        type
        recipient
        status { label __typename }
        __typename
      }
    }
    """
    variables = {
        "base64": b64,
        "recipient": box_id,
        "contentType": ["Image"],
        "options": {"framesBase64": None, "deviceId": device_id},
    }
    r = requests.post(
        GQL_URL,
        headers={"Authorization": f"Bearer {token}", "content-type": "application/json"},
        json={"operationName": "sendPixNote", "query": mutation, "variables": variables},
        timeout=timeout,
    )
    r.raise_for_status()
    body = r.json()
    if body.get("errors"):
        raise RuntimeError(f"sendPixNote fout: {body['errors']}")
    return body["data"]["sendPixNote"]
