"""Testcontainer fixtures with dynamic port allocation."""

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass

from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy


@dataclass(frozen=True)
class Container:
    """Connection info for a running testcontainer.

    Attributes:
        host: Container host (always localhost)
        port: Dynamic mapped port
        url: Pre-built connection URL
    """

    host: str
    port: int
    url: str


@contextmanager
def _start_container(
    image: str,
    port: int,
    wait_for_log: str,
) -> Generator[Container]:
    """Start a generic Docker container with dynamic port. Internal building block.

    Args:
        image: Docker image
        port: Internal container port to expose
        wait_for_log: Log message indicating readiness

    Yields:
        Container with http:// URL and dynamic port
    """
    c = (
        DockerContainer(image)
        .with_exposed_ports(port)
        .waiting_for(LogMessageWaitStrategy(wait_for_log))
    )

    with c:
        mapped = int(c.get_exposed_port(port))
        yield Container(
            host="localhost",
            port=mapped,
            url=f"http://localhost:{mapped}",
        )


@contextmanager
def start_mqtt_broker() -> Generator[Container]:
    """Start an HiveMQ MQTT broker with dynamic port.

    Yields:
        Container with mqtt:// URL and dynamic port
    """
    c = (
        DockerContainer("hivemq/hivemq-ce:latest")
        .with_exposed_ports(1883)
        .waiting_for(
            LogMessageWaitStrategy(
                "Started TCP Listener on address 0.0.0.0 and on port 1883."
            )
        )
    )

    with c:
        mapped = int(c.get_exposed_port(1883))
        yield Container(
            host="localhost",
            port=mapped,
            url=f"mqtt://localhost:{mapped}",
        )
