#!/usr/bin/env python3
"""Verbose smoke test for the DMS API.

Usage: python tests/smoke_test.py

Ensure the API is running at http://localhost:8000 (or set BASE_URL env var).
"""
import base64
import json
import os
import sys
import uuid
from pprint import pformat

import requests

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

session = requests.Session()


def dump_resp(resp):
    try:
        body = resp.json()
    except Exception:
        body = resp.text
    return {
        "status_code": resp.status_code,
        "headers": dict(resp.headers),
        "body": body,
    }


def print_step(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def pretty(obj):
    print(pformat(obj, width=120))


def register(email, password):
    url = f"{BASE_URL}/auth/register"
    resp = session.post(url, json={"email": email, "password": password})
    print_step(f"REGISTER -> {email}")
    pretty(dump_resp(resp))
    return resp


def login(email, password):
    url = f"{BASE_URL}/auth/login"
    resp = session.post(url, json={"email": email, "password": password})
    print_step("LOGIN")
    pretty(dump_resp(resp))
    token = None
    try:
        token = resp.json().get("access_token")
    except Exception:
        pass
    if token:
        session.headers.update({"Authorization": f"Bearer {token}"})
    return resp


def create_folder(name, parent=None):
    url = f"{BASE_URL}/folders"
    payload = {"name": name}
    if parent is not None:
        payload["parent_folder_id"] = parent
    resp = session.post(url, json=payload)
    print_step(f"CREATE FOLDER -> {name}")
    pretty(dump_resp(resp))
    return resp


def upload_file(name, content_bytes, parent=None):
    url = f"{BASE_URL}/files"
    content_b64 = base64.b64encode(content_bytes).decode("utf-8")
    payload = {"name": name, "content": content_b64, "parent_folder_id": parent}
    resp = session.post(url, json=payload)
    print_step(f"UPLOAD FILE -> {name}")
    pretty(dump_resp(resp))
    return resp


def get_file_meta(file_id):
    url = f"{BASE_URL}/files/{file_id}"
    resp = session.get(url)
    print_step(f"GET FILE METADATA -> {file_id}")
    pretty(dump_resp(resp))
    return resp


def download_file(file_id):
    url = f"{BASE_URL}/files/{file_id}/download"
    resp = session.get(url)
    print_step(f"DOWNLOAD FILE -> {file_id}")
    pretty(dump_resp(resp))
    # if base64 content present show len
    try:
        data = resp.json()
        c = data.get("content")
        if c:
            decoded = base64.b64decode(c)
            print("Decoded bytes:", len(decoded))
    except Exception:
        pass
    return resp


def rename_file(file_id, new_name):
    url = f"{BASE_URL}/files/{file_id}"
    resp = session.patch(url, json={"name": new_name})
    print_step(f"RENAME FILE -> {file_id} to {new_name}")
    pretty(dump_resp(resp))
    return resp


def move_file(file_id, parent_folder_id):
    url = f"{BASE_URL}/files/{file_id}/move"
    # move implemented with POST and parent as query param in server
    resp = session.post(url, params={"parent_folder_id": parent_folder_id})
    print_step(f"MOVE FILE -> {file_id} to folder {parent_folder_id}")
    pretty(dump_resp(resp))
    return resp


def delete_file(file_id):
    url = f"{BASE_URL}/files/{file_id}"
    resp = session.delete(url)
    print_step(f"DELETE FILE -> {file_id}")
    pretty(dump_resp(resp))
    return resp


def delete_folder(folder_id):
    url = f"{BASE_URL}/folders/{folder_id}"
    resp = session.delete(url)
    print_step(f"DELETE FOLDER -> {folder_id}")
    pretty(dump_resp(resp))
    return resp


def run_smoke():
    # generate unique user
    uniq = str(uuid.uuid4())[:8]
    email = f"test+{uniq}@example.com"
    password = "smoketest"

    register(email, password)
    login(email, password)

    # create folder
    fr = create_folder("smoke-folder")
    fdata = fr.json() if fr.ok else {}
    folder_id = fdata.get("id")

    # upload file
    content = b"hello smoke"
    ur = upload_file("hello.txt", content, parent=folder_id)
    udata = ur.json() if ur.ok else {}
    file_id = udata.get("id")

    if file_id:
        get_file_meta(file_id)
        download_file(file_id)
        rename_file(file_id, "hello-renamed.txt")

        # create dest folder and move
        dr = create_folder("dest-folder")
        ddata = dr.json() if dr.ok else {}
        dest_id = ddata.get("id")
        if dest_id:
            move_file(file_id, dest_id)

        delete_file(file_id)

    # cleanup folders
    if 'dest_id' in locals() and dest_id:
        delete_folder(dest_id)
    if folder_id:
        delete_folder(folder_id)

    print_step("SMOKE TEST COMPLETE")


if __name__ == "__main__":
    try:
        run_smoke()
    except Exception as e:
        print("ERROR during smoke tests:", e)
        sys.exit(2)
    sys.exit(0)
