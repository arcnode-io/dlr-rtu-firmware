"""
Hardware-in-Loop test for full DLR stack.

Tests the full Pi-deployed pipeline by:
- Starting an MQTT broker in a testcontainer with a dynamic port
- Deploying code to a Raspberry Pi via SSH
- Running the app on the Pi with the dynamic MQTT host+port plumbed in
- Verifying a line-rating message arrives on the MQTT topic
"""

import os
import socket
import threading
import time
from pathlib import Path

import paramiko
import paho.mqtt.client as mqtt_client

from build import CONFIG
from src.mqtt import FloatSample, dynamic_line_rating_topic
from tests.fixtures.containers import start_mqtt_broker

# Canonical topic where IEEE 738 line-rating readings are published. Built
# the same way the app builds it, from the same CONFIG (ENV unset -> "local"
# section, same as the SSH-deployed run below) -- avoids a second hardcoded
# copy drifting from the real topic.
MQTT_TOPIC = dynamic_line_rating_topic(CONFIG)

# Maximum time to wait for subscription confirmation (seconds)
SUBSCRIBE_TIMEOUT = 10

# Maximum time to wait for MQTT message after app completes (seconds)
MESSAGE_TIMEOUT = 10


def test_hil_mqtt_integration() -> None:
    """
    Test HIL MQTT integration.

    This test requires a Raspberry Pi with DHT22 sensor connected.
    It will fail if hardware is not available.
    """
    start_time = time.time()

    def log(msg: str) -> None:
        print(f"[{time.time() - start_time:.1f}s] {msg}")

    # Get Pi connection details from environment
    # Reason: must match the ENV this process resolved CONFIG/MQTT_TOPIC from
    # (build.py defaults the same way) -- otherwise the Pi publishes under a
    # different cfg.yml section's site_id/device_id than we're subscribed to.
    pi_env = os.environ.get("ENV", "local")
    pi_host = os.environ.get("PI_HOST", "pi@raspberrypi.local")
    pi_python = os.environ.get(
        "PI_PYTHON", "/home/pi/dlr-operating-envelope/.venv/bin/python"
    )
    if "@" in pi_host:
        pi_user, pi_hostname = pi_host.split("@")
    else:
        pi_user = "pi"
        pi_hostname = pi_host

    # Arrange - Start MQTT broker
    with start_mqtt_broker() as broker:
        broker_port = broker.port
        log(f"MQTT broker started on port {broker_port}")

        # Get host IP that Pi can reach (not localhost)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        host_ip = s.getsockname()[0]
        s.close()

        log(f"Host IP for Pi to connect: {host_ip}")

        # Setup subscriber to capture published messages
        received_messages: list[str] = []
        subscribed = threading.Event()

        def on_connect(
            _client: mqtt_client.Client,
            _userdata: object,
            _flags: object,
            reason_code: object,
            _properties: object,
        ) -> None:
            log(f"Subscriber connected (rc={reason_code})")
            _client.subscribe(MQTT_TOPIC)

        def on_subscribe(
            _client: mqtt_client.Client,
            _userdata: object,
            _mid: int,
            _reason_codes: object,
            _properties: object,
        ) -> None:
            log(f"Subscription confirmed for {MQTT_TOPIC}")
            subscribed.set()

        def on_message(
            _client: mqtt_client.Client,
            _userdata: object,
            message: mqtt_client.MQTTMessage,
        ) -> None:
            payload = message.payload.decode()
            log(f"Message received on {message.topic}: {payload}")
            received_messages.append(payload)

        subscriber = mqtt_client.Client(
            callback_api_version=mqtt_client.CallbackAPIVersion.VERSION2,  # type: ignore[attr-defined]
            client_id="hil_test_client",
            protocol=mqtt_client.MQTTv5,
        )
        subscriber.on_connect = on_connect
        subscriber.on_subscribe = on_subscribe
        subscriber.on_message = on_message

        log("Connecting subscriber to broker...")
        subscriber.connect("localhost", broker_port)
        subscriber.loop_start()

        # Reason: subscribe() races with loop_start() — the SUBSCRIBE packet
        # can't be sent until the loop thread runs. Wait for SUBACK before
        # launching the Pi app so we don't miss the first (and only) message.
        assert subscribed.wait(
            timeout=SUBSCRIBE_TIMEOUT
        ), f"Subscription not confirmed within {SUBSCRIBE_TIMEOUT}s"

        # Deploy and run code on Pi using paramiko
        log("Deploying code to Pi via SSH...")

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # noqa: S507

        try:
            ssh.connect(pi_hostname, username=pi_user)
            log(f"SSH connected to {pi_hostname}")

            # Create remote directory
            ssh.exec_command("mkdir -p /tmp/circuitpython-test")

            # Upload src directory
            sftp = ssh.open_sftp()
            project_root = Path(__file__).parent.parent

            # Upload src files
            for src_file in (project_root / "src").rglob("*.py"):
                relative_path = src_file.relative_to(project_root)
                remote_path = f"/tmp/circuitpython-test/{relative_path}"  # noqa: S108

                # Create remote directory if needed
                remote_dir = str(Path(remote_path).parent)
                ssh.exec_command(f"mkdir -p {remote_dir}")

                sftp.put(str(src_file), remote_path)

            # Upload build.py and cfg.yml
            sftp.put(
                str(project_root / "build.py"),
                "/tmp/circuitpython-test/build.py",  # noqa: S108
            )
            sftp.put(
                str(project_root / "cfg.yml"),
                "/tmp/circuitpython-test/cfg.yml",  # noqa: S108
            )

            sftp.close()
            log("Files deployed")

            log("Running application on Pi...")
            cmd = (
                f"cd /tmp/circuitpython-test && "
                f"MQTT_HOST={host_ip} MQTT_PORT={broker_port} MODE=development "
                f"ENV={pi_env} "
                f"{pi_python} -m src.main"
            )
            log(f"CMD: {cmd}")

            _stdin, stdout, stderr = ssh.exec_command(
                cmd,
                get_pty=True,
                timeout=30,
            )

            # Wait for command to complete
            exit_status = stdout.channel.recv_exit_status()

            stdout_text = stdout.read().decode()
            stderr_text = stderr.read().decode()

            log(f"Application completed (exit={exit_status})")
            if stdout_text:
                log(f"STDOUT: {stdout_text}")
            if stderr_text:
                log(f"STDERR: {stderr_text}")

            # Assert - Application ran successfully
            assert (
                exit_status == 0
            ), f"Application failed with exit status {exit_status}"

        finally:
            ssh.close()

        # Wait for message to arrive
        log(f"Waiting up to {MESSAGE_TIMEOUT}s for MQTT message...")
        deadline = time.time() + MESSAGE_TIMEOUT
        while not received_messages and time.time() < deadline:
            time.sleep(0.2)

        log(f"Messages received: {len(received_messages)}")

        # Assert - line-rating message received
        assert len(received_messages) >= 1, "No MQTT message received"

        # Assert - value is a positive float (IEEE 738 ampacity, amps).
        # Loose bound: ~10 A floor catches dead/zero output; 5000 A ceiling
        # catches obviously-wrong scaling. The sim sensors at first-tick state
        # land somewhere in the low-hundreds for DRAKE_ACSR_795 conductor.
        sample = FloatSample.model_validate_json(received_messages[0])
        line_rating_a = sample.value
        assert (
            10.0 <= line_rating_a <= 5000.0
        ), f"line rating {line_rating_a}A outside plausible range"

        log(f"Test passed! Received valid line rating: {line_rating_a}A")

        # Cleanup
        subscriber.loop_stop()
        subscriber.disconnect()
