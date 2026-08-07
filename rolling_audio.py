from __future__ import annotations

import io
import threading
import wave
from collections import deque

import sounddevice as sd


class RollingAudioBuffer:
    """Keep only the latest microphone audio in memory."""

    def __init__(
        self,
        duration_seconds: int = 10,
        sample_rate: int = 16_000,
        channels: int = 1,
    ) -> None:
        self.duration_seconds = max(1, int(duration_seconds))
        self.sample_rate = max(8_000, int(sample_rate))
        self.channels = max(1, int(channels))
        self.sample_width = 2  # int16

        self._max_bytes = 0
        self._update_max_bytes()

        self._chunks: deque[bytes] = deque()
        self._total_bytes = 0
        self._lock = threading.Lock()
        self._stream: sd.RawInputStream | None = None
        self._last_error = ""

    def _update_max_bytes(self) -> None:
        self._max_bytes = (
            self.duration_seconds
            * self.sample_rate
            * self.channels
            * self.sample_width
        )

    @property
    def last_error(self) -> str:
        return self._last_error

    @property
    def is_running(self) -> bool:
        stream = self._stream
        if stream is None:
            return False

        try:
            return bool(stream.active)
        except Exception:
            return False

    def _callback(self, indata, frames, time_info, status) -> None:
        del frames, time_info

        if status:
            self._last_error = str(status)

        chunk = bytes(indata)
        if not chunk:
            return

        with self._lock:
            self._chunks.append(chunk)
            self._total_bytes += len(chunk)

            while self._total_bytes > self._max_bytes and self._chunks:
                excess = self._total_bytes - self._max_bytes
                oldest = self._chunks[0]

                if excess >= len(oldest):
                    self._chunks.popleft()
                    self._total_bytes -= len(oldest)
                    continue

                self._chunks[0] = oldest[excess:]
                self._total_bytes -= excess

    def _close_stream(self, stream: sd.RawInputStream | None) -> None:
        if stream is None:
            return

        try:
            stream.stop()
        except Exception:
            pass

        try:
            stream.close()
        except Exception:
            pass

    def start(self) -> None:
        if self.is_running:
            return

        # A device change can leave a dead stream object behind. Close it before
        # opening another stream so Windows audio handles do not accumulate.
        stale_stream = self._stream
        self._stream = None
        self._close_stream(stale_stream)

        self._last_error = ""

        device_info = sd.query_devices(kind="input")
        default_rate = int(round(float(device_info["default_samplerate"])))

        if default_rate > 0:
            self.sample_rate = default_rate
            self._update_max_bytes()

        stream: sd.RawInputStream | None = None
        try:
            stream = sd.RawInputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
                callback=self._callback,
                blocksize=0,
                latency="low",
            )
            stream.start()
        except Exception:
            self._close_stream(stream)
            raise

        self._stream = stream

    def stop(self) -> None:
        stream = self._stream
        self._stream = None
        self._close_stream(stream)

        with self._lock:
            self._chunks.clear()
            self._total_bytes = 0

    def available_seconds(self) -> float:
        bytes_per_second = (
            self.sample_rate
            * self.channels
            * self.sample_width
        )

        with self._lock:
            total_bytes = self._total_bytes

        return total_bytes / bytes_per_second

    def snapshot_wav(self) -> bytes:
        with self._lock:
            chunks = list(self._chunks)

        pcm = b"".join(chunks)
        if not pcm:
            return b""

        with io.BytesIO() as buffer:
            with wave.open(buffer, "wb") as wav_file:
                wav_file.setnchannels(self.channels)
                wav_file.setsampwidth(self.sample_width)
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(pcm)

            return buffer.getvalue()
