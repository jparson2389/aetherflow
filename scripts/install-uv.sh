#!/usr/bin/env sh
set -eu

UV_VERSION="0.10.10"
UV_ARCHIVE="uv-x86_64-unknown-linux-gnu.tar.gz"
UV_SHA256="3e1027f26ce8c7e4c32e2277a7fed2cb410f2f1f9320d3df97653d40e21f415b"
UV_URL="https://releases.astral.sh/github/uv/releases/download/${UV_VERSION}/${UV_ARCHIVE}"
TMP_DIR="$(mktemp -d)"
ARCHIVE_PATH="${TMP_DIR}/${UV_ARCHIVE}"

cleanup() {
  rm -rf "${TMP_DIR}"
}

trap cleanup EXIT

curl -LsSf "${UV_URL}" -o "${ARCHIVE_PATH}"
echo "${UV_SHA256}  ${ARCHIVE_PATH}" | sha256sum -c -
tar -xzf "${ARCHIVE_PATH}" -C "${TMP_DIR}"
mkdir -p "${HOME}/.local/bin"
install "${TMP_DIR}/uv-x86_64-unknown-linux-gnu/uv" "${HOME}/.local/bin/uv"

