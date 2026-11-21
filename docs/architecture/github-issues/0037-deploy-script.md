# Add deploy.sh with pre-flight checks, rolling deploys and rollback

| | |
|---|---|
| ID | 0037 |
| Phase / milestone | Phase 2: Serving and runtime |
| Module | platform |
| Size | L |
| Labels | arch, phase:2, module:platform, type:feature, size:L, core-review |
| Depends on | 0020, 0032, 0036 |
| Blocks | 0045, 0061, 0068, 0078 |
| Repos | mulearnbackend |

## Why

Deploys must be repeatable, node by node, with a rollback that is just "deploy the previous digest" ([ADR-049](../adr/ADR-049-deployment-platform-and-dr.md), [10-infrastructure-and-deployment.md](../10-infrastructure-and-deployment.md#deploying-a-release)).

## Before you start

- Issues 0032 (health and drain) and 0036 (images) must be merged.
- Issue 0020 must also be merged.

## What to do

1. Create `scripts/deploy.sh <env> <digest>`. For each node in `deploy/<env>/nodes.txt`, canary first, it:
   1. runs the pre-flight: `python manage.py config_check` inside the new image against the environment's settings;
   2. pulls the image by digest;
   3. touches the drain file, so readiness returns 503, then waits for the balancer to deregister the node (up to 30 s);
   4. runs `docker compose up -d` with `IMAGE=<digest>`;
   5. polls `/healthz/ready` until 200 (up to 60 s), else stops and prints the rollback command;
   6. moves on to the next node.
2. Record each successful deploy's digest in `deploy/<env>/last-good.txt` on the host. `scripts/deploy.sh <env> --rollback` redeploys the previous one.
3. Create `deploy/compose.yml`, which runs the roles from one image (`web`, `worker`, `beat`) as separate services, with resource limits and no host port except nginx. Each line of `deploy/<env>/nodes.txt` names a node and the roles it runs, for example `pod0 web,worker,beat` and `pod1 web,worker`. `deploy.sh` starts only those roles on each node, and refuses a nodes file in which no node, or more than one, runs `beat`. Today's second node already runs no beat on purpose (`docker-compose.pod.yml`).
4. Add `--dry-run`, which prints every step without running it.

## Acceptance criteria

- [ ] `scripts/deploy.sh staging <digest> --dry-run` prints the full plan.
- [ ] On a staging rehearsal, a deploy and a rollback each finish within 5 minutes.
- [ ] A failing readiness check stops the rollout at the first node.
- [ ] A nodes file with two `beat` nodes, or none, is refused before anything is deployed.

## How to test

Run `scripts/deploy.sh staging <digest> --dry-run` and paste the output. The real rehearsal is issue 0045.

## Out of scope

- Changing production (issue 0047).

## Notes for reviewers

This is the deploy path. Two reviewers; check that a failure can never leave every node on a broken digest.
