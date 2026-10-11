"""Kubernetes Lease guard so duplicate controller pods never both write an HPA."""
from datetime import datetime, timedelta, timezone
import logging
import os

logger = logging.getLogger(__name__)


def _get(value, key, default=None):
    return value.get(key, default) if isinstance(value, dict) else getattr(value, key, default)


class KubernetesLeaseLock:
    def __init__(self, api, namespace: str, name: str, identity: str, duration_seconds: int = 30):
        self.api = api
        self.namespace = namespace
        self.name = name
        self.identity = identity
        self.duration_seconds = duration_seconds

    @classmethod
    def from_env(cls):
        from kubernetes import client
        return cls(client.CoordinationV1Api(), os.getenv("KUBERNETES_NAMESPACE", "sla-autoscaling"),
                   os.getenv("LEASE_NAME", "cloudscale-controller-lock"),
                   os.getenv("POD_NAME", os.getenv("HOSTNAME", "cloudscale-controller")),
                   int(os.getenv("LEASE_DURATION_SECONDS", "30")))

    def acquire_or_renew(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        try:
            lease = self.api.read_namespaced_lease(self.name, self.namespace)
        except Exception as exc:
            if getattr(exc, "status", None) != 404:
                logger.exception("Unable to read controller Lease %s", self.name)
                raise
            body = self._body(now, None)
            try:
                self.api.create_namespaced_lease(self.namespace, body)
                logger.info("Acquired controller Lease %s as %s", self.name, self.identity)
                return True
            except Exception as create_error:
                if getattr(create_error, "status", None) == 409:
                    return False
                logger.exception("Unable to create controller Lease %s", self.name)
                raise

        spec = _get(lease, "spec", {})
        owner = _get(spec, "holder_identity", _get(spec, "holderIdentity"))
        renewed = _get(spec, "renew_time", _get(spec, "renewTime"))
        duration = _get(spec, "lease_duration_seconds", _get(spec, "leaseDurationSeconds", self.duration_seconds))
        if owner and owner != self.identity:
            if renewed is None or (now - renewed).total_seconds() < duration:
                return False
        body = self._body(now, _get(_get(lease, "metadata", {}), "resource_version",
                                    _get(_get(lease, "metadata", {}), "resourceVersion")), lease)
        try:
            self.api.replace_namespaced_lease(self.name, self.namespace, body)
            if owner != self.identity:
                logger.info("Acquired controller Lease %s as %s", self.name, self.identity)
            return True
        except Exception as exc:
            if getattr(exc, "status", None) == 409:
                return False
            logger.exception("Unable to renew controller Lease %s", self.name)
            raise

    def _body(self, now: datetime, resource_version, previous=None):
        from kubernetes import client
        metadata = client.V1ObjectMeta(name=self.name, namespace=self.namespace,
                                       resource_version=resource_version)
        prior_spec = _get(previous, "spec", {}) if previous is not None else {}
        owner = _get(prior_spec, "holder_identity", _get(prior_spec, "holderIdentity"))
        acquired = _get(prior_spec, "acquire_time", _get(prior_spec, "acquireTime"))
        if owner != self.identity or acquired is None:
            acquired = now
        spec = client.V1LeaseSpec(holder_identity=self.identity,
                                  lease_duration_seconds=self.duration_seconds,
                                  acquire_time=acquired, renew_time=now)
        return client.V1Lease(metadata=metadata, spec=spec)
