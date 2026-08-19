# Deploying bluffhouse on AWS

Live: <https://bluffhouse.6nnk2pydj9qsy.ap-south-1.cs.amazonlightsail.com/>

Hosted as a single container on a **Lightsail container service** (`bluffhouse`,
`ap-south-1`, power `nano`). Lightsail terminates TLS and hands out the HTTPS
hostname, so there is no load balancer, certificate, or domain to manage.

## Why the build runs on a throwaway EC2 host

The AWS account is on the **new Free Tier plan**, which rules out the obvious
paths. Worth knowing before you reach for one of them again:

| Approach | Why it doesn't work here |
| --- | --- |
| App Runner | `SubscriptionRequiredException` in every region |
| CodeBuild | account limit of **0** concurrent builds |
| Lightsail `micro`+ | only `nano` is allowed |
| EC2 `t3.small`+ | "not eligible for Free Tier" — `t3.micro` only |

Lightsail also can't pull from a private ECR, and the account's ECR Public
registry has no alias — so the image has to be pushed straight into the
Lightsail registry with `lightsailctl`. That needs a real Docker daemon, which
is what the EC2 host provides.

`t3.micro` has 1GB of RAM, so the build script adds a 4GB swapfile before
running `docker build`.

## Rebuilding and redeploying

1. Repackage the source (forward-slash paths matter — PowerShell's
   `Compress-Archive` writes backslashes that Linux `tar`/`unzip` choke on):

   ```bash
   tar -czf source.tar.gz --exclude=__pycache__ \
     pyproject.toml uv.lock README.md .dockerignore src deploy
   aws s3 cp source.tar.gz s3://bluffhouse-build-516633645639/build/source.tar.gz
   ```

2. Launch the build host. It installs Docker, builds the image, runs its smoke
   tests, pushes to Lightsail, and terminates itself:

   ```bash
   aws ec2 run-instances --region ap-south-1 \
     --image-id ami-0d15e9052c94acb75 --instance-type t3.micro \
     --iam-instance-profile Name=bluffhouse-builder \
     --instance-initiated-shutdown-behavior terminate \
     --user-data file://user-data.sh
   ```

   Progress is mirrored to `s3://bluffhouse-build-516633645639/build/status.txt`
   and `build.log` — the instance has no inbound access, so that's how you watch
   it. Terminal states are `SUCCESS` and `FAILED: <step>`.

3. Deploy the pushed image. `push-container-image` prints the ref to use, and
   the version number increments on every push:

   ```bash
   aws lightsail get-container-images --region ap-south-1 --service-name bluffhouse
   sed 's|IMAGE_REF|:bluffhouse.app.N|' lightsail-deployment.json > /tmp/d.json
   aws lightsail create-container-service-deployment --region ap-south-1 \
     --service-name bluffhouse --cli-input-json file:///tmp/d.json
   ```

The service reports `RUNNING` / `ACTIVE` when live; `get-container-log` shows
`Reached a steady state`. Expect a few minutes — it serves 503 until the health
checks flip it over.

## What the build verifies before shipping

`user-data.sh` fails the build rather than pushing a broken image if any of
these regress:

- the built frontend is actually inside the wheel (`webapp/static/index.html`)
- the scripted demo run baked in (`/app/runs/demo-seed11/`)
- the container really serves `/` and `/api/hub` on port 8080

## Things to know about the running service

- **Storage is ephemeral.** Live games written at runtime are lost on redeploy.
  The Dockerfile bakes in the scripted `demo-seed11` run so the hub is never
  empty on a cold container.
- **No API keys are deployed.** Live games use keys supplied per-request from
  the browser and held in memory only; the scripted demo needs none.
- **512MB of RAM.** Fine for replay and the demo. Several concurrent live LLM
  games are the thing most likely to strain it — `micro` needs a paid plan.

## Resources this created

- Lightsail container service `bluffhouse` (ap-south-1)
- S3 bucket `bluffhouse-build-516633645639` — build source and logs
- IAM role `bluffhouse-builder-role` + instance profile `bluffhouse-builder`
