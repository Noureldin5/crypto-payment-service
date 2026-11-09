# Bitcoin Core (open-source crypto wallet + node), downloaded from bitcoincore.org.
# Works on x86_64 (DigitalOcean) and arm64 (Apple Silicon / ARM servers).
FROM debian:bookworm-slim

ARG BITCOIN_VERSION=27.1
ARG TARGETARCH

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && case "${TARGETARCH:-amd64}" in \
         amd64) ARCH=x86_64-linux-gnu ;; \
         arm64) ARCH=aarch64-linux-gnu ;; \
         *) echo "unsupported arch ${TARGETARCH}" && exit 1 ;; \
       esac \
    && curl -fsSL "https://bitcoincore.org/bin/bitcoin-core-${BITCOIN_VERSION}/bitcoin-${BITCOIN_VERSION}-${ARCH}.tar.gz" \
       | tar -xz -C /opt \
    && ln -s /opt/bitcoin-${BITCOIN_VERSION}/bin/* /usr/local/bin/ \
    && apt-get purge -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

VOLUME /root/.bitcoin
EXPOSE 18443
