# WARNING: THIS FILE IS AUTOGENERATED BY update-deps.py DO NOT EDIT

load("@//:build/http.bzl", "http_archive")

TAG_NAME = "0.11.10"
URL = "https://github.com/astral-sh/ruff/releases/download/0.11.10/ruff-x86_64-unknown-linux-gnu.tar.gz"
STRIP_PREFIX = "ruff-x86_64-unknown-linux-gnu"
SHA256 = "ade458637abe06ff6780e0b3a5fdd281da552d33eb75b954fc2a27278258b856"
TYPE = "tgz"

def dep_ruff_linux_amd64():
    http_archive(
        name = "ruff-linux-amd64",
        url = URL,
        strip_prefix = STRIP_PREFIX,
        type = TYPE,
        sha256 = SHA256,
        build_file_content = "filegroup(name='file', srcs=['ruff'], visibility=['//visibility:public'])",
    )
