import signal
import sys

class ShutdownManager:
    def __init__(self, enabled=False):
        self.enabled = enabled
        self._services = []
        if self.enabled:
            signal.signal(signal.SIGINT, self._handle)

    def register(self, service):
        """
        service must implement:
        - stop()
        - thread (optional)
        """
        self._services.append(service)

    def _handle(self, signum, frame):
        print("\nshutdown initiated")

        for s in self._services:
            try:
                s.stop()
            except Exception as e:
                print(f"Stop error: {e}")

        for s in self._services:
            t = getattr(s, "thread", None)
            if t and t.is_alive():
                t.join(timeout=2)

        # sys.exit(0)