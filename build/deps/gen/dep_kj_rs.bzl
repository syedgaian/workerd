# WARNING: THIS FILE IS AUTOGENERATED BY update-deps.py DO NOT EDIT

load("@//:build/http.bzl", "http_archive")

URL = "https://github.com/capnproto/kj-rs/tarball/85961e850c3e2710847bbfa596e9b8bcb562e873"
STRIP_PREFIX = "capnproto-kj-rs-85961e8"
SHA256 = "4682114672487873a8ace77a47fb49c9622c3a3f789630a14aad3509bae918cc"
TYPE = "tgz"
COMMIT = "85961e850c3e2710847bbfa596e9b8bcb562e873"

def dep_kj_rs():
    http_archive(
        name = "kj-rs",
        url = URL,
        strip_prefix = STRIP_PREFIX,
        type = TYPE,
        sha256 = SHA256,
    )
