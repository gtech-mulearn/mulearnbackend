"""Liveness and readiness for the load balancer and deploys (ADR-006).

Both describe this process only: readiness never checks anything outside it, so one bad
dependency elsewhere can't take the whole fleet out of rotation.
"""
