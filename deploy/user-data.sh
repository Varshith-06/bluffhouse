#!/bin/bash
# Disposable build host: build the bluffhouse image, push it into the Lightsail
# container service registry, report status to S3, then shut down.
set -uxo pipefail

BUCKET=bluffhouse-build-516633645639
REGION=ap-south-1
SERVICE=bluffhouse
LOG=/var/log/bluffhouse-build.log

exec > >(tee -a "$LOG") 2>&1

put() { aws s3 cp "$2" "s3://$BUCKET/build/$3" --region "$REGION" >/dev/null 2>&1 || true; }
status() { echo "$1" > /tmp/status; put x /tmp/status status.txt; put x "$LOG" build.log; }

# ship the log every 15s so progress is visible from outside
( while true; do sleep 15; put x "$LOG" build.log; done ) &

fail() { echo "STEP FAILED: $1"; status "FAILED: $1"; shutdown -h +5; exit 1; }

status RUNNING

# t3.micro is the only free-tier-eligible type on this account (1GB RAM),
# which is thin for a docker build — back it with swap.
fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
free -m

dnf install -y docker tar gzip || fail "dnf install"
systemctl start docker || fail "start docker"

curl -sSL "https://s3.us-west-2.amazonaws.com/lightsailctl/latest/linux-amd64/lightsailctl" \
  -o /usr/local/bin/lightsailctl || fail "download lightsailctl"
chmod +x /usr/local/bin/lightsailctl

mkdir -p /build && cd /build || fail "mkdir /build"
aws s3 cp "s3://$BUCKET/build/source.tar.gz" source.tar.gz --region "$REGION" || fail "fetch source"
tar -xzf source.tar.gz || fail "untar source"
ls -la

status BUILDING
docker build -f deploy/Dockerfile -t bluffhouse:latest . || fail "docker build"

# guard the two assumptions that would otherwise ship a broken app:
# that the wheel carries the built frontend, and that the demo run baked in
status SMOKETEST
docker run --rm bluffhouse:latest python -c "
from importlib.resources import files
from pathlib import Path
p = Path(str(files('bluffhouse.webapp') / 'static')) / 'index.html'
assert p.exists(), 'frontend build missing from wheel'
print('ok: frontend build present')
" || fail "smoke test: frontend build"

docker run --rm bluffhouse:latest python -c "
from pathlib import Path
assert Path('/app/runs/demo-seed11/run.json').exists(), 'demo run missing'
assert Path('/app/runs/demo-seed11/replay.html').exists(), 'replay missing'
print('ok: demo run baked in')
" || fail "smoke test: demo run"

# the app must actually answer on :8080 before we ship it
docker run -d --name probe -p 8080:8080 bluffhouse:latest || fail "start probe"
for i in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/ || true)
  hub=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/api/hub || true)
  echo "probe attempt $i: / -> $code, /api/hub -> $hub"
  if [ "$code" = "200" ] && [ "$hub" = "200" ]; then ok=1; break; fi
  sleep 2
done
echo "--- probe container logs ---"; docker logs probe 2>&1 | tail -30
curl -s http://127.0.0.1:8080/api/hub | head -c 600; echo
docker rm -f probe >/dev/null 2>&1 || true
[ "${ok:-0}" = "1" ] || fail "probe: app did not serve / and /api/hub"

status PUSHING
aws lightsail push-container-image --region "$REGION" --service-name "$SERVICE" \
  --label app --image bluffhouse:latest || fail "push to lightsail"

status SUCCESS
shutdown -h +2
